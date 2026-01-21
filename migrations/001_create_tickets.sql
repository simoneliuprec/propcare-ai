-- 001_create_tickets.sql
-- Purpose: core maintenance tickets

create table if not exists public.tickets (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),

  summary text not null,
  urgency text,
  status text not null default 'open',

  tenant_name text,
  tenant_email text,
  tenant_phone text,

  property_address text,
  unit text,

  source text,
  external_ref text,

  updated_at timestamptz default now(),
  last_activity_at timestamptz,
  resolved_at timestamptz
);

create index if not exists idx_tickets_status
  on public.tickets (status);

create index if not exists idx_tickets_created_at
  on public.tickets (created_at);
