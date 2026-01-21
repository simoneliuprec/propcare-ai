# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # recommended name

# Email (Resend)
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@simoneliu.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")  # required only for the email worker
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")  # where ops notifications go
REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL", "info@simoneliu.com")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing.")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing.")

# Don't hard-fail the whole API server if email isn't configured yet;
# Only fail when you actually run the email worker.
if not NOTIFICATION_EMAIL:
    # You can choose to hard-fail if you want. I recommend warning.
    # raise RuntimeError("NOTIFICATION_EMAIL is missing.")
    pass