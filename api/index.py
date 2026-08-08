"""
api/index.py — Vercel serverless entry point for the DonatingBot.

Routes:
  POST /api/webhook  — Telegram webhook
  GET  /api/setup    — One-time sheet tab setup
  GET  /api/debug    — Health check
  GET  /             — Health check
"""
import json
import re
import time
import telebot
from http.server import BaseHTTPRequestHandler

from lib import config, state, sheets, security, broadcast
from lib import messages as MSG
from lib.vision import extract_payment_info
from lib.drive import upload_screenshot

# ─── Bot instance ─────────────────────────────────────────────────────────────
bot = telebot.TeleBot(config.BOT_TOKEN, threaded=False)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _normalize_student_id(raw: str) -> str:
    """Strip everything except letters and digits, uppercase."""
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()


def _make_class_keyboard(classes: list[str]) -> telebot.types.InlineKeyboardMarkup:
    kb = telebot.types.InlineKeyboardMarkup(row_width=3)
    buttons = [
        telebot.types.InlineKeyboardButton(c, callback_data=f"class:{c}")
        for c in classes
    ]
    kb.add(*buttons)
    return kb


def _make_method_keyboard(methods: list[str]) -> telebot.types.InlineKeyboardMarkup:
    """Build method keyboard from whatever methods exist in the sheet for this class."""
    kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        telebot.types.InlineKeyboardButton(
            _method_label(m), callback_data=f"method:{m}"
        )
        for m in methods
    ]
    kb.add(*buttons)
    kb.add(telebot.types.InlineKeyboardButton(MSG.CANCEL_BUTTON, callback_data="cancel"))
    return kb


def _method_label(method: str) -> str:
    """Return a nice emoji label for any payment method."""
    m = method.upper()
    if "WAVE" in m:  return MSG.WAVE_LABEL
    if "NUG"  in m:  return MSG.NUG_LABEL
    if "KBZ"  in m:  return "🏦 KBZPay"
    if "CB"   in m:  return "🏦 CBPay"
    if "AYA"  in m:  return "🏦 AYAPay"
    return f"💳 {method}"


def _make_start_keyboard() -> telebot.types.InlineKeyboardMarkup:
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton(MSG.START_BUTTON, callback_data="begin"))
    return kb


def _send_welcome(bot: telebot.TeleBot, chat_id: int, user_id: int, username: str):
    """Show welcome message and register user."""
    sheets.register_user(user_id, username)
    welcome = sheets.get_setting("welcome_message", MSG.DEFAULT_WELCOME)
    bot.send_message(chat_id, welcome, reply_markup=_make_start_keyboard())
    state.set_step(user_id, "idle")


def _format_stats_message(s: dict, label: str) -> str:
    lines = [
        f"📊 <b>{label}</b>",
        f"─────────────────────",
        f"📋 လှူဒါန်း အရေအတွက် - {s['total_count']} ကြိမ်",
        f"💰 စုစုပေါင်း - {s['total_entered_ks']:,} Ks",
        f"",
        f"<b>💜 WavePay</b> - {s['by_method'].get('Wave', 0):,} Ks",
        f"<b>🟡 NUGPay</b>  - {s['by_method'].get('NUG', 0):,} Ks",
    ]
    if s.get("by_class"):
        lines.append("\n<b>📚 တန်းအလိုက်</b>")
        for cls, amt in sorted(s["by_class"].items()):
            lines.append(f"  • {cls} - {amt:,} Ks")
    return "\n".join(lines)


# ─── /start command ───────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: telebot.types.Message):
    user_id  = message.from_user.id
    chat_id  = message.chat.id
    username = message.from_user.username or message.from_user.first_name or str(user_id)

    if not security.is_member_of_allowed_chat(bot, user_id):
        # No link or button — only insiders who already know the channel can proceed
        bot.send_message(chat_id, MSG.NOT_MEMBER)
        return

    state.reset(user_id)
    _send_welcome(bot, chat_id, user_id, username)


