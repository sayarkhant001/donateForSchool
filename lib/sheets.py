"""
lib/sheets.py — Google Sheets integration for the school donation bot.

Sheet Tabs:
  "Donations"        — one row per donation submission
  "Payment Accounts" — class → Wave/NUG account mapping (teacher-editable)
  "Settings"         — configurable bot messages (teacher-editable)
  "Users"            — tracks all user IDs for broadcast

Donations columns:
  A: Submitted At (bot UTC timestamp)
  B: Student ID
  C: Class (Grade)
  D: Payment Method (Wave / NUG)
  E: Entered Amount (Ks)  ← student typed
  F: SS Amount (Ks)       ← extracted from screenshot by Gemini
  G: Transaction Date & Time (from SS)
  H: From Account (sender, from SS)
  I: To Account (recipient, from SS)
  J: Transaction ID (from SS)
  K: Screenshot Link (Drive URL)
  L: Submitted By (Telegram @username or first name)
  M: Telegram User ID

Payment Accounts columns:
  A: Class (e.g. Grade 9)
  B: Method (Wave / NUG)
  C: Account Name
  D: Account Number / NUG ID
  E: Active (TRUE/FALSE)

Settings columns:
  A: Key
  B: Value

Users columns:
  A: User ID
  B: Username
  C: First Seen (UTC)
"""
import gspread
from google.oauth2 import service_account
from datetime import datetime, timezone, timedelta
from lib import config

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

_DONATIONS_SHEET   = "Donations"
_ACCOUNTS_SHEET    = "Payment Accounts"
_SETTINGS_SHEET    = "Settings"
_USERS_SHEET       = "Users"

_client: gspread.Client | None = None
_spreadsheet: gspread.Spreadsheet | None = None
_settings_cache: dict | None = None


def _get_spreadsheet() -> gspread.Spreadsheet:
    global _client, _spreadsheet
    if _spreadsheet is None:
        creds = service_account.Credentials.from_service_account_info(
            config.SERVICE_ACCOUNT_INFO, scopes=_SCOPES
        )
        _client = gspread.authorize(creds)
        _spreadsheet = _client.open_by_key(config.GOOGLE_SPREADSHEET_ID)
    return _spreadsheet


def get_sheet(name: str) -> gspread.Worksheet:
    return _get_spreadsheet().worksheet(name)


def _ensure_tab(name: str, headers: list[str]):
    """Create a sheet tab with headers if it doesn't exist."""
    ss = _get_spreadsheet()
    try:
        ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="USER_ENTERED")


# Ordered list of supported payment methods and their column names
_METHODS = ["KBZ", "Wave", "NUG"]
_ACCOUNTS_HEADERS = [
    "Class",
    "KBZ Name", "KBZ Number",
    "Wave Name", "Wave Number",
    "NUG Name",  "NUG Number",
    "Active",
]


def setup_sheets():
    """Ensure all required tabs and headers exist. Call once on deploy."""
    _ensure_tab(_DONATIONS_SHEET, [
        "Submitted At", "Student ID", "Class", "Payment Method",
        "Entered Amount (Ks)", "SS Amount (Ks)",
        "Transaction Date & Time", "From Account", "To Account",
        "Transaction ID", "Screenshot Link", "Submitted By", "Telegram User ID"
    ])
    _ensure_tab(_ACCOUNTS_SHEET, _ACCOUNTS_HEADERS)
    _ensure_tab(_SETTINGS_SHEET, ["Key", "Value"])
    _ensure_tab(_USERS_SHEET, ["User ID", "Username", "First Seen"])


# ─── Donations ────────────────────────────────────────────────────────────────

