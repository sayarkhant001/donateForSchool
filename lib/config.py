"""
lib/config.py — Load and validate all environment variables.
"""
import os
import base64
import json


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return val


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# ─── Telegram ─────────────────────────────────────────────────────────────────
BOT_TOKEN: str = _require("BOT_TOKEN")

_admin_raw = _optional("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]

# The channel/group users must be members of (e.g. "@mychannel" or -1001234567890)
ALLOWED_CHAT_ID: str = _require("ALLOWED_CHAT_ID")

WEBHOOK_SECRET: str = _optional("WEBHOOK_SECRET", "")

# ─── Google ───────────────────────────────────────────────────────────────────
GOOGLE_SPREADSHEET_ID: str = _require("GOOGLE_SPREADSHEET_ID")
GOOGLE_DRIVE_FOLDER_ID: str = _require("GOOGLE_DRIVE_FOLDER_ID")

_sa_b64 = _require("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
try:
    SERVICE_ACCOUNT_INFO: dict = json.loads(base64.b64decode(_sa_b64).decode("utf-8"))
except Exception as e:
    raise ValueError(f"Failed to decode GOOGLE_SERVICE_ACCOUNT_JSON_BASE64: {e}")

# ─── OCR ──────────────────────────────────────────────────────────────────────
OCR_SPACE_API_KEY: str = _optional("OCR_SPACE_API_KEY", "helloworld")

# ─── Settings ─────────────────────────────────────────────────────────────────
RATE_LIMIT_SECONDS: int = int(_optional("RATE_LIMIT_SECONDS", "60"))
