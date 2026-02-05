# app/main.py  (DROP-IN: replace your current file with this)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from supabase import create_client, Client

from .config import OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from .schemas import ChatRequest, ChatResponse, Message, TriageState
from .media import router as media_router

# NEW: LangGraph
from .graph_runtime import get_triage_graph

import os

app = FastAPI(title="PropCare AI API")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

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
async def inject_clients(request: Request, call_next):
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
        # 1) normalize incoming messages
        if request.messages:
            msgs = request.messages
        else:
            if not request.message:
                raise HTTPException(status_code=400, detail="Provide 'messages' or 'message'.")
            msgs = (request.history or []) + [Message(role="user", content=request.message)]

        # 2) build triage state (same as before)
        triage = TriageState(
            messages=msgs,
            tenant_name=request.tenant_name,
            tenant_email=request.tenant_email,
            tenant_phone=request.tenant_phone,
            property_address=request.property_address,
            unit=request.unit,
        )

        # 3) LangGraph invoke (replaces run_triage_turn)
        graph = get_triage_graph(llm_client, supabase)
        out = await graph.ainvoke({"triage": triage})

        # 4) reply (prefer graph output; fallback to last assistant msg)
        reply = out.get("tenant_reply") or (triage.messages[-1].content if triage.messages else "")
        return ChatResponse(
            reply=reply,
            ticket_created=triage.ticket_created,
            ticket_id=triage.ticket_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
