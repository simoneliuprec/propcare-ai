# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from supabase import create_client, Client

from .config import OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from .schemas import ChatRequest, ChatResponse, Message, TriageState
from .orchestrator import run_triage_turn
from .media import router as media_router

app = FastAPI(title="PropCare AI API")

import os

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Inject shared clients for routers/endpoints
@app.middleware("http")
async def inject_clients(request: ChatRequest, call_next):
    request.state.supabase = supabase
    request.state.llm_client = llm_client
    return await call_next(request)

# Mount media routes (e.g., /upload_media)
app.include_router(media_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        if request.messages:
            msgs = request.messages
        else:
            if not request.message:
                raise HTTPException(status_code=400, detail="Provide 'messages' or 'message'.")
            msgs = (request.history or []) + [Message(role="user", content=request.message)]

        state = TriageState(
            messages=msgs,
            tenant_name=request.tenant_name,
            tenant_email=request.tenant_email,
            tenant_phone=request.tenant_phone,
            property_address=request.property_address,
            unit=request.unit,
        )
        state = await run_triage_turn(llm_client, supabase, state)

        # Return latest assistant message as reply
        reply = state.messages[-1].content if state.messages else ""
        return ChatResponse(
            reply=reply,
            ticket_created=state.ticket_created,
            ticket_id=state.ticket_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
