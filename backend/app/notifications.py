# app/notifications.py
from supabase import Client
from datetime import datetime, timezone
from .config import NOTIFICATION_EMAIL

def enqueue_ticket_created(supabase: Client, ticket: dict) -> None:
    if not NOTIFICATION_EMAIL:
        # keep API functioning even if email isn't configured
        return

    ticket_id = int(ticket["id"])
    dedupe_key = f"ticket.created:{ticket_id}"

    payload = {
        "ticket": {
            "id": ticket_id,
            "summary": ticket.get("summary"),
            "urgency": ticket.get("urgency"),
            "status": ticket.get("status"),
            "property_address": ticket.get("property_address"),
            "unit": ticket.get("unit"),
            "tenant_name": ticket.get("tenant_name"),
            "tenant_email": ticket.get("tenant_email"),
            "tenant_phone": ticket.get("tenant_phone"),
        }
    }

    # Insert into outbox (unique dedupe_key prevents duplicates)
    row = {
        "event_type": "ticket.created",
        "ticket_id": ticket_id,         # IMPORTANT: bigint
        "dedupe_key": dedupe_key,
        "to_email": NOTIFICATION_EMAIL,
        "payload": payload,
        "status": "pending",
        "attempt_count": 0,
        "next_attempt_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        supabase.table("notification_outbox").insert(row).execute()
    except Exception as e:
        # If dedupe_key unique constraint hits, ignore; otherwise re-raise
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg:
            return
        raise
