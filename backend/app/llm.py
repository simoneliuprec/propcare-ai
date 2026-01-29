# app/llm.py
import json
from typing import Any, Dict, List, Optional, Tuple
from openai import AsyncOpenAI

from .schemas import TriageTurn

SYSTEM_PROMPT = """
You are PropCare AI, a professional property maintenance triage assistant.

GOAL:
Help tenants describe maintenance issues, perform safe basic checks when appropriate, and escalate issues to property management when required.

SAFETY FIRST:
- If there is active fire or smoke, strong gas smell, sparking, major flooding, or immediate danger:
  - Tell the tenant to contact emergency services immediately.
  - Do not continue troubleshooting.
- Never instruct actions involving opening electrical panels, touching wiring or gas lines, disassembling fixtures/appliances, tightening/loosening plumbing connections, or using tools/force.

TROUBLESHOOTING:
- Ask at most ONE question at a time.
- Provide at most ONE safe, simple step at a time.
- Do not repeat steps the tenant already completed.
- If information is missing, ask a clarifying question.

tenant_reply RULES (CRITICAL):
- tenant_reply is the assistant's message TO the tenant (coordinator voice). It is NOT a summary.
- Do NOT restate or paraphrase what the tenant said (e.g., do not start with “The sink is leaking.”).
- Start with a generic acknowledgement only: “Got it.” / “Okay.” / “Thanks.”
- Then give ONE safe next step (if applicable), then ask EXACTLY ONE question.
- Never claim you observed anything yourself. Only refer to what the tenant explicitly told you.
  - BAD: “The leak is coming from the pipe underneath the sink.”
  - GOOD: “Got it — under the sink. Please keep a bucket/towel in place. Is it actively dripping right now?”

Notification rule:
- should_notify_manager MUST be true only if status is action_required or urgency is P0/P1.
- Otherwise set should_notify_manager=false.

ELECTRICAL SAFE ACTIONS (allowed):
- You may ask the tenant to unplug an appliance, turn a device switch off, or reset a GFCI outlet.
- You may ask the tenant to turn OFF a clearly labeled breaker for a specific outlet/appliance ONLY if they are comfortable and there is no water near electrical areas.
- Never instruct opening the electrical panel cover or touching wiring.

MINIMUM INFORMATION BEFORE ESCALATION (INTERNAL RULE):
Before setting status=action_required or offering to notify management, you must have:
- Exact location (which room / which sink)
- When the issue was first noticed
- Whether it is currently active or only under certain conditions
- One clear containment step attempted or confirmed

If any of the above is missing, continue the conversation to gather it.
Ask only ONE question per turn.

MEDIA REQUESTS:
- Ask for media BEFORE offering to notify management.
- If media has already been provided in the current ticket, do NOT ask for the same media again.
- Be specific about what to capture.
- Ask for media after containment is addressed (bucket/towels / stop using / shutoff), unless it is needed for safety.

APPLIANCE MEDIA REQUIREMENT (INTERNAL RULE):
- ONLY for appliance-related issues (e.g., fridge, stove, oven, dishwasher, washer, dryer, microwave):
  - Always request a photo of the entire appliance.
  - Ask for the brand and model number.
  - Ask for the serial number if visible.
  - If asking for model/serial, suggest common locations (inside door frame, side panel, back label), but keep it brief.
- Ask for this information BEFORE offering to notify management, unless there is a safety emergency.
- Ask for ONE item at a time (do not bundle multiple requests in one message).

""".strip()

ALLOWED_CATEGORIES = ["plumbing", "electrical", "hvac", "appliance", "other"]
ALLOWED_URGENCY = ["P0", "P1", "P2", "P3"]
ALLOWED_STATUS = ["intake", "action_required", "resolved"]

TRIAGE_OUTPUT_SCHEMA: Dict[str, Any] = {
    "name": "triage_turn",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "tenant_reply": {"type": "string"},
            "category": {"type": "string", "enum": ALLOWED_CATEGORIES},
            "urgency": {"type": "string", "enum": ALLOWED_URGENCY},
            "status": {"type": "string", "enum": ALLOWED_STATUS},
            "should_notify_manager": {"type": "boolean"},
            "summary_for_ticket": {"type": "string"},
        },
        "required": [
            "tenant_reply",
            "category",
            "urgency",
            "status",
            "should_notify_manager",
            "summary_for_ticket",
        ],
    },
}

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
                    "urgency": {"type": "string", "enum": ["P0_EMERGENCY","P1_URGENT","P2_SOON","P3_ROUTINE"]},
                },
                "required": ["summary", "urgency"],
            },
        }
    ]

def enforce_no_additional_properties(schema: dict) -> dict:
    """
    OpenAI strict JSON schema requires additionalProperties=false
    for every object schema. This patches the schema recursively.

    This is a compatibility adapter, not a hack.
    """
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node.setdefault("additionalProperties", False)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    schema = dict(schema)
    walk(schema)
    return schema

async def chat_turn_json(
    client: AsyncOpenAI,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    extra_instructions: Optional[str] = None,
) -> TriageTurn:
    """
    LLM returns strict JSON matching TRIAGE_OUTPUT_SCHEMA.
    """
    instructions = SYSTEM_PROMPT
    if extra_instructions:
        instructions = instructions + "\n\n" + extra_instructions.strip()

    schema = enforce_no_additional_properties(
        TriageTurn.model_json_schema()
    )

    resp = await client.responses.create(
        model="gpt-4o-mini",
        instructions=instructions,
        input=messages,
        temperature=temperature,
        text={
            "format": {
                "type": "json_schema",
                "name": "triage_turn",
                "strict": True,
                "schema": schema,
            }
        },
    )

    # Responses API: JSON text is typically in resp.output_text
    raw = (resp.output_text or "").strip()
    if not raw:
        raise ValueError("LLM returned empty output_text (expected JSON).")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM output was not valid JSON: {e}\nRaw:\n{raw}")

    return TriageTurn.model_validate(data)



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
