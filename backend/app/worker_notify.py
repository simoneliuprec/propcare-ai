import time
import os, socket, uuid
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

from .config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    RESEND_API_KEY,
    EMAIL_FROM,
)
from .email_resend import ResendEmailClient, OutboundEmail

POLL_INTERVAL_SECONDS = 1
BATCH_SIZE = 10

WORKER_ID = os.getenv("WORKER_ID") or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def backoff_seconds(attempt: int) -> int:
    # 1m, 2m, 5m, 10m, 30m, 60m (cap)
    schedule = [60, 120, 300, 600, 1800, 3600]
    return schedule[min(attempt, len(schedule) - 1)]


def render_ticket_created(payload: dict) -> tuple[str, str]:
    ticket = (payload or {}).get("ticket") or {}
    tid = ticket.get("id", "(unknown)")
    urgency = ticket.get("urgency", "(n/a)")
    summary = ticket.get("summary", "(n/a)")
    address = ticket.get("property_address", "(n/a)")
    unit = ticket.get("unit", "(n/a)")
    tenant_name = ticket.get("tenant_name", "(n/a)")
    tenant_email = ticket.get("tenant_email", "(n/a)")
    tenant_phone = ticket.get("tenant_phone", "(n/a)")

    subject = f"[PropCare] Ticket #{tid} ({urgency}) created"
    text = (
        "A new maintenance ticket was created.\n\n"
        "Tenant / Contact\n"
        f"Name:  {tenant_name}\n"
        f"Email: {tenant_email}\n"
        f"Phone: {tenant_phone}\n\n"
        "Property\n"
        f"Address: {address}\n"
        f"Unit:    {unit}\n\n"
        "Ticket\n"
        f"Summary: {summary}\n"
        f"Urgency: {urgency}\n\n"
        "This is an automated message.\n"
    )
    return subject, text

def claim_due_pending(supabase: Client):
    # Calls Postgres function: public.claim_due_notifications(worker_id, batch_size)
    res = supabase.rpc(
        "claim_due_notifications",
        {"p_worker_id": WORKER_ID, "p_batch_size": BATCH_SIZE},
    ).execute()
    return res.data or []

def mark_sent(supabase: Client, row_id: int):
    supabase.table("notification_outbox").update({
        "status": "sent",
        "sent_at": utc_now_iso(),
        "last_error": None,
        "locked_at": None,
        "locked_by": None,
    }).eq("id", row_id).execute()


def reschedule_failure(supabase: Client, row_id: int, attempt_count: int, err: Exception):
    next_attempt = attempt_count + 1
    delay = backoff_seconds(next_attempt)
    next_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()

    supabase.table("notification_outbox").update({
        "status": "pending",
        "attempt_count": next_attempt,
        "last_error": str(err),
        "next_attempt_at": next_at,
        "locked_at": None,
        "locked_by": None,
    }).eq("id", row_id).execute()


def main():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    email_client = ResendEmailClient(api_key=RESEND_API_KEY, from_email=EMAIL_FROM)

    print("[worker] started. polling outbox...")

    while True:
        rows = claim_due_pending(supabase)
        for row in rows:
            row_id = row["id"]
            event_type = row.get("event_type")
            to_email = row.get("to_email")
            payload = row.get("payload") or {}
            attempt_count = int(row.get("attempt_count") or 0)

            try:
                if event_type == "ticket.created":
                    subject, text = render_ticket_created(payload)
                else:
                    raise RuntimeError(f"Unknown event_type: {event_type}")

                email_client.send(OutboundEmail(to=to_email, subject=subject, text=text))
                mark_sent(supabase, row_id)
                print(f"[worker] sent {event_type} row={row_id} to={to_email}")

            except Exception as e:
                reschedule_failure(supabase, row_id, attempt_count, e)
                print(f"[worker] failed row={row_id} attempt={attempt_count + 1} err={e}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
