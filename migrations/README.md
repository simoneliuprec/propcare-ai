# Database Migrations

This folder contains all **append-only database schema migrations** for PropCare AI.

The database schema is designed to support a **hybrid agentic architecture**:
- Deterministic routing and safety logic in code
- LLM-assisted conversation and summarization
- Persistent, auditable AgentState stored with each ticket
- Media uploads linked to tickets
- Asynchronous notification processing

---

## Applying migrations (development)

1. Open the **Supabase Dashboard**
2. Navigate to **SQL Editor**
3. Run migration files **in numeric order**:

   - `001_create_tickets.sql`  
     Creates the core `tickets` table, including:
     - Enum-backed `status` (`intake | action_required | resolved`)
     - Persistent `state_json` column for AgentState (LangGraph)
     - Timestamps for agent activity tracking

   - `002_create_notification_outbox.sql`  
     Creates the notification outbox table used for async email / webhook dispatch.

   - `003_add_outbox_locking.sql`  
     Adds locking and concurrency safety for background notification workers.

4. (Optional, if present) Run media-related migrations:
   - Media uploads are stored in Supabase Storage and linked via a `media` table.

---

## Key Schema Concepts

### Tickets (`public.tickets`)
Each ticket represents **one maintenance issue thread** and serves as the durable anchor for agent behavior.

Important columns:
- `status` (enum): lifecycle state (`intake`, `action_required`, `resolved`)
- `state_json` (jsonb): persistent AgentState used by LangGraph
- `summary`: owner / manager–facing summary
- `urgency`: mapped urgency (`P0_EMERGENCY` → `P3_ROUTINE`)
- `last_turn_at`: timestamp of the most recent agent turn

> `state_json` stores structured agent memory such as:
> - conversation phase
> - extracted facts
> - missing information
> - troubleshooting plan + progress
> - linked media IDs

---

## Migration Rules (Important)

- **Migrations are append-only**
- **Never edit existing migration files** once applied
- Any new schema change must be introduced via a **new numbered migration**
- Enum changes (e.g., adding a new ticket status) require explicit `ALTER TYPE` migrations

---

## Compatibility Notes

- Older tickets with legacy statuses (e.g., `open`) are normalized during migration.
- The schema is forward-compatible with LangGraph-based orchestration.
- Application code must treat `state_json` as code-owned AgentState; the LLM never writes directly to the database.

---

## Recommended Workflow

- Add new features → update application code
- If schema changes are needed → create a new migration file
- Apply migrations locally in Supabase SQL Editor
- Commit migrations alongside the code change

---

This schema is intentionally minimal but **agent-ready**, enabling safe iteration toward more advanced automation without breaking existing data.
