# app/schemas.py
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]

class Message(BaseModel):
    role: Role
    content: str = Field(min_length=1)

class ChatRequest(BaseModel):
    messages: Optional[List[Message]] = None
    message: Optional[str] = None
    history: Optional[List[Message]] = None

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
