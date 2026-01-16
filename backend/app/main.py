# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from supabase import create_client, Client

from .config import OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from .schemas import ChatRequest, ChatResponse, Message, TriageState
from .orchestrator import run_triage_turn

app = FastAPI(title="PropCare AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("=== PropCare API booted: main.py loaded ===", flush=True)

llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        if request.messages:
            msgs = request.messages
        else:
            if not request.message:
                raise HTTPException(status_code=400, detail="Provide 'messages' or 'message'.")
            msgs = (request.history or []) + [Message(role="user", content=request.message)]

        state = TriageState(messages=msgs)
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
