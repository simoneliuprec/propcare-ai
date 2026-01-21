-- 002_create_notification_outbox.sql
-- Purpose: transactional outbox for notifications

create table if not exists public.notification_outbox (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),

  event_type text not null,
  ticket_id bigint references public.tickets(id) on delete cascade,

  to_email text not null,
  payload jsonb not null,

  status text not null default 'pending',
  attempt_count int not null default 0,

  next_attempt_at timestamptz not null default now(),
  sent_at timestamptz,
  last_error text
);

create index if not exists idx_outbox_pending
  on public.notification_outbox (status, next_attempt_at);

create index if not exists idx_outbox_ticket_id
  on public.notification_outbox (ticket_id);