def append_donation(
    student_id: str,
    class_name: str,
    method: str,
    entered_amount: str,
    ss_amount: str,
    date_time: str,
    from_account: str,
    to_account: str,
    transaction_id: str,
    screenshot_link: str,
    submitted_by: str,
    user_id: int,
) -> bool:
    """Appends one donation row. Returns True on success."""
    try:
        ws = get_sheet(_DONATIONS_SHEET)
        mmt_tz = timezone(timedelta(hours=6, minutes=30))
        submitted_at = datetime.now(mmt_tz).strftime("%Y-%m-%d %I:%M:%S %p MMT")
        
        match_msg = "ပမာဏ ကိုက်ညီပါသည်။" if str(entered_amount).strip() == str(ss_amount).strip() else "ပမာဏ မကိုက်ညီသဖြင့် လူကိုယ်တိုင်စစ်ဆေးရန် လိုအပ်ပါသည်။"

        row = [
            submitted_at,
            student_id,
            class_name,
            method,
            entered_amount,
            ss_amount,
            match_msg,
            date_time,
            from_account,
            to_account,
            transaction_id,
            screenshot_link,
            submitted_by,
            str(user_id),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        print(f"[sheets] append_donation failed: {e}")
        return False


def is_duplicate_transaction(transaction_id: str, student_id: str) -> bool:
    """Returns True if this Transaction ID already exists for the SAME Student ID."""
    if not transaction_id:
        return False
    try:
        ws = get_sheet(_DONATIONS_SHEET)
        student_ids = ws.col_values(2)  # Column B — Student ID
        tx_ids = ws.col_values(11)      # Column K — Transaction ID (Shifted by 1 due to match_msg column)
        
        for s_id, t_id in zip(student_ids[1:], tx_ids[1:]):
            if t_id.strip() == transaction_id and s_id.strip() == student_id:
                return True
        return False
    except Exception as e:
        print(f"[sheets] is_duplicate_transaction failed: {e}")
        return False


# ─── Payment Accounts ─────────────────────────────────────────────────────────

def get_all_classes() -> list[str]:
    """Returns ordered list of classes from Payment Accounts sheet (one row per class)."""
    try:
        ws = get_sheet(_ACCOUNTS_SHEET)
        records = ws.get_all_records()
        return [
            str(r.get("Class", "")).strip()
            for r in records
            if str(r.get("Class", "")).strip()
        ]
    except Exception as e:
        print(f"[sheets] get_all_classes failed: {e}")
        return []


def _row_for_class(class_name: str) -> dict | None:
    """Return the single sheet row dict for a given class, or None."""
    try:
        ws = get_sheet(_ACCOUNTS_SHEET)
        records = ws.get_all_records()
        for r in records:
            if str(r.get("Class", "")).strip() == class_name.strip():
                return r
        return None
    except Exception as e:
        print(f"[sheets] _row_for_class failed: {e}")
        return None


def get_methods_for_class(class_name: str) -> list[str]:
    """
    Returns active methods for a class from the single-row layout.
    Checks KBZ Number, Wave Number, NUG Number columns.
    """
    row = _row_for_class(class_name)
    if not row:
        return []
    active = str(row.get("Active", "")).upper()
    if active not in ("TRUE", "YES", "1", "✓"):
        return []
    methods = []
    for m in _METHODS:
        num = str(row.get(f"{m} Number", "")).strip()
        if num:
            methods.append(m)
    return methods


def get_payment_account(class_name: str, method: str) -> dict | None:
    """
    Returns account info for a given class and method.
    Reads from single-row layout: {Method} Name / {Method} Number columns.
    """
    row = _row_for_class(class_name)
    if not row:
        return None
    active = str(row.get("Active", "")).upper()
    if active not in ("TRUE", "YES", "1", "✓"):
        return None
    m = method.strip()
    name   = str(row.get(f"{m} Name",   "")).strip()
    number = str(row.get(f"{m} Number", "")).strip()
    if not number:
        return None
    return {
        "class":          class_name,
        "method":         m,
        "account_name":   name,
        "account_number": number,
    }


def get_all_accounts() -> list[dict]:
    """Returns all payment account rows (for admin /accounts command)."""
    try:
        ws = get_sheet(_ACCOUNTS_SHEET)
        return ws.get_all_records()
    except Exception as e:
        print(f"[sheets] get_all_accounts failed: {e}")
        return []


# ─── Settings ─────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    """
    Reads the Settings tab and returns a dict of {key: value}.
    Results are cached per cold-start. Returns {} on failure.
    """
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache
    try:
        ws = get_sheet(_SETTINGS_SHEET)
        records = ws.get_all_records()
        _settings_cache = {
            str(r.get("Key", "")).strip(): str(r.get("Value", "")).strip()
            for r in records if r.get("Key")
        }
        return _settings_cache
    except Exception as e:
        print(f"[sheets] get_settings failed: {e}")
        return {}


def get_setting(key: str, default: str = "") -> str:
    return get_settings().get(key, default)


# ─── Stats ────────────────────────────────────────────────────────────────────

def get_daily_stats(date_str: str | None = None) -> dict:
    """
    Returns donation stats for a given date (YYYY-MM-DD).
    Defaults to today UTC.
    Returns: {date, total_count, total_entered_ks, by_class, by_method}
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        ws = get_sheet(_DONATIONS_SHEET)
        records = ws.get_all_records()
        result = {
            "date": date_str,
            "total_count": 0,
            "total_entered_ks": 0,
            "by_class": {},
            "by_method": {"Wave": 0, "NUG": 0},
        }
        for r in records:
            submitted = str(r.get("Submitted At", ""))
            if not submitted.startswith(date_str):
                continue
            result["total_count"] += 1
            try:
                amt = int(str(r.get("Entered Amount (Ks)", "0")).replace(",", ""))
            except Exception:
                amt = 0
            result["total_entered_ks"] += amt
            cls = str(r.get("Class", "Unknown"))
            result["by_class"][cls] = result["by_class"].get(cls, 0) + amt
            method = str(r.get("Payment Method", ""))
            if "NUG" in method.upper():
                result["by_method"]["NUG"] += amt
            else:
                result["by_method"]["Wave"] += amt
        return result
    except Exception as e:
        print(f"[sheets] get_daily_stats failed: {e}")
        return {"date": date_str, "total_count": 0, "total_entered_ks": 0,
                "by_class": {}, "by_method": {}}


def get_monthly_stats(year: int | None = None, month: int | None = None) -> dict:
    """
    Returns donation stats for a given month.
    Defaults to current UTC month.
    """
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    prefix = f"{year}-{month:02d}"
    try:
        ws = get_sheet(_DONATIONS_SHEET)
        records = ws.get_all_records()
        result = {
            "month": prefix,
            "total_count": 0,
            "total_entered_ks": 0,
            "by_class": {},
            "by_method": {"Wave": 0, "NUG": 0},
        }
        for r in records:
            submitted = str(r.get("Submitted At", ""))
            if not submitted.startswith(prefix):
                continue
            result["total_count"] += 1
            try:
                amt = int(str(r.get("Entered Amount (Ks)", "0")).replace(",", ""))
            except Exception:
                amt = 0
            result["total_entered_ks"] += amt
            cls = str(r.get("Class", "Unknown"))
            result["by_class"][cls] = result["by_class"].get(cls, 0) + amt
            method = str(r.get("Payment Method", ""))
            if "NUG" in method.upper():
                result["by_method"]["NUG"] += amt
            else:
                result["by_method"]["Wave"] += amt
        return result
    except Exception as e:
        print(f"[sheets] get_monthly_stats failed: {e}")
        return {"month": prefix, "total_count": 0, "total_entered_ks": 0,
                "by_class": {}, "by_method": {}}


# ─── Users (for broadcast) ────────────────────────────────────────────────────

def register_user(user_id: int, username: str):
    """Add user to Users tab if not already present."""
    try:
        ws = get_sheet(_USERS_SHEET)
        ids = ws.col_values(1)[1:]  # skip header
        if str(user_id) not in ids:
            first_seen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            ws.append_row([str(user_id), username, first_seen],
                          value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"[sheets] register_user failed: {e}")


def get_all_user_ids() -> list[int]:
    """Returns all registered user IDs for broadcast."""
    try:
        ws = get_sheet(_USERS_SHEET)
        ids = ws.col_values(1)[1:]  # skip header
        return [int(i) for i in ids if i.isdigit()]
    except Exception as e:
        print(f"[sheets] get_all_user_ids failed: {e}")
        return []
