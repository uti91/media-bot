import logging
import re

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import brain
import config
import hub
import static_texts as T
import stories
from util import RateLimiter, leaked_secret, split_message

log = logging.getLogger(__name__)

limiter = RateLimiter(config.RATE_LIMIT_PER_MIN)
story_limiter = RateLimiter(1, window=3600)


async def _reply(update: Update, text: str) -> None:
    for chunk in split_message(text, 4000):
        await update.effective_message.reply_text(chunk)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, T.HELP)


async def cmd_network(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, T.NETWORK_INFO)


async def cmd_links(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, T.LINKS)


async def cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    await _reply(update, f"Chat ID: {chat.id}\nUser ID: {update.effective_user.id}")


async def cmd_story(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not story_limiter.allow(f"tg:{chat_id}"):
        await _reply(update, T.STORY_COOLDOWN)
        return
    await ctx.bot.send_chat_action(chat_id, "typing")
    try:
        story = await stories.generate_story(status="adhoc", source="command")
    except Exception:
        log.exception("Lỗi tạo truyện")
        await _reply(update, T.ERROR)
        return
    await _reply(update, story["body"] + stories.DISCLAIMER)


async def on_new_members(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    for member in update.effective_message.new_chat_members or []:
        if member.is_bot:
            continue
        await _reply(update, T.member_welcome(member.first_name))


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not msg.text or not user:
        return
    text = msg.text

    # Trong nhóm: chỉ trả lời khi được @mention hoặc khi người dùng reply tin nhắn của bot
    if chat.type != "private":
        bot_username = ctx.bot.username
        mentioned = f"@{bot_username}".lower() in text.lower()
        replied = bool(
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.id == ctx.bot.id
        )
        if not (mentioned or replied):
            return
        text = re.sub(f"@{re.escape(bot_username)}", "", text, flags=re.I).strip()
    if not text:
        return

    # Chặn rò rỉ seed phrase / private key trước khi gọi AI
    if leaked_secret(text):
        try:
            await msg.delete()
        except Exception:
            pass  # bot cần quyền admin để xoá trong nhóm
        await ctx.bot.send_message(chat.id, T.SECRET_WARNING)
        return

    if not limiter.allow(f"tg:{user.id}"):
        await _reply(update, T.RATE_LIMITED)
        return

    await ctx.bot.send_chat_action(chat.id, "typing")
    meta = {
        "platform": "telegram",
        "channel_id": chat.id,
        "message_id": msg.message_id,
        "user_name": f"{user.full_name} (@{user.username})" if user.username else user.full_name,
        "where": chat.title or "tin nhắn riêng",
    }
    reply, _ = await brain.answer(f"tg:{chat.id}:{user.id}", text, meta)
    await _reply(update, reply)


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Lỗi Telegram handler", exc_info=ctx.error)


def build_app() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_help))
    app.add_handler(CommandHandler("network", cmd_network))
    app.add_handler(CommandHandler("links", cmd_links))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("story", cmd_story))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_members))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    hub.register_telegram(app.bot)
    return app
