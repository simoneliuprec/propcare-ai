# app/orchestrator.py
from typing import Dict, List
from openai import AsyncOpenAI
from supabase import Client

from .schemas import Message, TriageState
from .policy import should_escalate
from .tools import create_ticket
from .llm import chat_turn, force_create_ticket, extract_tool_call_create_ticket

def _to_openai_messages(msgs: List[Message], keep_last: int = 12) -> List[Dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in msgs[-keep_last:]]

async def run_triage_turn(llm_client: AsyncOpenAI, supabase: Client, state: TriageState) -> TriageState:
    msgs = state.messages
    openai_msgs = _to_openai_messages(msgs)

    # 0) Pre-check escalation BEFORE calling the model (prevents "choose urgency" questions)
    needs_ticket, urgency, reason = should_escalate(msgs)
    if needs_ticket:
        summary = f"{reason} | Tenant report: {msgs[-1].content}"
        ticket_id = create_ticket(supabase, summary=summary, urgency=urgency)

        state.ticket_created = True
        state.ticket_id = ticket_id
        state.escalation_reason = reason
        state.escalation_urgency = urgency

        state.messages.append(Message(
            role="assistant",
            content="Thanks — I’ve created a maintenance ticket. Your property manager will follow up shortly."
        ))
        return state

    # 1) Normal model response (troubleshooting)
    resp = await chat_turn(llm_client, openai_msgs)
    reply_text = resp.output_text or ""

    # 1a) If model voluntarily called create_ticket (optional path), execute it
    tool_call = extract_tool_call_create_ticket(resp)
    if tool_call:
        summary, tool_urgency = tool_call
        final_urgency = tool_urgency or "Medium"
        final_summary = summary.strip() or f"Tenant report: {msgs[-1].content}"

        ticket_id = create_ticket(supabase, summary=final_summary, urgency=final_urgency)
        state.ticket_created = True
        state.ticket_id = ticket_id

        state.messages.append(Message(
            role="assistant",
            content="Thanks — I’ve created a maintenance ticket. Your property manager will follow up shortly."
        ))
        return state

    # 2) Return normal reply
    state.messages.append(Message(role="assistant", content=reply_text))
    return state
