"""
api/seed.py — Populate Google Sheets with real payment account data.
Access: GET https://your-vercel-url/api/seed        (skip if data exists)
        GET https://your-vercel-url/api/seed?force=1 (clear and re-add)
"""
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from lib import sheets

CLASSES = [
    "Grade 6", "Grade 7", "Grade 8",
    "Grade 9", "Grade 10", "Grade 11",
]

# ── Real payment accounts (same 3 for every class) ─────────────────────────
BASE_ACCOUNTS = [
    # Method  | Account Name       | Account Number          | Active
    ("KBZ",   "Daw Aye Aye Myint", "09981059064",            "TRUE"),
    ("Wave",  "Ko Khant",          "09941197735",            "TRUE"),
    ("NUG",   "Sayar Khant",       "sayarkhant*nugpay.app",  "TRUE"),
]

SETTINGS = [
    ["welcome_message",
     "မင်္ဂလာပါ 🎓\n\nကျောင်းဆောင်ဒဏ် ပေးသွင်းရန် ကြိုဆိုပါသည်။\nဆက်လက်ရန် အောက်ပါ ခလုတ်ကို နှိပ်ပါ 👇"],
    ["thank_you_message",
     "✅ ကျေးဇူးတင်ပါသည်!\n\n🎓 Student ID  : {student_id}\n📚 တန်း        : {class_name}\n💳 ငွေလွှဲနည်း  : {method}\n💰 ပမာဏ        : {amount} Ks\n👤 အကောင့်    : {account_name}\n🔢 TX ID       : {transaction_id}\n🕐 ရက်/အချိန်   : {date_time}\n\nသင်၏ လှူဒါန်းမှုအတွက် ကျေးဇူးအများကြီးတင်ပါသည် 🙏"],
]


def build_rows() -> list[list[str]]:
    rows = []
    for cls in CLASSES:
        for method, name, number, active in BASE_ACCOUNTS:
            rows.append([cls, method, name, number, active])
    return rows


def seed_sheets(force: bool = False) -> dict:
    results = {}

    ACCOUNTS_HEADER = ["Class", "Method", "Account Name", "Account Number", "Active"]
    SETTINGS_HEADER = ["Key", "Value"]

    # ── Payment Accounts ──────────────────────────────────────────
    ws_acc = sheets.get_sheet("Payment Accounts")
    existing = ws_acc.get_all_values()
    rows = build_rows()

    if force or len(existing) <= 1:
        ws_acc.clear()                                          # wipe everything
        ws_acc.append_row(ACCOUNTS_HEADER)                     # re-add header
        ws_acc.append_rows(rows, value_input_option="USER_ENTERED")
        results["payment_accounts"] = f"Added {len(rows)} rows ({len(CLASSES)} classes × 3 methods)"
    else:
        results["payment_accounts"] = f"Already has {len(existing)-1} rows — use ?force=1 to reset"

    # ── Settings ──────────────────────────────────────────────────
    ws_set = sheets.get_sheet("Settings")
    existing2 = ws_set.get_all_values()

    if force or len(existing2) <= 1:
        ws_set.clear()                                          # wipe everything
        ws_set.append_row(SETTINGS_HEADER)                     # re-add header
        ws_set.append_rows(SETTINGS, value_input_option="USER_ENTERED")
        results["settings"] = f"Added {len(SETTINGS)} rows"
    else:
        results["settings"] = f"Already has {len(existing2)-1} rows — use ?force=1 to reset"

    return results



class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _send(self, status: int, body: str):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        force = "1" in qs.get("force", [])
        try:
            results = seed_sheets(force=force)
            self._send(200, json.dumps({"ok": True, "results": results}))
        except Exception as e:
            self._send(500, json.dumps({"ok": False, "error": str(e)}))