# ─── /cancel command ──────────────────────────────────────────────────────────

@bot.message_handler(commands=["cancel"])
def cmd_cancel(message: telebot.types.Message):
    state.reset(message.from_user.id)
    bot.send_message(message.chat.id, MSG.CANCEL_MSG)


# ─── /admin command ───────────────────────────────────────────────────────────

@bot.message_handler(commands=["admin"])
def cmd_admin(message: telebot.types.Message):
    if not security.is_admin(message.from_user.id):
        bot.send_message(message.chat.id, MSG.NOT_ADMIN)
        return
    bot.send_message(message.chat.id, MSG.ADMIN_MENU, parse_mode="HTML")


# ─── /stats command ───────────────────────────────────────────────────────────

@bot.message_handler(commands=["stats"])
def cmd_stats(message: telebot.types.Message):
    if not security.is_admin(message.from_user.id):
        bot.send_message(message.chat.id, MSG.NOT_ADMIN)
        return

    daily   = sheets.get_daily_stats()
    monthly = sheets.get_monthly_stats()

    if daily["total_count"] == 0 and monthly["total_count"] == 0:
        bot.send_message(message.chat.id, MSG.NO_STATS)
        return

    text = (
        _format_stats_message(daily,   f"ယနေ့ ({daily['date']})") +
        "\n\n" +
        _format_stats_message(monthly, f"ဤလ ({monthly['month']})")
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")


# ─── /accounts command ────────────────────────────────────────────────────────

@bot.message_handler(commands=["accounts"])
def cmd_accounts(message: telebot.types.Message):
    if not security.is_admin(message.from_user.id):
        bot.send_message(message.chat.id, MSG.NOT_ADMIN)
        return

    accounts = sheets.get_all_accounts()
    if not accounts:
        bot.send_message(message.chat.id, "📭 ငွေလွှဲ အကောင့် မရှိသေးပါ။")
        return

    lines = ["💳 <b>ငွေလွှဲ အကောင့်များ</b>", "─────────────────────"]
    for a in accounts:
        active = "✅" if str(a.get("Active", "")).upper() in ("TRUE", "YES", "1") else "❌"
        lines.append(
            f"{active} <b>{a.get('Class','')} — {a.get('Method','')}</b>\n"
            f"   👤 {a.get('Account Name','')} | {a.get('Account Number','')}"
        )
    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="HTML")


# ─── /broadcast command ───────────────────────────────────────────────────────

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message: telebot.types.Message):
    if not security.is_admin(message.from_user.id):
        bot.send_message(message.chat.id, MSG.NOT_ADMIN)
        return
    state.set_step(message.from_user.id, "admin_broadcast")
    bot.send_message(message.chat.id, MSG.BROADCAST_PROMPT)


