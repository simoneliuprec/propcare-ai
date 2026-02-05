# app/graph.py
from __future__ import annotations
from typing import Dict, List, TypedDict, Any, Optional
from datetime import datetime, timezone

from langgraph.graph import StateGraph, START, END
from openai import AsyncOpenAI
from supabase import Client

from .schemas import Message, TriageState, TriageTurn
from .tools import create_ticket_record, update_ticket_record
from .notifications import enqueue_ticket_event
from .llm import chat_turn_json
from .policy import detect_emergency

URGENCY_MAP = {
    "P0": "P0_EMERGENCY",
    "P1": "P1_URGENT",
    "P2": "P2_SOON",
    "P3": "P3_ROUTINE",
}

def _to_openai_messages(msgs: List[Message], keep_last: int = 12) -> List[Dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in msgs[-keep_last:]]

def _latest_user_text(msgs: List[Message]) -> str:
    for m in reversed(msgs):
        if m.role == "user":
            return m.content or ""
    return ""

def _append_detail(prev: str | None, line: str) -> str:
    base = (prev or "").strip()
    return line if not base else base + "\n" + line

# LangGraph State = your TriageState + a few ephemeral fields
class GraphState(TypedDict, total=False):
    triage: TriageState
    latest_text: str
    is_emergency: bool
    emergency_type: Optional[str]
    emergency_reason: Optional[str]
    turn: TriageTurn
    tenant_reply: str

def build_triage_graph(llm_client: AsyncOpenAI, supabase: Client):
    async def detect_node(s: GraphState) -> GraphState:
        triage = s["triage"]
        latest = _latest_user_text(triage.messages)
        is_emergency, etype, ereason = detect_emergency(latest)
        return {
            "latest_text": latest,
            "is_emergency": is_emergency,
            "emergency_type": etype,
            "emergency_reason": ereason,
        }

    async def ensure_ticket_node(s: GraphState) -> GraphState:
        triage = s["triage"]
        latest = s.get("latest_text", "")
        if triage.ticket_id:
            return {}
        init_summary = f"Tenant report: {latest}".strip()[:5000]
        ticket = create_ticket_record(
            supabase,
            summary=init_summary,
            urgency=URGENCY_MAP["P2"],
            status="intake",
            tenant_name=triage.tenant_name,
            tenant_email=triage.tenant_email,
            tenant_phone=triage.tenant_phone,
            property_address=triage.property_address,
            unit=triage.unit,
            source="web",
        )
        triage.ticket_created = True
        triage.ticket_id = int(ticket["id"])
        return {}

    async def llm_node(s: GraphState) -> GraphState:
        triage = s["triage"]
        ticket_id = int(triage.ticket_id or 0)
        openai_msgs = _to_openai_messages(triage.messages)

        extra = (
            "CONTEXT (not tenant-facing):\n"
            f"- Tenant name: {triage.tenant_name or ''}\n"
            f"- Tenant email: {triage.tenant_email or ''}\n"
            f"- Tenant phone: {triage.tenant_phone or ''}\n"
            f"- Property address: {triage.property_address or ''}\n"
            f"- Unit: {triage.unit or ''}\n"
            f"- Ticket id: {ticket_id}\n"
        )

        if s.get("is_emergency"):
            extra += (
                "\nBACKEND:\n"
                f"- emergency=true\n"
                f"- emergency_type={s.get('emergency_type')}\n"
                "RULES:\n"
                "- Enter EMERGENCY MODE: give brief BC safety guidance, stop troubleshooting, ask exactly ONE safety confirmation question.\n"
                "- If gas-related, mention FortisBC Emergency Line 1-800-663-9911 (call from outside, once safe).\n"
                "- Set status=action_required and should_notify_manager=true.\n"
            )

        turn = await chat_turn_json(
            llm_client,
            openai_msgs,
            temperature=0.2 if s.get("is_emergency") else 0.3,
            extra_instructions=extra,
        )
        return {"turn": turn}

    async def persist_and_notify_node(s: GraphState) -> GraphState:
        triage = s["triage"]
        turn = s["turn"]
        latest = s.get("latest_text", "")
        ticket_id = int(triage.ticket_id)

        category = turn.category
        urgency = turn.urgency
        status = turn.status
        should_notify = turn.should_notify_manager
        summary = (turn.summary_for_ticket or "").strip()
        tenant_reply = (turn.tenant_reply or "").strip()

        if s.get("is_emergency"):
            urgency = "P0"
            status = "action_required"
            should_notify = True
            if not summary:
                summary = f"[EMERGENCY:{s.get('emergency_type')}] {s.get('emergency_reason')} Tenant said: {latest}"

        db_urgency = URGENCY_MAP.get(urgency, URGENCY_MAP["P2"])

        now = datetime.now(timezone.utc).isoformat()
        detail_line = f"{now}Z | user: {latest}"

        existing = (
            supabase.table("tickets")
            .select("issue_details")
            .eq("id", ticket_id)
            .limit(1)
            .execute()
        )
        prev_details = existing.data[0].get("issue_details") if existing.data else None
        new_details = _append_detail(prev_details, detail_line)

        ticket = update_ticket_record(
            supabase,
            ticket_id=ticket_id,
            summary=summary or f"Tenant report: {latest}",
            urgency=db_urgency,
            status=status,
            category=category,
            issue_details=new_details,
            resolved=(status == "resolved"),
        )

        if should_notify and status == "action_required":
            enqueue_ticket_event(
                supabase,
                event_type="ticket.emergency" if s.get("is_emergency") else "ticket.action_required",
                ticket=ticket,
            )

        triage.messages.append(Message(role="assistant", content=tenant_reply))
        triage.ticket_created = True
        triage.ticket_id = ticket_id
        return {"tenant_reply": tenant_reply}

    # ---- build graph ----
    g = StateGraph(GraphState)
    g.add_node("detect", detect_node)
    g.add_node("ensure_ticket", ensure_ticket_node)
    g.add_node("llm", llm_node)
    g.add_node("persist", persist_and_notify_node)

    g.add_edge(START, "detect")
    g.add_edge("detect", "ensure_ticket")
    g.add_edge("ensure_ticket", "llm")
    g.add_edge("llm", "persist")
    g.add_edge("persist", END)

    return g.compile()
