"""
lib/vision.py — Extract payment data from WavePay AND NUGPay screenshots
using Gemini Vision API.

Supports:
  - WavePay / MyanmarPay screenshots
  - NUGPay screenshots (fields: from_account, to_account, transaction_id, amount, date_time)

Returns a unified dict with the same keys regardless of payment type.
"""
import json
import re
import google.generativeai as genai
from PIL import Image
import io
from lib import config

genai.configure(api_key=config.GEMINI_API_KEY)

_MODEL = "gemini-2.0-flash"

_PROMPT = """\
You are analyzing a mobile payment receipt screenshot from Myanmar.
This could be a WavePay, MyanmarPay, or NUGPay receipt.

Extract the following information and return ONLY valid JSON (no markdown, no explanation).

{
  "payment_type": "wavepay or nugpay or myanmarpay or unknown",
  "status": "Success or Failed or unknown",
  "amount": "numeric value only, no currency symbol, e.g. 268000",
  "from_account": "sender account (phone number for Wave, or username*nugpay.app for NUG)",
  "to_account": "recipient account (phone number for Wave, or username*nugpay.app for NUG)",
  "recipient_name": "full name of recipient if shown separately, else empty string",
  "transaction_id": "transaction ID or reference number as a string",
  "date_time": "date and time exactly as shown on screen, e.g. 12 Mar 2026, 09:58AM"
}

Rules:
- Return ONLY the JSON object, nothing else.
- If a field is not visible, use an empty string "".
- Do not add currency or commas to the amount field — digits only.
- For NUGPay: "To account" field is the recipient (e.g. sayarkhant*nugpay.app).
- For KBZPay: recipient phone number is shown under the account/name field.
- For WavePay: recipient phone is usually shown under recipient name.
- Keep date_time exactly as shown.
- Status: look for words like Success, Successful, Received, Approved, Completed, ငွေလွှဲပြောင်းပြီး, လက်ခံရရှိ.
- Set status to "Success" if payment went through. Set "Failed" only if clearly rejected.
"""


def extract_payment_info(image_bytes: bytes) -> dict:
    """
    Send screenshot to Gemini Vision and extract payment fields.

    Returns dict with keys:
        payment_type, status, amount, from_account, to_account,
        recipient_name, transaction_id, date_time

    On failure returns {"error": "..."} with all other keys as empty strings.
    """
    raw_text = ""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        model = genai.GenerativeModel(_MODEL)
        response = model.generate_content([_PROMPT, image])
        raw_text = response.text.strip()
        print(f"[vision] Gemini raw response: {raw_text[:300]!r}")

        # Strip markdown fences if Gemini wrapped in ```json ... ```
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        result = json.loads(raw_text)

        defaults = {
            "payment_type": "unknown",
            "status": "unknown",
            "amount": "",
            "from_account": "",
            "to_account": "",
            "recipient_name": "",
            "transaction_id": "",
            "date_time": "",
        }
        defaults.update(result)

        # Normalize amount: strip commas, spaces, currency
        raw_amt = str(defaults.get("amount", "")).replace(",", "").replace("Ks", "").strip()
        defaults["amount"] = raw_amt

        # Normalize status — accept many KBZ/Wave/NUG variations
        status_raw = str(defaults.get("status", "")).lower()
        if any(k in status_raw for k in (
            "success", "received", "complete", "approved",
            "done", "paid", "ငွေ", "လက်ခံ", "ပြီး"
        )):
            defaults["status"] = "Success"
        elif any(k in status_raw for k in ("fail", "reject", "cancel", "error", "decline")):
            defaults["status"] = "Failed"
        else:
            # Unknown status — treat as Success to avoid false rejections
            if defaults["status"] not in ("Success", "Failed"):
                defaults["status"] = "Success"

        return defaults

    except json.JSONDecodeError as e:
        print(f"[vision] JSON decode error: {e}\nRaw: {raw_text!r}")
        return _error_result(f"JSON parse error: {e}")
    except Exception as e:
        print(f"[vision] Gemini Vision error: {e}")
        return _error_result(str(e))


def _error_result(msg: str) -> dict:
    return {
        "payment_type": "unknown",
        "status": "unknown",
        "amount": "",
        "from_account": "",
        "to_account": "",
        "recipient_name": "",
        "transaction_id": "",
        "date_time": "",
        "error": msg,
    }
