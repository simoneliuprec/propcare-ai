# backend/app/email_resend.py
from dataclasses import dataclass
import requests

@dataclass(frozen=True)
class OutboundEmail:
    to: str
    subject: str
    text: str
    reply_to: str | None = None

class ResendEmailClient:
    def __init__(self, api_key: str, from_email: str):
        if not api_key:
            raise RuntimeError("RESEND_API_KEY is missing.")
        if not from_email:
            raise RuntimeError("EMAIL_FROM is missing.")
        self.api_key = api_key
        self.from_email = from_email

    def send(self, msg: OutboundEmail) -> None:
        payload: dict = {
            "from": self.from_email,
            "to": [msg.to],
            "subject": msg.subject,
            "text": msg.text,
        }
        if msg.reply_to:
            payload["reply_to"] = msg.reply_to

        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
