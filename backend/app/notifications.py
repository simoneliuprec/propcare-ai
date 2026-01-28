# app/notifications.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from supabase import Client
from .config import NOTIFICATION_EMAIL


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def enqueue_notification(
    supabase: Client,
    *,
    event_type: str,
    ticket_id: int,
    to_email: str,
    payload: Dict[str, Any],
    dedupe_key: str,
) -> None:
    """
    Inserts a row into notification_outbox.
    Assumes notification_outbox has a unique constraint on dedupe_key.
    """
    row = {
        "event_type": event_type,
        "ticket_id": int(ticket_id),
        "dedupe_key": dedupe_key,
        "to_email": to_email,
        "payload": payload,
        "status": "pending",
        "attempt_count": 0,
        "next_attempt_at": utc_now_iso(),
    }

    try:
        supabase.table("notification_outbox").insert(row).execute()
    except Exception as e:
        msg = str(e).lower()
        # Ignore dedupe collisions (idempotent behavior)
        if "duplicate" in msg or "unique" in msg:
            return
        raise


def enqueue_ticket_event(
    supabase: Client,
    *,
    event_type: str,
    ticket: Dict[str, Any],
    to_email: Optional[str] = None,
    dedupe_suffix: Optional[str] = None,
) -> None:
    """
    Convenience wrapper for ticket-related events. Keeps payload shape consistent.
    """
    if not (to_email or NOTIFICATION_EMAIL):
        return

    to_email_final = to_email or NOTIFICATION_EMAIL
    ticket_id = int(ticket["id"])

    # Dedupe key strategy:
    # - For 'ticket.created' -> one-time per ticket
    # - For 'ticket.action_required' -> one-time per status transition
    # - For 'ticket.emergency' -> one-time per ticket (or per turn if you add suffix)
    suffix = dedupe_suffix or ""
    dedupe_key = f"{event_type}:{ticket_id}{(':' + suffix) if suffix else ''}"

    payload = {
        "ticket": {
            "id": ticket_id,
            "summary": ticket.get("summary"),
            "urgency": ticket.get("urgency"),
            "status": ticket.get("status"),
            "category": ticket.get("category"),
            "property_address": ticket.get("property_address"),
            "unit": ticket.get("unit"),
            "tenant_name": ticket.get("tenant_name"),
            "tenant_email": ticket.get("tenant_email"),
            "tenant_phone": ticket.get("tenant_phone"),
            "property_id": ticket.get("property_id"),
        }
    }

    enqueue_notification(
        supabase,
        event_type=event_type,
        ticket_id=ticket_id,
        to_email=to_email_final,
        payload=payload,
        dedupe_key=dedupe_key,
    )
