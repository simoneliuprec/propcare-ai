# app/schemas.py
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]
Category = Literal["plumbing", "electrical", "hvac", "appliance", "other"]
Urgency = Literal["P0", "P1", "P2", "P3"]
TicketStatus = Literal["intake", "action_required", "resolved"]

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

class TriageState(BaseModel):
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

class TriageTurn(BaseModel):
    tenant_reply: str
    category: Category
    urgency: Urgency
    status: TicketStatus
    should_notify_manager: bool
    summary_for_ticket: str