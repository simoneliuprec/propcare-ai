# app/llm.py
import json
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI

SYSTEM_PROMPT = """
You are PropCare AI, a professional property maintenance triage assistant.

GOAL:
Help tenants describe maintenance issues, perform safe basic checks when appropriate, and escalate issues to property management when required.

SAFETY FIRST:
- If there is active fire or smoke, strong gas smell, sparking, major flooding, or immediate danger:
  - Tell the tenant to contact emergency services immediately.
  - Do not continue troubleshooting.
- Never instruct actions involving opening electrical panels, touching wiring or gas lines, disassembling fixtures/appliances, or using tools/force.

TROUBLESHOOTING:
- Ask at most ONE question at a time.
- Provide at most ONE safe, simple step at a time.
- Do not repeat steps the tenant already completed.
- If information is missing, ask a clarifying question.

PHOTOS:
- Request photos only when they materially help diagnosis and are safe to obtain.
- State exactly what to photograph.
""".strip()


def tool_schema_create_ticket() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "create_ticket",
            "description": "Create a maintenance ticket when escalation is required.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["Low", "Medium", "High", "Emergency"]},
                },
                "required": ["summary", "urgency"],
            },
        }
    ]


def extract_tool_call_create_ticket(response) -> Optional[Tuple[str, str]]:
    """
    Returns (summary, urgency) if model produced a tool call.
    """
    for item in getattr(response, "output", []) or []:
        item_type = getattr(item, "type", None)
        name = getattr(item, "name", None)
        arguments = getattr(item, "arguments", None)

        if name is None and hasattr(item, "function"):
            name = getattr(item.function, "name", None)
            arguments = getattr(item.function, "arguments", arguments)

        if item_type in ("function_call", "tool_call") and name == "create_ticket":
            args = json.loads(arguments or "{}")
            return args.get("summary", "").strip(), args.get("urgency", "Medium")

    return None


async def chat_turn(
    client: AsyncOpenAI,
    messages: List[Dict[str, str]],
    temperature: float = 0.4,
):
    """
    Standard model call (no forced tool usage).
    """
    return await client.responses.create(
        model="gpt-4o-mini",
        instructions=SYSTEM_PROMPT,
        input=messages,
        tools=tool_schema_create_ticket(),
        temperature=temperature,
    )


async def force_create_ticket(
    client: AsyncOpenAI,
    messages: List[Dict[str, str]],
    reason: str,
    urgency: str,
):
    """
    Forced tool call pass: guarantees model produces create_ticket call shape.
    """
    return await client.responses.create(
        model="gpt-4o-mini",
        instructions=(
            SYSTEM_PROMPT
            + f"\n\nBACKEND OVERRIDE: Ticket required. Reason: {reason}. Urgency: {urgency}.\n"
              "Call create_ticket now. Output ONLY the tool call."
        ),
        input=messages,
        tools=tool_schema_create_ticket(),
        tool_choice={"type": "function", "name": "create_ticket"},
        temperature=0.2,
    )
