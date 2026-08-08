"""
api/seed.py — Populate Google Sheets with sample data.
Access: GET https://your-vercel-url/api/seed

WARNING: Only run once. Checks if data exists before inserting.
"""
import json
from http.server import BaseHTTPRequestHandler
from lib import sheets


PAYMENT_ACCOUNTS = [
    # Grade 6
    ["Grade 6",  "Wave", "Daw Khin Mya",  "09420012345",       "TRUE"],
    ["Grade 6",  "NUG",  "Daw Khin Mya",  "khinmya*nugpay.app","TRUE"],
    ["Grade 6",  "KBZ",  "Daw Khin Mya",  "09420012345",       "TRUE"],
    # Grade 7
    ["Grade 7",  "Wave", "U Kyaw Zin",    "09250034567",       "TRUE"],
    ["Grade 7",  "NUG",  "U Kyaw Zin",    "kyawzin*nugpay.app","TRUE"],
    ["Grade 7",  "KBZ",  "U Kyaw Zin",    "09250034567",       "TRUE"],
    # Grade 8
    ["Grade 8",  "Wave", "Daw Su Su",     "09790056789",       "TRUE"],
    ["Grade 8",  "NUG",  "Daw Su Su",     "susu*nugpay.app",   "TRUE"],
    ["Grade 8",  "KBZ",  "Daw Su Su",     "09790056789",       "TRUE"],
    # Grade 9
    ["Grade 9",  "Wave", "U Aung Naing",  "09450078901",       "TRUE"],
    ["Grade 9",  "NUG",  "U Aung Naing",  "aungnaing*nugpay.app","TRUE"],
    ["Grade 9",  "KBZ",  "U Aung Naing",  "09450078901",       "TRUE"],
    # Grade 10
    ["Grade 10", "Wave", "Daw Thida",     "09260090123",       "TRUE"],
    ["Grade 10", "NUG",  "Daw Thida",     "thida*nugpay.app",  "TRUE"],
    ["Grade 10", "KBZ",  "Daw Thida",     "09260090123",       "TRUE"],
    # Grade 11
    ["Grade 11", "Wave", "U Min Ko",      "09770011223",       "TRUE"],
    ["Grade 11", "NUG",  "U Min Ko",      "minko*nugpay.app",  "TRUE"],
    ["Grade 11", "KBZ",  "U Min Ko",      "09770011223",       "TRUE"],
]

SETTINGS = [
    ["welcome_message",
     "မင်္ဂလာပါ 🎓\n\nကျောင်းဆောင်ဒဏ် ပေးသွင်းရန် ကြိုဆိုပါသည်။\nဆက်လက်ရန် အောက်ပါ ခလုတ်ကို နှိပ်ပါ 👇"],
    ["thank_you_message",
     "✅ ကျေးဇူးတင်ပါသည်!\n\n🎓 Student ID  : {student_id}\n📚 တန်း        : {class_name}\n💳 ငွေလွှဲနည်း  : {method}\n💰 ပမာဏ        : {amount} Ks\n👤 အကောင့်    : {account_name}\n🔢 TX ID       : {transaction_id}\n🕐 ရက်/အချိန်   : {date_time}\n\nသင်၏ လှူဒါန်းမှုအတွက် ကျေးဇူးအများကြီးတင်ပါသည် 🙏"],
]


def seed_sheets() -> dict:
    results = {}

    # ── Payment Accounts ──────────────────────────────────────────
    ws_acc = sheets.get_sheet("Payment Accounts")
    existing = ws_acc.get_all_values()
    if len(existing) <= 1:
        ws_acc.append_rows(PAYMENT_ACCOUNTS, value_input_option="USER_ENTERED")
        results["payment_accounts"] = f"Added {len(PAYMENT_ACCOUNTS)} rows"
    else:
        results["payment_accounts"] = f"Already has {len(existing)-1} rows — skipped"

    # ── Settings ──────────────────────────────────────────────────
    ws_set = sheets.get_sheet("Settings")
    existing2 = ws_set.get_all_values()
    if len(existing2) <= 1:
        ws_set.append_rows(SETTINGS, value_input_option="USER_ENTERED")
        results["settings"] = f"Added {len(SETTINGS)} rows"
    else:
        results["settings"] = f"Already has {len(existing2)-1} rows — skipped"

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
        try:
            results = seed_sheets()
            self._send(200, json.dumps({"ok": True, "results": results}))
        except Exception as e:
            self._send(500, json.dumps({"ok": False, "error": str(e)}))
