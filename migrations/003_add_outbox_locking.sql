-- 003_add_outbox_locking.sql
-- Purpose: safe concurrent workers (SKIP LOCKED)

alter table public.notification_outbox
  add column if not exists locked_at timestamptz,
  add column if not exists locked_by text;

create or replace function public.claim_due_notifications(
  p_worker_id text,
  p_batch_size int default 10
)
returns setof public.notification_outbox
language plpgsql
security definer
as $$
begin
  return query
  with picked as (
    select n.id
    from public.notification_outbox n
    where
      (
        n.status = 'pending'
        and n.next_attempt_at <= now()
      )
      or
      (
        -- reclaim stuck jobs (worker crashed mid-send)
        n.status = 'processing'
        and n.locked_at < now() - interval '2 minutes'
      )
    order by n.created_at asc
    for update skip locked
    limit p_batch_size
  ),
  updated as (
    update public.notification_outbox n
    set
      status   = 'processing',
      locked_at = now(),
      locked_by = p_worker_id
    from picked
    where n.id = picked.id
    returning n.*
  )
  select * from updated;
end;
$$;
