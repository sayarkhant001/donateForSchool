"""
lib/vision.py — Extract payment data from WavePay, KBZPay, and NUGPay screenshots
using Google Gemini Vision API.
"""
import json
import re
import io
from PIL import Image
from google import genai
from google.genai import types
from lib import config

_client: genai.Client | None = None

_PROMPT = """\
You are analyzing a mobile payment receipt screenshot from Myanmar.
This could be a WavePay, KBZPay, or NUGPay receipt.

Extract the following information and return ONLY valid JSON (no markdown, no explanation).

{
  "payment_type": "wavepay or kbzpay or nugpay or unknown",
  "status": "Success or Failed or unknown",
  "amount": "numeric value only, no currency symbol, e.g. 19000",
  "from_account": "sender account (phone number for Wave/KBZ, or username*nugpay.app for NUG)",
  "to_account": "recipient account (phone number for Wave/KBZ, or username*nugpay.app for NUG)",
  "recipient_name": "full name of recipient if shown, else empty string",
  "transaction_id": "transaction ID or reference number as a string",
  "date_time": "date and time exactly as shown on screen"
}

Rules:
- Return ONLY the JSON object, nothing else.
- If a field is not visible, use an empty string "".
- Do not add currency or commas to the amount field — digits only.
- For KBZPay: recipient phone number is shown next to the account/transfer field.
- For NUGPay: "To account" field is the recipient (e.g. sayarkhant*nugpay.app).
- For WavePay: recipient phone is shown under recipient name.
- Status: look for Success, Successful, Received, Approved, Completed, ငွေလွှဲပြောင်းပြီး, လက်ခံရရှိ.
- Set status to "Success" if payment clearly went through.
- Set "Failed" only if clearly rejected/failed.
- Keep date_time exactly as shown on the screenshot.
"""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client




def _normalize_result(raw: dict) -> dict:
    """Apply standard normalizations to a parsed result dict."""
    defaults = {
        "payment_type":   "unknown",
        "status":         "unknown",
        "amount":         "",
        "from_account":   "",
        "to_account":     "",
        "recipient_name": "",
        "transaction_id": "",
        "date_time":      "",
    }
    defaults.update(raw)

    # Normalize amount: strip commas, spaces, currency symbols
    raw_amt = str(defaults["amount"]).replace(",", "").replace("Ks", "").strip()
    defaults["amount"] = raw_amt

    # Normalize status
    status_raw = str(defaults["status"]).lower()
    if any(k in status_raw for k in (
        "success", "received", "complete", "approved",
        "done", "paid", "ငွေ", "လက်ခံ", "ပြီး"
    )):
        defaults["status"] = "Success"
    elif any(k in status_raw for k in ("fail", "reject", "cancel", "error", "decline")):
        defaults["status"] = "Failed"
    else:
        defaults["status"] = "Success"  # unknown → treat as Success

    return defaults


# ─── Public API ───────────────────────────────────────────────────────────────

def extract_payment_info(image_bytes: bytes) -> dict:
    """
    Send screenshot to Gemini Vision and extract payment fields.
    Automatically rotates through models on 429 quota errors.

    Returns dict with keys:
        payment_type, status, amount, from_account, to_account,
        recipient_name, transaction_id, date_time

    On failure returns {"error": "..."} with all other keys as empty strings.
    """
    # Convert to JPEG once
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        jpeg_bytes = buf.getvalue()
    except Exception as e:
        return _error_result(f"Image conversion failed: {e}")

    client = _get_client()
    model = "gemini-2.0-flash"

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_text(text=_PROMPT),
                types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
            ],
        )

        raw_text = response.text.strip()
        print(f"[vision] Gemini raw (first 300): {raw_text[:300]!r}")

        # Strip markdown fences if Gemini wrapped in ```json ... ```
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        result = json.loads(raw_text)
        return _normalize_result(result)

    except json.JSONDecodeError as e:
        return _error_result(f"JSON parse error: {e}")
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            return _error_result("Quota Exhausted: You have used up your free Gemini API requests for today. Please wait or use a new API key.")
        return _error_result(msg)


def _error_result(msg: str) -> dict:
    return {
        "payment_type":   "unknown",
        "status":         "unknown",
        "amount":         "",
        "from_account":   "",
        "to_account":     "",
        "recipient_name": "",
        "transaction_id": "",
        "date_time":      "",
        "error":          msg,
    }