# ─── Inline keyboard callbacks ────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call: telebot.types.CallbackQuery):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data    = call.data

    bot.answer_callback_query(call.id)

    # ── begin (after welcome) ─────────────────────────────────────────────────
    if data == "begin":
        state.set_step(user_id, "waiting_student_id")
        bot.send_message(chat_id, MSG.ASK_STUDENT_ID)
        return

    # ── cancel ────────────────────────────────────────────────────────────────
    if data == "cancel":
        state.reset(user_id)
        bot.send_message(chat_id, MSG.CANCEL_MSG)
        return

    # ── class selection ───────────────────────────────────────────────────────
    if data.startswith("class:"):
        class_name = data.split(":", 1)[1]
        state.update_data(user_id, class_name=class_name)

        # Dynamically load methods for this class from sheet
        methods = sheets.get_methods_for_class(class_name)
        if not methods:
            bot.send_message(chat_id, f"⚠️ <b>{class_name}</b> အတွက် ငွေလွှဲ အကောင့် မရှိသေးပါ။\nAdmin ထံ ဆက်သွယ်ပါ။", parse_mode="HTML")
            state.reset(user_id)
            return

        state.set_step(user_id, "waiting_method")
        bot.send_message(
            chat_id,
            f"📚 တန်း - <b>{class_name}</b>\n\n{MSG.CHOOSE_METHOD}",
            parse_mode="HTML",
            reply_markup=_make_method_keyboard(methods),
        )
        return

    # ── method selection ──────────────────────────────────────────────────────
    if data.startswith("method:"):
        method = data.split(":", 1)[1]  # "Wave" or "NUG"
        state.update_data(user_id, method=method)

        data_dict  = state.get_data(user_id)
        class_name = data_dict.get("class_name", "")
        account    = sheets.get_payment_account(class_name, method)

        if account is None:
            bot.send_message(chat_id, MSG.NO_ACCOUNT.format(_method_label(method)))
            return

        state.update_data(user_id,
                          account_name=account["account_name"],
                          account_number=account["account_number"])

        # Universal account display — works for Wave, NUG, KBZ, or any method
        m_upper = method.upper()
        if "NUG" in m_upper:
            account_text = MSG.SHOW_ACCOUNT_NUG.format(
                account_name=account["account_name"],
                account_number=account["account_number"],
            )
        else:
            # Wave, KBZ, CB, AYA — all use phone-number style display
            account_text = MSG.SHOW_ACCOUNT_WAVE.format(
                account_name=account["account_name"],
                account_number=account["account_number"],
            )

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton(MSG.CANCEL_BUTTON, callback_data="cancel"))

        bot.send_message(chat_id, account_text, reply_markup=kb)
        state.set_step(user_id, "waiting_amount")
        bot.send_message(chat_id, MSG.ASK_AMOUNT)
        return



# ─── Text message handler ─────────────────────────────────────────────────────

@bot.message_handler(content_types=["text"])
def handle_text(message: telebot.types.Message):
    user_id  = message.from_user.id
    chat_id  = message.chat.id
    text     = message.text.strip()
    step     = state.get_step(user_id)

    # ── Admin broadcast input ─────────────────────────────────────────────────
    if step == "admin_broadcast" and security.is_admin(user_id):
        if text.lower() == "/cancel":
            state.reset(user_id)
            bot.send_message(chat_id, MSG.CANCEL_MSG)
            return
        sent, failed = broadcast.broadcast_message(bot, text)
        state.reset(user_id)
        bot.send_message(
            chat_id,
            MSG.BROADCAST_SENT.format(count=sent) +
            (f"\n⚠️ {failed} ဦးထံ ပေးပို့မရပါ" if failed else "")
        )
        return

    # ── Student ID input ──────────────────────────────────────────────────────
    if step == "waiting_student_id":
        normalized = _normalize_student_id(text)
        if len(normalized) < 3:
            bot.send_message(chat_id, MSG.INVALID_STUDENT_ID)
            return
        state.update_data(user_id, student_id=normalized)
        state.set_step(user_id, "waiting_class")

        classes = sheets.get_all_classes()
        if not classes:
            # Fallback: Grade 1–12
            classes = [f"Grade {i}" for i in range(1, 13)]

        kb = _make_class_keyboard(classes)
        bot.send_message(chat_id,
                         f"🎓 Student ID - <b>{normalized}</b>\n\n{MSG.CHOOSE_CLASS}",
                         parse_mode="HTML",
                         reply_markup=kb)
        return

    # ── Amount input ──────────────────────────────────────────────────────────
    if step == "waiting_amount":
        amount_raw = re.sub(r"[^0-9]", "", text)
        if not amount_raw or int(amount_raw) <= 0:
            bot.send_message(chat_id, MSG.INVALID_AMOUNT)
            return
        state.update_data(user_id, entered_amount=amount_raw)
        state.set_step(user_id, "waiting_screenshot")
        bot.send_message(chat_id, MSG.ASK_SCREENSHOT)
        return

    # ── Unexpected text ───────────────────────────────────────────────────────
    if step == "idle":
        # Re-prompt welcome
        if not security.is_member_of_allowed_chat(bot, user_id):
            bot.send_message(chat_id, MSG.NOT_MEMBER)
            return
        bot.send_message(chat_id, "ဆက်လုပ်ရန် /start နှိပ်ပါ")
    else:
        bot.send_message(chat_id, "⚠️ ကျေးဇူးပြု၍ မှန်ကန်သော အချက်အလက် ပေးပို့ပါ သို့မဟုတ် /cancel နှိပ်ပါ")


