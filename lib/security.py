"""
lib/security.py — Channel membership verification and admin checks.

Uses Telegram's getChatMember API to verify that a user is a member
of the configured ALLOWED_CHAT_ID before permitting bot usage.
"""
import telebot
from lib import config


def is_member_of_allowed_chat(bot: telebot.TeleBot, user_id: int) -> bool:
    """
    Returns True if the user is a member, admin, or creator of the
    configured ALLOWED_CHAT_ID channel/group. Returns False otherwise.
    """
    try:
        member = bot.get_chat_member(config.ALLOWED_CHAT_ID, user_id)
        return member.status in ("member", "administrator", "creator", "restricted")
    except telebot.apihelper.ApiTelegramException as e:
        # If the bot isn't an admin of the channel, this may fail
        print(f"[security] getChatMember failed for user {user_id}: {e}")
        # Fail-closed: deny access if we can't verify
        return False
    except Exception as e:
        print(f"[security] Unexpected error checking membership: {e}")
        return False


def is_admin(user_id: int) -> bool:
    """Returns True if user_id is in the ADMIN_IDS list."""
    return user_id in config.ADMIN_IDS
