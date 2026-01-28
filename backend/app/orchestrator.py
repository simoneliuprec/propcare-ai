# app/orchestrator.py
from __future__ import annotations

from typing import Dict, List
from datetime import datetime, timezone

from openai import AsyncOpenAI
from supabase import Client

from .schemas import Message, TriageState, TriageTurn
from .tools import create_ticket_record, update_ticket_record
from .notifications import enqueue_ticket_event
from .llm import chat_turn_json
from .policy import detect_emergency

def _to_openai_messages(msgs: List[Message], keep_last: int = 12) -> List[Dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in msgs[-keep_last:]]

def _latest_user_text(msgs: List[Message]) -> str:
    for m in reversed(msgs):
        if m.role == "user":
            return m.content or ""
    return ""

# Map LLM urgency (P0–P3) to your DB urgency strings
URGENCY_MAP = {
    "P0": "P0_EMERGENCY",
    "P1": "P1_URGENT",
    "P2": "P2_SOON",
    "P3": "P3_ROUTINE",
}

def _append_detail(prev: str | None, line: str) -> str:
    base = (prev or "").strip()
    if not base:
        return line
    return base + "\n" + line

async def run_triage_turn(llm_client: AsyncOpenAI, supabase: Client, state: TriageState) -> TriageState:
    msgs = state.messages
    openai_msgs = _to_openai_messages(msgs)
    latest_text = _latest_user_text(msgs)

    # 0) Deterministic P0 detection (latest user message only)
    is_emergency, emergency_type, emergency_reason = detect_emergency(latest_text)

    # 1) Ensure we have one ticket per issue thread (create early, then update every turn)
    if not state.ticket_id:
        # Create an "intake" ticket immediately (supports "always log")
        init_summary = f"Tenant report: {latest_text}".strip()[:5000]
        ticket = create_ticket_record(
            supabase,
            summary=init_summary,
            urgency=URGENCY_MAP["P2"],   # default; may be overridden after LLM output
            status="intake",
            tenant_name=state.tenant_name,
            tenant_email=state.tenant_email,
            tenant_phone=state.tenant_phone,
            property_address=state.property_address,
            unit=state.unit,
            source="web",
        )
        state.ticket_created = True
        state.ticket_id = int(ticket["id"])

        # Optional: only if you actually want an email on ticket creation.
        # Most teams do NOT email on creation; they email when action_required.
        # enqueue_ticket_event(supabase, event_type="ticket.created", ticket=ticket)

    ticket_id = int(state.ticket_id)

    # 2) Call LLM ALWAYS (even emergency) to produce tenant-facing text + structured fields
    extra = (
        "CONTEXT (not tenant-facing):\n"
        f"- Tenant name: {state.tenant_name or ''}\n"
        f"- Tenant email: {state.tenant_email or ''}\n"
        f"- Tenant phone: {state.tenant_phone or ''}\n"
        f"- Property address: {state.property_address or ''}\n"
        f"- Unit: {state.unit or ''}\n"
        f"- Ticket id: {ticket_id}\n"
    )

    if is_emergency:
        extra += (
            "\nBACKEND:\n"
            f"- emergency=true\n"
            f"- emergency_type={emergency_type}\n"
            "RULES:\n"
            "- Enter EMERGENCY MODE: give brief BC safety guidance, stop troubleshooting, ask exactly ONE safety confirmation question.\n"
            "- If gas-related, mention FortisBC Emergency Line 1-800-663-9911 (call from outside, once safe).\n"
            "- Set status=action_required and should_notify_manager=true.\n"
        )

    turn = await chat_turn_json(
        llm_client,
        openai_msgs,
        temperature=0.2 if is_emergency else 0.3,
        extra_instructions=extra,
    )

    print("DEBUG TriageTurn:", turn)

    # 3) Deterministic overrides (safety wins)
    category = turn.category
    urgency = turn.urgency
    status = turn.status
    should_notify = turn.should_notify_manager
    summary = turn.summary_for_ticket.strip()
    tenant_reply = turn.tenant_reply.strip()

    if is_emergency:
        urgency = "P0"
        status = "action_required"
        should_notify = True
        if not summary:
            summary = f"[EMERGENCY:{emergency_type}] {emergency_reason} Tenant said: {latest_text}"

    db_urgency = URGENCY_MAP.get(urgency, URGENCY_MAP["P2"])

    # 4) Persist: update ticket every turn (summary/category/urgency/status + running issue_details)
    now = datetime.now(timezone.utc).isoformat()
    detail_line = f"{now}Z | user: {latest_text}"
    # Pull current issue_details so we can append (simple approach)
    # If you don’t want the extra read, skip and just overwrite issue_details with summary.
    existing = supabase.table("tickets").select("issue_details").eq("id", ticket_id).limit(1).execute()
    prev_details = existing.data[0].get("issue_details") if existing.data else None
    new_details = _append_detail(prev_details, detail_line)

    ticket = update_ticket_record(
        supabase,
        ticket_id=ticket_id,
        summary=summary or f"Tenant report: {latest_text}",
        urgency=db_urgency,
        status=status,
        category=category,
        issue_details=new_details,
        resolved=(status == "resolved"),
    )

    # 5) Notify only when needed (emergency or action_required)
    if should_notify and status == "action_required":
        enqueue_ticket_event(
            supabase,
            event_type="ticket.action_required" if not is_emergency else "ticket.emergency",
            ticket=ticket,
            # later: to_email=resolved_by_property_mapping(...)
            # For now uses NOTIFICATION_EMAIL from config
        )

    # 6) Append assistant reply to conversation state
    state.messages.append(Message(role="assistant", content=tenant_reply))
    state.ticket_created = True
    state.ticket_id = ticket_id

    return state