# ─── Photo handler (screenshot) ───────────────────────────────────────────────

@bot.message_handler(content_types=["photo"])
def handle_photo(message: telebot.types.Message):
    user_id  = message.from_user.id
    chat_id  = message.chat.id
    step     = state.get_step(user_id)

    if step != "waiting_screenshot":
        bot.send_message(chat_id, "⚠️ ယခု Screenshot မလိုအပ်သေးပါ။ /start နှိပ်ပြီး ပြန်စပါ")
        return

    # Rate limit check
    wait = state.check_rate_limit(user_id, config.RATE_LIMIT_SECONDS)
    if wait:
        bot.send_message(chat_id, MSG.RATE_LIMITED.format(seconds=wait))
        return

    state.set_step(user_id, "processing")
    processing_msg = bot.send_message(chat_id, MSG.PROCESSING)

    try:
        data_dict = state.get_data(user_id)
        student_id    = data_dict.get("student_id", "")
        class_name    = data_dict.get("class_name", "")
        method        = data_dict.get("method", "")
        entered_amount = data_dict.get("entered_amount", "")
        account_name  = data_dict.get("account_name", "")
        account_number = data_dict.get("account_number", "")

        # ── Download photo ────────────────────────────────────────────────────
        photo   = max(message.photo, key=lambda p: p.file_size)
        file_info = bot.get_file(photo.file_id)
        image_bytes = bot.download_file(file_info.file_path)

        # ── Gemini extraction ──────────────────────────────────────────────────
        extracted = extract_payment_info(image_bytes)

        if "error" in extracted:
            bot.delete_message(chat_id, processing_msg.message_id)
            bot.send_message(chat_id, MSG.EXTRACTION_FAILED)
            state.set_step(user_id, "waiting_screenshot")
            return

        # ── Status check ───────────────────────────────────────────────────────
        if extracted.get("status") != "Success":
            bot.delete_message(chat_id, processing_msg.message_id)
            bot.send_message(chat_id, MSG.NOT_SUCCESS.format(
                status=extracted.get("status", "unknown")
            ))
            state.set_step(user_id, "waiting_screenshot")
            return

        # ── Duplicate TX check ─────────────────────────────────────────────────
        tx_id = extracted.get("transaction_id", "")
        if tx_id and sheets.is_duplicate_transaction(tx_id):
            bot.delete_message(chat_id, processing_msg.message_id)
            bot.send_message(chat_id, MSG.DUPLICATE_TX)
            state.reset(user_id)
            return

        # ── Account verification ───────────────────────────────────────────────
        to_account = extracted.get("to_account", "")
        if account_number and to_account:
            # Soft check: normalize both (strip *, spaces, lowercase)
            norm_expected = re.sub(r"[^a-z0-9]", "", account_number.lower())
            norm_found    = re.sub(r"[^a-z0-9]", "", to_account.lower())
            if norm_expected and norm_found and norm_expected not in norm_found and norm_found not in norm_expected:
                bot.delete_message(chat_id, processing_msg.message_id)
                bot.send_message(chat_id, MSG.WRONG_ACCOUNT.format(
                    expected=account_number,
                    found=to_account,
                ))
                state.set_step(user_id, "waiting_screenshot")
                return

        # ── Upload to Drive ────────────────────────────────────────────────────
        method_prefix = "nug" if method == "NUG" else "wave"
        filename = f"{method_prefix}_{student_id}_{int(time.time())}.jpg"
        screenshot_link = upload_screenshot(image_bytes, filename)

        # ── Save to Sheets ─────────────────────────────────────────────────────
        username = message.from_user.username or message.from_user.first_name or str(user_id)
        ss_amount = extracted.get("amount", "")

        saved = sheets.append_donation(
            student_id     = student_id,
            class_name     = class_name,
            method         = method,
            entered_amount = entered_amount,
            ss_amount      = ss_amount,
            date_time      = extracted.get("date_time", ""),
            from_account   = extracted.get("from_account", ""),
            to_account     = extracted.get("to_account", ""),
            transaction_id = tx_id,
            screenshot_link= screenshot_link,
            submitted_by   = username,
            user_id        = user_id,
        )

        if not saved:
            bot.delete_message(chat_id, processing_msg.message_id)
            bot.send_message(chat_id, "❌ မှတ်တမ်း တင်မရပါ။ ထပ်မံကြိုးစားပါ။")
            state.set_step(user_id, "waiting_screenshot")
            return

        state.record_submission(user_id)
        state.reset(user_id)

        # ── Build thank-you message ────────────────────────────────────────────
        thank_you_tpl = sheets.get_setting("thank_you_message", MSG.DEFAULT_THANK_YOU)
        thank_you = thank_you_tpl.format(
            student_id    = student_id,
            class_name    = class_name,
            method        = f"{MSG.WAVE_LABEL if method == 'Wave' else MSG.NUG_LABEL}",
            amount        = f"{int(entered_amount):,}",
            account_name  = account_name,
            transaction_id= tx_id or "-",
            date_time     = extracted.get("date_time", "-"),
        )

        bot.delete_message(chat_id, processing_msg.message_id)
        bot.send_message(chat_id, thank_you)

        # Note about dual-student SS if amounts differ
        if ss_amount and entered_amount and ss_amount != entered_amount:
            bot.send_message(chat_id, MSG.AMOUNT_NOTE)

    except Exception as e:
        print(f"[webhook] handle_photo error: {e}")
        bot.delete_message(chat_id, processing_msg.message_id)
        bot.send_message(chat_id, "❌ အမှားတစ်ခု ဖြစ်ပွားသည်။ ထပ်မံကြိုးစားပါ။")
        state.set_step(user_id, "waiting_screenshot")


