"""Điểm trung gian để các module gửi tin sang Telegram/Discord mà không phụ thuộc nhau."""
import logging

import config
from util import split_message

log = logging.getLogger(__name__)

_tg_bot = None
_dc_client = None


def register_telegram(bot) -> None:
    global _tg_bot
    _tg_bot = bot


def register_discord(client) -> None:
    global _dc_client
    _dc_client = client


def status() -> dict:
    return {
        "telegram": _tg_bot is not None,
        "discord": bool(_dc_client is not None and _dc_client.is_ready()),
    }


async def send_telegram(chat_id: int, text: str) -> None:
    if _tg_bot is None:
        raise RuntimeError("Bot Telegram chưa chạy")
    for chunk in split_message(text, 4000):
        await _tg_bot.send_message(chat_id=chat_id, text=chunk)


async def send_discord(channel_id: int, text: str) -> None:
    if _dc_client is None:
        raise RuntimeError("Bot Discord chưa chạy")
    channel = _dc_client.get_channel(channel_id) or await _dc_client.fetch_channel(channel_id)
    for chunk in split_message(text, 1900):
        await channel.send(chunk)


async def reply_in(platform: str, channel_id: int, message_id: int, text: str) -> None:
    """Admin trả lời trực tiếp vào tin nhắn gốc của người dùng."""
    if platform == "telegram":
        if _tg_bot is None:
            raise RuntimeError("Bot Telegram chưa chạy")
        for i, chunk in enumerate(split_message(text, 4000)):
            await _tg_bot.send_message(
                chat_id=channel_id,
                text=chunk,
                reply_to_message_id=message_id if i == 0 else None,
                allow_sending_without_reply=True,
            )
    elif platform == "discord":
        if _dc_client is None:
            raise RuntimeError("Bot Discord chưa chạy")
        channel = _dc_client.get_channel(channel_id) or await _dc_client.fetch_channel(channel_id)
        for i, chunk in enumerate(split_message(text, 1900)):
            ref = channel.get_partial_message(message_id) if i == 0 and hasattr(channel, "get_partial_message") else None
            await channel.send(chunk, reference=ref)
    else:
        raise ValueError(f"Nền tảng không hợp lệ: {platform}")


async def broadcast(text: str, telegram: bool = True, discord: bool = True) -> dict[str, bool]:
    """Đăng lên kênh cộng đồng đã cấu hình. Trả về {nền tảng: thành công?} chỉ cho nền tảng có cấu hình."""
    results: dict[str, bool] = {}
    if telegram and config.TELEGRAM_COMMUNITY_CHAT_ID:
        try:
            await send_telegram(config.TELEGRAM_COMMUNITY_CHAT_ID, text)
            results["telegram"] = True
        except Exception:
            log.exception("Không đăng được lên Telegram")
            results["telegram"] = False
    if discord and config.DISCORD_STORY_CHANNEL_ID:
        try:
            await send_discord(config.DISCORD_STORY_CHANNEL_ID, text)
            results["discord"] = True
        except Exception:
            log.exception("Không đăng được lên Discord")
            results["discord"] = False
    return results


async def notify_admin(text: str) -> None:
    """Báo cho admin thật (không bao giờ ném lỗi)."""
    if config.TELEGRAM_ADMIN_CHAT_ID:
        try:
            await send_telegram(config.TELEGRAM_ADMIN_CHAT_ID, "🔔 " + text)
        except Exception:
            log.exception("Không báo được admin qua Telegram")
    if config.DISCORD_ADMIN_CHANNEL_ID:
        try:
            await send_discord(config.DISCORD_ADMIN_CHANNEL_ID, "🔔 " + text)
        except Exception:
            log.exception("Không báo được admin qua Discord")
