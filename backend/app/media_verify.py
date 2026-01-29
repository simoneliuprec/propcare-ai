# backend/app/media_verify.py
from __future__ import annotations

import base64
import json
from typing import Dict

from openai import AsyncOpenAI


def _to_data_url(image_bytes: bytes, mime_type: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _extract_text(resp) -> str:
    """
    Best-effort extraction across OpenAI SDK response shapes.
    """
    # Newer SDKs often have .output_text
    t = getattr(resp, "output_text", None)
    if isinstance(t, str) and t.strip():
        return t

    # Otherwise walk resp.output[*].content[*].text
    out = ""
    try:
        for item in (getattr(resp, "output", None) or []):
            for c in (getattr(item, "content", None) or []):
                ctype = getattr(c, "type", None)
                if ctype in ("output_text", "text"):
                    out += getattr(c, "text", "") or ""
    except Exception:
        pass

    return out


async def verify_image(
    client: AsyncOpenAI,
    issue_context: str,
    image_bytes: bytes,
    mime_type: str,
) -> Dict[str, str | bool]:
    """
    MVP image relevance check.
    Returns: {"is_valid": bool, "reason": str}
    Compatible with older SDKs (no response_format kwarg).
    """
    data_url = _to_data_url(image_bytes, mime_type)

    resp = await client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You are a strict verifier for property maintenance images. "
                    "You MUST respond with a single JSON object ONLY (no markdown, no extra text) "
                    "with keys: is_valid (boolean), reason (string)."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Issue context:\n"
                            f"{issue_context}\n\n"
                            "Question: Is this image relevant to diagnosing the issue?"
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": data_url,
                    },
                ],
            },
        ],
    )

    text = _extract_text(resp).strip()

    # Some models may wrap JSON in text; attempt to find the first {...}
    if text and (not text.startswith("{") or not text.endswith("}")):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    try:
        obj = json.loads(text)
        return {
            "is_valid": bool(obj.get("is_valid")),
            "reason": str(obj.get("reason") or "")[:500],
        }
    except Exception:
        return {"is_valid": False, "reason": "Verifier did not return valid JSON."}
