-- 001_create_tickets.sql
-- Purpose: core maintenance tickets (agent-ready, enum-safe)

-- 0) Status enum (idempotent)
do $$
begin
  if not exists (select 1 from pg_type where typname = 'ticket_status') then
    create type public.ticket_status as enum ('intake', 'action_required', 'resolved');
  end if;
end$$;

create table if not exists public.tickets (
  id bigint generated always as identity primary key,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_activity_at timestamptz,
  last_turn_at timestamptz,
  resolved_at timestamptz,

  summary text not null,
  urgency text,
  status public.ticket_status not null default 'intake',

  -- agent state (LangGraph / AgentState)
  state_json jsonb not null default '{}'::jsonb,

  tenant_name text,
  tenant_email text,
  tenant_phone text,

  property_address text,
  unit text,

  source text,
  external_ref text
);

create index if not exists idx_tickets_status on public.tickets (status);
create index if not exists idx_tickets_created_at on public.tickets (created_at);
create index if not exists idx_tickets_last_turn_at on public.tickets (last_turn_at);
create index if not exists idx_tickets_state_json on public.tickets using gin (state_json);
