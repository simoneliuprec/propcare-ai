from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form

from .config import IMAGE_VERIFIER_ID, MEDIA_BUCKET, MEDIA_SIGNED_URL_TTL_SECONDS
from .media_verify import verify_image

router = APIRouter()

MAX_BYTES = 25 * 1024 * 1024  # 25MB

def _media_type_from_mime(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    return "unknown"


def _signed_url(supabase, bucket: str, path: str, ttl: int) -> Optional[str]:
    try:
        r = supabase.storage.from_(bucket).create_signed_url(path, ttl)
    except Exception:
        return None

    # supabase-py versions vary
    if isinstance(r, dict):
        return r.get("signedURL") or r.get("signed_url") or r.get("signedUrl") or r.get("url")
    data = getattr(r, "data", None)
    if isinstance(data, dict):
        return data.get("signedURL") or data.get("signed_url") or data.get("signedUrl") or data.get("url")
    return None


@router.post("/upload_media")
async def upload_media(
    request: Request,
    ticket_id: int = Form(...),
    issue_context: str = Form(""),
    file: UploadFile = File(...),
):
    print("UPLOAD_MEDIA hit:", {"ticket_id": ticket_id, "filename": file.filename, "mime": file.content_type})

    supabase = request.state.supabase
    llm_client = request.state.llm_client
    if supabase is None or llm_client is None:
        raise HTTPException(500, "Server misconfigured")

    # Ensure ticket exists (avoid FK failure / orphan storage)
    try:
        t = supabase.table("tickets").select("id").eq("id", ticket_id).limit(1).execute()
        if not t.data:
            raise HTTPException(404, f"Ticket not found: {ticket_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ticket lookup failed: {e}")

    mime = file.content_type or ""
    mtype = _media_type_from_mime(mime)
    if mtype == "unknown":
        raise HTTPException(400, f"Unsupported content type: {mime}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty upload")
    if len(data) > MAX_BYTES:
        raise HTTPException(400, f"File too large (>{MAX_BYTES} bytes)")

    # Store in Supabase Storage (private bucket)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", file.filename or "upload")[:120]
    path = f"tickets/{ticket_id}/{ts}_{safe_name}"

    try:
        resp = supabase.storage.from_(MEDIA_BUCKET).upload(
            path,
            data,
            file_options={"content-type": mime, "upsert": False},
        )
        # best-effort detect error payloads
        if isinstance(resp, dict) and resp.get("error"):
            raise Exception(resp["error"])
    except Exception as e:
        raise HTTPException(500, f"Storage upload failed: {e}")

    # Verify images only (basic MVP). Videos can be "accepted" without verification for now.
    is_valid: Optional[bool] = None
    reason: Optional[str] = None
    verifier = None
    verified_at = None

    if mtype == "image":
        try:
            verdict = await verify_image(
                llm_client,
                issue_context=issue_context,
                image_bytes=data,
                mime_type=mime,
            )
            is_valid = bool(verdict.get("is_valid"))
            reason = (verdict.get("reason") or "")[:500]
            verifier = IMAGE_VERIFIER_ID
            verified_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            is_valid = None
            reason = f"verification_error: {str(e)[:450]}"
            verifier = IMAGE_VERIFIER_ID
            verified_at = None

    # Insert DB row
    row = {
        "ticket_id": ticket_id,
        "media_type": mtype,
        "storage_bucket": MEDIA_BUCKET,
        "storage_path": path,
        "mime_type": mime,
        "byte_size": len(data),
        "original_filename": file.filename,
        "is_valid": is_valid,
        "invalid_reason": reason,
        "verifier": verifier,
        "verified_at": verified_at,
    }

    try:
        res = supabase.table("ticket_media").insert(row).execute()
        media_row = res.data[0] if res.data else None
    except Exception as e:
        # cleanup to avoid orphan storage objects
        try:
            supabase.storage.from_(MEDIA_BUCKET).remove([path])
        except Exception:
            pass
        raise HTTPException(500, f"DB insert failed: {e}")

    signed_url = _signed_url(supabase, MEDIA_BUCKET, path, MEDIA_SIGNED_URL_TTL_SECONDS)

    return {
        "ok": True,
        "media_id": media_row["id"] if media_row else None,
        "is_valid": is_valid,
        "reason": reason,
        "storage_path": path,
        "signed_url": signed_url,   # ✅ frontend can now display the image
        "media_type": mtype,
    }
