# app/tools.py
from supabase import Client

def create_ticket(supabase: Client, summary: str, urgency: str) -> int:
    payload = {"summary": summary, "urgency": urgency, "status": "open"}
    print("SUPABASE insert payload:", payload)
    """
    Tool/action: creates a ticket in Supabase. Returns ticket id.
    """
    res = supabase.table("tickets").insert({
        "summary": summary,
        "urgency": urgency,
        "status": "open",
    }).execute()
    print("SUPABASE insert response data:", res.data)

    if not res.data:
        raise RuntimeError("Supabase insert returned no data.")
    return int(res.data[0]["id"])
