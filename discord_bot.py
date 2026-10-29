import logging

import discord

import brain
import config
import hub
import static_texts as T
import stories
from util import RateLimiter, leaked_secret, split_message

log = logging.getLogger(__name__)

limiter = RateLimiter(config.RATE_LIMIT_PER_MIN)
story_limiter = RateLimiter(1, window=3600)

STATIC_COMMANDS = {
    "!help": T.HELP,
    "!network": T.NETWORK_INFO,
    "!links": T.LINKS,
}


class KpowClient(discord.Client):
    async def on_ready(self) -> None:
        log.info("Discord bot đã đăng nhập: %s", self.user)

    async def on_member_join(self, member: discord.Member) -> None:
        if config.DISCORD_WELCOME_CHANNEL_ID:
            await hub.send_discord(config.DISCORD_WELCOME_CHANNEL_ID, T.member_welcome(member.mention))

    async def _reply(self, message: discord.Message, text: str) -> None:
        for chunk in split_message(text, 1900):
            await message.reply(chunk, mention_author=False)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        content = message.content.strip()
        # Bỏ mention của bot khỏi nội dung
        if self.user:
            content = content.replace(f"<@{self.user.id}>", "").replace(f"<@!{self.user.id}>", "").strip()
        if not content:
            return

        # Lệnh nhanh (không gọi AI), dùng được ở mọi kênh
        cmd = content.lower().split()[0]
        if cmd in STATIC_COMMANDS:
            await self._reply(message, STATIC_COMMANDS[cmd])
            return
        if cmd == "!id":
            await self._reply(message, f"Channel ID: {message.channel.id}\nUser ID: {message.author.id}")
            return
        if cmd == "!story":
            if not story_limiter.allow(f"dc:{message.channel.id}"):
                await self._reply(message, T.STORY_COOLDOWN)
                return
            async with message.channel.typing():
                try:
                    story = await stories.generate_story(status="adhoc", source="command")
                except Exception:
                    log.exception("Lỗi tạo truyện")
                    await self._reply(message, T.ERROR)
                    return
            await self._reply(message, story["body"] + stories.DISCLAIMER)
            return

        # Khi nào bot trả lời: DM, được @mention, hoặc ở kênh hỗ trợ đã cấu hình
        is_dm = message.guild is None
        mentioned = self.user in message.mentions if self.user else False
        in_support = message.channel.id in config.DISCORD_SUPPORT_CHANNEL_IDS
        if not (is_dm or mentioned or in_support):
            return

        if leaked_secret(content):
            try:
                await message.delete()
            except Exception:
                pass  # cần quyền Manage Messages
            await message.channel.send(T.SECRET_WARNING)
            return

        if not limiter.allow(f"dc:{message.author.id}"):
            await self._reply(message, T.RATE_LIMITED)
            return

        meta = {
            "platform": "discord",
            "channel_id": message.channel.id,
            "message_id": message.id,
            "user_name": str(message.author),
            "where": f"#{message.channel}" if message.guild else "tin nhắn riêng",
        }
        async with message.channel.typing():
            reply, _ = await brain.answer(f"dc:{message.channel.id}:{message.author.id}", content, meta)
        await self._reply(message, reply)


def build_client() -> KpowClient:
    intents = discord.Intents.default()
    intents.message_content = True  # cần bật "Message Content Intent" trong Developer Portal
    intents.members = True          # cần bật "Server Members Intent" để chào thành viên mới
    client = KpowClient(
        intents=intents,
        # Không cho bot @everyone / @role dù AI có viết ra
        allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
    )
    hub.register_discord(client)
    return client