# ─── Vercel HTTP Handler ───────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # suppress noisy access logs

    def _send(self, status: int, body: str):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def _original_path(self) -> str:
        """Get the original request path before Vercel rewrites it."""
        # Vercel sets X-Forwarded-Uri or X-Now-Route-Matches with original path
        uri = self.headers.get("X-Forwarded-Uri", "") or self.headers.get("X-Now-Route-Matches", "")
        if uri:
            return uri.split("?")[0]
        return self.path.split("?")[0]

    def do_GET(self):
        path = self._original_path()

        if "setup" in path:
            try:
                sheets.setup_sheets()
                self._send(200, json.dumps({"ok": True, "msg": "Sheets setup complete"}))
            except Exception as e:
                self._send(500, json.dumps({"ok": False, "error": str(e)}))
            return

        if "seed" in path:
            try:
                from api.seed import seed_sheets
                results = seed_sheets()
                self._send(200, json.dumps({"ok": True, "results": results}))
            except Exception as e:
                self._send(500, json.dumps({"ok": False, "error": str(e)}))
            return

        self._send(200, json.dumps({
            "ok": True,
            "msg": "DonatingBot is running",
            "path": path,
        }))


    def do_POST(self):
        # All POSTs to /api/index come from Telegram webhook
        # Validate webhook secret
        if config.WEBHOOK_SECRET:
            secret_header = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if secret_header != config.WEBHOOK_SECRET:
                self._send(403, json.dumps({"ok": False, "error": "Forbidden"}))
                return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            update = telebot.types.Update.de_json(json.loads(body))
            bot.process_new_updates([update])
            self._send(200, json.dumps({"ok": True}))
        except Exception as e:
            print(f"[webhook] process error: {e}")
            self._send(200, json.dumps({"ok": True}))  # always 200 to Telegram

