import os
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Set it in your .env file.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# CORS: for dev. In prod, replace with your real domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Role = Literal["user", "assistant"]

class Message(BaseModel):
    role: Role
    content: str = Field(min_length=1)

class ChatRequest(BaseModel):
    # Option 1: structured messages
    messages: Optional[List[Message]] = None

    # Option 2: simple "message + history"
    message: Optional[str] = None
    history: Optional[List[Message]] = None

class ChatResponse(BaseModel):
    reply: str

SYSTEM_PROMPT = """
You are PropCare AI, an expert property maintenance triage assistant.

CRITICAL SAFETY:
- If there is active fire/smoke, strong gas smell, sparking, or major flooding: instruct tenant to call emergency services immediately, then notify property manager.
- Never instruct actions involving opening electrical panels, touching wiring, gas lines, or disassembling equipment.

STRICT TRIAGE MODE:
- For "NO HEAT", follow the required checklist below IN ORDER and do NOT skip steps unless the tenant already completed them.
- Ask at most 1 question at a time.
- Provide 1 safe step at a time.

NO HEAT REQUIRED CHECKLIST (in order):
1) Thermostat: set to HEAT, setpoint above room temp; confirm batteries/display.
2) Vents: at least 1–2 supply vents open (do not force stuck vents).
3) Filter: ask if filter was changed recently; if unknown, ask them to locate it and visually check if clogged. (No tools. No disassembly.)
4) Furnace power switch: confirm ON.
5) Breaker: confirm not tripped (no opening panel beyond flipping breaker fully off/on only if tenant comfortable).
6) For gas furnaces ONLY: ask if they can see the status indicator light through the viewing window and whether pilot light appears OFF. Do NOT instruct relighting. If pilot appears off or error light present → escalate.
7) Listen for start-up sounds (click/hum/fan).
Escalate only after checklist steps are completed OR tenant cannot perform a required step.

Tone: empathetic, concise, professional.

PHOTO EVIDENCE RULES:
- Only request a photo when it materially helps diagnosis.
- When requesting a photo, clearly state WHAT to photograph.
- Never request photos that require opening panels, touching wiring, or handling gas components.
- If a photo is optional, say so.
- Acknowledge receipt of the photo before moving to the next step.

END: If escalating, produce a concise summary of what was checked and results.

""".strip()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Convert your chat history into Responses API "input" items with content blocks
        # Keep the last N messages to control cost and latency
        full_history = []
        for msg in request.messages[-12:]:  # keep last N
            full_history.append({"role": msg.role, "content": msg.content})

        response = await client.responses.create(
            model="gpt-4o-mini",
            instructions=SYSTEM_PROMPT,
            input=full_history,
            temperature=0.4,
        )

        return {"reply": response.output_text}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
