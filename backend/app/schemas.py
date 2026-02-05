# app/schemas.py
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]
Category = Literal["plumbing", "electrical", "hvac", "appliance", "other"]
Urgency = Literal["P0", "P1", "P2", "P3"]
TicketStatus = Literal["intake", "action_required", "resolved"]

Phase = Literal["intake", "gather", "troubleshoot", "summarize", "escalated", "resolved"]

class Message(BaseModel):
    role: Role
    content: str = Field(min_length=1)

class ChatRequest(BaseModel):
    messages: Optional[List[Message]] = None
    message: Optional[str] = None
    history: Optional[List[Message]] = None
    tenant_name: Optional[str] = None
    tenant_email: Optional[str] = None
    tenant_phone: Optional[str] = None
    property_address: Optional[str] = None
    unit: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    ticket_created: bool = False
    ticket_id: Optional[int] = None

class TroubleshootingStep(BaseModel):
    step_id: str = Field(..., description="Stable id for idempotency, e.g. 'check_shutoff_valve'")
    instruction: str = Field(..., description="Tenant-facing instruction (safe, non-invasive)")
    expected_result: Optional[str] = Field(None, description="What tenant should observe")
    stop_if: Optional[str] = Field(None, description="Condition to stop and escalate")

class StepObservation(BaseModel):
    step_id: str
    tenant_result: str
    timestamp_iso: Optional[str] = None

class TriageState(BaseModel):
    # existing
    messages: List[Message]
    ticket_created: bool = False
    ticket_id: Optional[int] = None
    escalation_reason: Optional[str] = None
    escalation_urgency: Optional[str] = None
    tenant_name: Optional[str] = None
    tenant_email: Optional[str] = None
    tenant_phone: Optional[str] = None
    property_address: Optional[str] = None
    unit: Optional[str] = None

    phase: Phase = "intake"
    # extracted working memory (code-owned; LLM may suggest updates)
    facts: Dict[str, Any] = Field(default_factory=dict)
    # deterministic “what do we still need?”
    missing_fields: List[str] = Field(default_factory=list)
    # troubleshooting loop
    plan: List[TroubleshootingStep] = Field(default_factory=list)
    step_index: int = 0
    observations: List[StepObservation] = Field(default_factory=list)
    # media linkage
    media_ids: List[int] = Field(default_factory=list)  # or str, depending on your media table PK

class TriageTurn(BaseModel):
    tenant_reply: str
    category: Category
    urgency: Urgency
    status: TicketStatus
    should_notify_manager: bool
    summary_for_ticket: str
    next_action: Literal["ask", "troubleshoot", "summarize", "await_media"] | None = None
    required_media: Literal["none", "photo", "video"] | None = None
