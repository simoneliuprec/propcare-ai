# app/tools.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from supabase import Client


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_ticket_record(
    supabase: Client,
    *,
    summary: str,
    urgency: Optional[str] = None,          # e.g. "P2_SOON" (DB format)
    status: str = "intake",                 # "intake" | "action_required" | "resolved"
    category: Optional[str] = None,         # plumbing/electrical/hvac/appliance/other
    issue_details: Optional[str] = None,    # richer internal notes (optional)
    tenant_name: Optional[str] = None,
    tenant_email: Optional[str] = None,
    tenant_phone: Optional[str] = None,
    property_address: Optional[str] = None,
    unit: Optional[str] = None,
    property_id: Optional[str] = None,      # capture soon
    source: str = "web",
    external_ref: Optional[str] = None,     # for thread key later (optional)
) -> Dict[str, Any]:
    """
    Creates one 'issue thread' ticket. In the new flow you create this early
    and then update it every turn.
    """
    payload: Dict[str, Any] = {
        "summary": summary,
        "status": status,
        "source": source,
        "updated_at": utc_now_iso(),
        "last_activity_at": utc_now_iso(),
    }

    if urgency is not None:
        payload["urgency"] = urgency
    if category is not None:
        payload["category"] = category
    if issue_details is not None:
        payload["issue_details"] = issue_details
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
    if property_id:
        payload["property_id"] = property_id
    if external_ref:
        payload["external_ref"] = external_ref

    res = supabase.table("tickets").insert(payload).execute()
    if not res.data:
        raise RuntimeError("Supabase insert returned no data.")
    return res.data[0]


def update_ticket_record(
    supabase: Client,
    *,
    ticket_id: int,
    summary: Optional[str] = None,
    urgency: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    issue_details: Optional[str] = None,
    resolved: bool = False,
) -> Dict[str, Any]:
    """
    Updates an existing ticket each turn. Use this instead of re-inserting.
    """
    patch: Dict[str, Any] = {
        "updated_at": utc_now_iso(),
        "last_activity_at": utc_now_iso(),
    }

    if summary is not None:
        patch["summary"] = summary
    if urgency is not None:
        patch["urgency"] = urgency
    if status is not None:
        patch["status"] = status
    if category is not None:
        patch["category"] = category
    if issue_details is not None:
        patch["issue_details"] = issue_details
    if resolved:
        patch["resolved_at"] = utc_now_iso()

    res = supabase.table("tickets").update(patch).eq("id", ticket_id).execute()
    if not res.data:
        # If Supabase returns nothing, keep it explicit
        raise RuntimeError(f"Supabase update returned no data for ticket_id={ticket_id}.")
    return res.data[0]
