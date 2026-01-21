# app/tools.py
from supabase import Client
from typing import Optional, Dict, Any

def create_ticket(supabase: Client, summary: str, urgency: Optional[str] = None, **kwargs) -> int:
    ticket = create_ticket_record(supabase, summary=summary, urgency=urgency, **kwargs)
    return int(ticket["id"])

def create_ticket_record(
    supabase: Client,
    summary: str,
    urgency: Optional[str] = None,
    *,
    tenant_name: Optional[str] = None,
    tenant_email: Optional[str] = None,
    tenant_phone: Optional[str] = None,
    property_address: Optional[str] = None,
    unit: Optional[str] = None,
    source: str = "web",
) -> Dict[str, Any]:
    payload = {
        "summary": summary,
        "status": "open",
        "source": source,
    }
    if urgency is not None:
        payload["urgency"] = urgency
    if tenant_name:
        payload["tenant_name"] = tenant_name
    if tenant_email:
        payload["tenant_email"] = tenant_email
    if tenant_phone:
        payload["tenant_phone"] = tenant_phone
    if property_address:
        payload["property_address"] = property_address
    if unit:
        payload["unit"] = unit

    print("SUPABASE insert payload:", payload)
    res = supabase.table("tickets").insert(payload).execute()
    print("SUPABASE insert response data:", res.data)

    if not res.data:
        raise RuntimeError("Supabase insert returned no data.")
    return res.data[0]