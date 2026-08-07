"""
lib/broadcast.py — Broadcast messages to all registered users.

User IDs are persisted in the Google Sheets "Users" tab via sheets.py.
"""
import telebot
from lib import sheets


def broadcast_message(bot: telebot.TeleBot, text: str) -> tuple[int, int]:
    """
    Send text to all users in the Users sheet.

    Returns:
        (sent_count, failed_count)
    """
    user_ids = sheets.get_all_user_ids()
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            print(f"[broadcast] Failed to send to {uid}: {e}")
            failed += 1
    return sent, failed
