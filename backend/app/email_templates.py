# backend/app/email_templates.py

def _get(ticket: dict, *keys: str, default: str = "(n/a)") -> str:
    for k in keys:
        v = ticket.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return default

def render_ticket_created(ticket: dict) -> tuple[str, str]:
    tid = _get(ticket, "id", default="(unknown)")
    urgency = _get(ticket, "urgency", default="(n/a)")
    summary = _get(ticket, "summary", "issue_summary", default="(n/a)")
    address = _get(ticket, "property_address", "address", default="(n/a)")
    unit = _get(ticket, "unit", default="(n/a)")

    tenant_name = _get(ticket, "tenant_name", "contact_name", "requester_name", default="(n/a)")
    tenant_phone = _get(ticket, "tenant_phone", "contact_phone", "phone", default="(n/a)")
    tenant_email = _get(ticket, "tenant_email", "contact_email", "email", default="(n/a)")

    subject = f"[Maintenance] New ticket {tid} ({urgency})"

    body = (
        "A new maintenance ticket was created.\n\n"
        "Tenant / Contact\n"
        f"Name:  {tenant_name}\n"
        f"Phone: {tenant_phone}\n"
        f"Email: {tenant_email}\n"
        "\n"
        "Ticket\n"
        f"Ticket ID: {tid}\n"
        f"Urgency:   {urgency}\n"
        f"Address:   {address}\n"
        f"Unit:      {unit}\n"
        f"Summary:   {summary}\n"
        "\n"
        "This is an automated message. Please do not reply.\n"
    )
    return subject, body
