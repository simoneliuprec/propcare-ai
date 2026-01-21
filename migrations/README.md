# Database Migrations

This folder contains all database schema migrations for PropCare AI.

## Applying migrations (development)

1. Open Supabase Dashboard
2. Go to SQL Editor
3. Run migration files in numeric order:
   - 001_create_tickets.sql
   - 002_create_notification_outbox.sql
   - 003_add_outbox_locking.sql

## Notes

- Migrations are append-only
- Do not edit old migration files
- New schema changes require a new migration
