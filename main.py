import asyncio
import logging
import sys
from datetime import datetime, timedelta

import config
import db
import hub
import stories

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("main")


async def run_telegram() -> None:
    import telegram_bot

    app = telegram_bot.build_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    log.info("Telegram bot đang chạy")
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


async def run_discord() -> None:
    import discord_bot

    client = discord_bot.build_client()
    async with client:
        await client.start(config.DISCORD_BOT_TOKEN)


async def run_admin() -> None:
    import admin_web

    admin_web.start_in_thread(asyncio.get_running_loop())
    log.info("Trang admin: http://%s:%s", config.ADMIN_HOST, config.ADMIN_PORT)
    await asyncio.Event().wait()


async def maybe_run_daily_story() -> None:
    """Chạy mỗi phút: đến giờ đã cài (trong cửa sổ 6 tiếng) và hôm nay chưa chạy thì tạo/đăng truyện."""
    cfg = stories.get_settings()
    if not cfg["enabled"]:
        return
    now = datetime.now(config.TIMEZONE)
    today = now.date().isoformat()
    if db.get_setting("story_last_date") == today:
        return
    scheduled = now.replace(hour=cfg["hour"], minute=0, second=0, microsecond=0)
    if not (scheduled <= now < scheduled + timedelta(hours=6)):
        return
    db.set_setting("story_last_date", today)  # đặt trước để lỗi không gây thử lại liên tục
    try:
        story = await stories.generate_story(status="draft", source="auto")
        if cfg["mode"] == "auto":
            await stories.publish_story(story["id"])
            log.info("Đã tự đăng truyện #%s", story["id"])
        else:
            link = f"\nDuyệt tại: {config.ADMIN_PUBLIC_URL}/stories" if config.ADMIN_PUBLIC_URL else ""
            await hub.notify_admin(f"Có bản nháp truyện mới chờ duyệt: {story['title']}{link}")
            log.info("Đã tạo bản nháp #%s chờ duyệt", story["id"])
    except Exception as e:
        log.exception("Lỗi truyện hằng ngày")
        await hub.notify_admin(f"Truyện hằng ngày bị lỗi: {e}")


async def scheduler_loop() -> None:
    ticks = 0
    while True:
        try:
            if ticks % 1440 == 0:  # ~mỗi ngày: xoá nhật ký quá hạn
                n = db.purge_conversations(config.LOG_RETENTION_DAYS)
                if n:
                    log.info("Đã xoá %s hội thoại quá %s ngày", n, config.LOG_RETENTION_DAYS)
            await maybe_run_daily_story()
        except Exception:
            log.exception("Lỗi scheduler")
        ticks += 1
        await asyncio.sleep(60)


async def main() -> None:
    if not config.ANTHROPIC_API_KEY:
        sys.exit("Thiếu ANTHROPIC_API_KEY trong file .env")

    tasks = []
    if config.TELEGRAM_BOT_TOKEN:
        tasks.append(run_telegram())
    if config.DISCORD_BOT_TOKEN:
        tasks.append(run_discord())
    if not tasks:
        sys.exit("Cần ít nhất một trong TELEGRAM_BOT_TOKEN hoặc DISCORD_BOT_TOKEN")

    if config.ADMIN_PASSWORD:
        if len(config.ADMIN_PASSWORD) < 8:
            sys.exit("ADMIN_PASSWORD phải có ít nhất 8 ký tự")
        tasks.append(run_admin())
    else:
        log.warning("Chưa đặt ADMIN_PASSWORD → trang admin đang TẮT")

    tasks.append(scheduler_loop())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
