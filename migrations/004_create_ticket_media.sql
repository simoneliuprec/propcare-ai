-- 004_create_ticket_media.sql
-- Purpose: store photo/video uploads linked to maintenance tickets

-- UUID generator (Supabase/Postgres typically supports pgcrypto)
create extension if not exists pgcrypto;

create table if not exists public.ticket_media (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),

  -- FK to tickets.id (BIGINT identity)
  ticket_id bigint not null references public.tickets(id) on delete cascade,

  media_type text not null check (media_type in ('image', 'video')),
  mime_type text not null,
  byte_size integer not null check (byte_size >= 0),

  storage_bucket text not null,
  storage_path text not null,

  original_filename text,

  -- Image verification (MVP: images only; videos can remain null)
  is_valid boolean,
  invalid_reason text,
  verifier text,
  verified_at timestamptz
);

-- Indexes for common queries
create index if not exists idx_ticket_media_ticket_id_created_at
  on public.ticket_media (ticket_id, created_at desc);

create index if not exists idx_ticket_media_storage
  on public.ticket_media (storage_bucket, storage_path);

-- Prevent duplicate records for the same stored object
create unique index if not exists uq_ticket_media_storage_object
  on public.ticket_media (storage_bucket, storage_path);

-- Recommended: enable RLS (service role bypasses, keeps you safe if later using anon/auth keys)
alter table public.ticket_media enable row level security;

-- NOTE:
-- If you are inserting via the Supabase SERVICE ROLE key from your backend,
-- you do NOT need policies for inserts/selects for now.
-- Add policies later if you want tenant-facing media browsing via anon/auth keys.
