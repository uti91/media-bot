import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int(name: str):
    v = _get(name)
    return int(v) if v else None


def _int_list(name: str) -> list[int]:
    return [int(x) for x in _get(name).split(",") if x.strip()]


def _bool(name: str, default: str = "false") -> bool:
    return _get(name, default).lower() in ("1", "true", "yes")


DATA_DIR = Path(_get("DATA_DIR")) if _get("DATA_DIR") else Path(__file__).parent / "data"

ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _get("CLAUDE_MODEL", "claude-sonnet-5-5")

TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
TELEGRAM_COMMUNITY_CHAT_ID = _int("TELEGRAM_COMMUNITY_CHAT_ID")
TELEGRAM_ADMIN_CHAT_ID = _int("TELEGRAM_ADMIN_CHAT_ID")

DISCORD_BOT_TOKEN = _get("DISCORD_BOT_TOKEN")
DISCORD_STORY_CHANNEL_ID = _int("DISCORD_STORY_CHANNEL_ID")
DISCORD_WELCOME_CHANNEL_ID = _int("DISCORD_WELCOME_CHANNEL_ID")
DISCORD_SUPPORT_CHANNEL_IDS = _int_list("DISCORD_SUPPORT_CHANNEL_IDS")
DISCORD_ADMIN_CHANNEL_ID = _int("DISCORD_ADMIN_CHANNEL_ID")

# Giá trị khởi tạo; sau đó chỉnh trong trang admin (lưu trong database)
STORY_ENABLED = _bool("STORY_ENABLED", "true")
STORY_HOUR = int(_get("STORY_HOUR", "19"))
STORY_MODE = _get("STORY_MODE", "auto")  # auto = tự đăng | approve = chờ admin duyệt
TIMEZONE = ZoneInfo(_get("TIMEZONE", "Asia/Ho_Chi_Minh"))
RATE_LIMIT_PER_MIN = int(_get("RATE_LIMIT_PER_MIN", "6"))
LOG_RETENTION_DAYS = int(_get("LOG_RETENTION_DAYS", "30"))

# Trang quản trị (bỏ trống ADMIN_PASSWORD = tắt trang admin)
ADMIN_PASSWORD = _get("ADMIN_PASSWORD")
ADMIN_SECRET = _get("ADMIN_SECRET")  # khoá ký cookie; bỏ trống thì suy ra từ mật khẩu
ADMIN_HOST = _get("ADMIN_HOST", "127.0.0.1")
ADMIN_PORT = int(_get("ADMIN_PORT", "8080"))
ADMIN_PUBLIC_URL = _get("ADMIN_PUBLIC_URL").rstrip("/")
ADMIN_COOKIE_SECURE = _bool("ADMIN_COOKIE_SECURE")   # bật true khi chạy sau HTTPS
ADMIN_BEHIND_PROXY = _bool("ADMIN_BEHIND_PROXY")     # bật true khi đứng sau nginx/caddy
