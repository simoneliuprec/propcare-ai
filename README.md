# Propcare AI

An end-to-end prototype for **AI-assisted property maintenance triage**:
- **Backend**: FastAPI service that accepts maintenance requests, runs policy/orchestration logic, and sends notifications.
- **Frontend**: Next.js app (App Router) for a simple UI.

## Repository structure

```text
.
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   │   ├── main.py          # FastAPI entrypoint (API routes)
│   │   ├── orchestrator.py  # Orchestration flow (LLM + tools + policies)
│   │   ├── policy.py        # Triage rules/policies
│   │   ├── tools.py         # Tooling functions invoked by orchestration
│   │   ├── llm.py           # LLM client wrapper/helpers
│   │   ├── notifications.py # Notification routing (email, etc.)
│   │   ├── email_resend.py  # Email provider integration (Resend)
│   │   ├── email_templates.py
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── config.py        # Environment/config management
│   ├── tests/               # Pytest tests + fakes
│   └── pytest.ini
└── frontend/                # Next.js frontend
    ├── app/                 # App Router pages/layout
    ├── next.config.ts
    └── eslint.config.mjs
```

---

## Quick start

### 1) Backend (FastAPI)

#### Requirements
- Python 3.11+
- (Recommended) create & activate a virtualenv in `backend/`

#### Install
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt  # if you have one
```

If you don’t have `requirements.txt` yet, generate it from your current env:
```bash
pip freeze > requirements.txt
```

#### Environment variables
Create `backend/.env` (or export env vars in your shell). The backend is typically configured for:
- LLM access (OpenAI)
- Email sending (Resend)
- Optional database (e.g., Supabase) depending on how you implemented `tools.py` / `notifications.py`

Example `backend/.env`:
```env
# --- OpenAI ---
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini  # or your preferred model

# --- Email (Resend) ---
RESEND_API_KEY=your_key_here
EMAIL_FROM="Propcare AI <noreply@yourdomain.com>"
EMAIL_TO="ops@yourcompany.com"

# --- App ---
APP_ENV=dev
LOG_LEVEL=INFO
```

#### Run (dev)
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Backend should be available at:
- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs

---

### 2) Frontend (Next.js)

#### Requirements
- Node.js 18+ (recommended)
- npm / pnpm / yarn

#### Install
```bash
cd frontend
npm install
```

#### Environment variables
Create `frontend/.env.local` if you need to point the UI at your backend:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

#### Run (dev)
```bash
cd frontend
npm run dev
```

Frontend should be available at:
- http://localhost:3000

---

## API overview (backend)

Your FastAPI entrypoint is `backend/app/main.py`. Typical endpoints in this project pattern are:
- `POST /chat` or `POST /triage` — accepts a maintenance payload, runs orchestration, returns a structured result
- `GET /health` — healthcheck

For the canonical list of endpoints, open:
- http://localhost:8000/docs

---

## Backend module guide

- `app/schemas.py`  
  Pydantic models for request/response payloads. Start here to understand input/output contracts.

- `app/policy.py`  
  Deterministic rules (e.g., severity, emergency detection, escalation).

- `app/orchestrator.py`  
  The “brain” that coordinates policies, tool calls (`tools.py`), LLM calls (`llm.py`), and notifications.

- `app/notifications.py` + `app/email_resend.py` + `app/email_templates.py`  
  Notification pipeline:
  1) Create a normalized notification event  
  2) Render email content  
  3) Send via provider integration

---

## Tests

Tests live in `backend/tests/`.

Run:
```bash
cd backend
source venv/bin/activate
pytest -q
```

Common files:
- `tests/test_policy.py` — unit tests for policy logic  
- `tests/test_orchestrator.py` — orchestration behavior with fakes  
- `tests/test_api_chat.py` — API endpoint integration tests (lightweight)  
- `tests/fake_supabase.py` / `tests/fakes.py` — test doubles

---

## Common workflows

### Add a new triage rule
1. Implement the rule in `app/policy.py`
2. Add/adjust related schema fields in `app/schemas.py`
3. Add tests in `tests/test_policy.py`

### Add a new “tool”
1. Implement in `app/tools.py`
2. Register/invoke it from `app/orchestrator.py`
3. Add tests using fakes in `tests/fakes.py`

### Add a new notification channel
1. Extend `app/notifications.py`
2. Add implementation module(s) (email/SMS/etc.)
3. Add tests for routing and payload formation

---

## Notes

- `backend/venv/` and `frontend/node_modules/` should be ignored by git.
- If you see dependency deprecation warnings during tests, treat them as upstream unless behavior breaks.

---

## Roadmap ideas (optional)

- Auth (user login / role-based access)
- Property-aware routing (determine notification recipients by property address)
- Persistent storage (tickets table in Supabase/Postgres)
- Worker/queue for retries and scheduled reminders
- Admin UI for triage review and audit trail
