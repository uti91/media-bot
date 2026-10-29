import logging
import shutil
from pathlib import Path

import anthropic

import config
import db
import hub
from prompts import ADMIN_TAG, SUPPORT_PROMPT
from static_texts import ERROR

log = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

# Bản kiến thức "đang dùng" nằm trong data/ (sửa được từ trang admin, giữ được khi cập nhật code).
# Lần chạy đầu sẽ được khởi tạo từ knowledge/kpow.md.
DEFAULT_KNOWLEDGE_FILE = Path(__file__).parent / "knowledge" / "kpow.md"
KNOWLEDGE_FILE = config.DATA_DIR / "kpow.md"
config.DATA_DIR.mkdir(parents=True, exist_ok=True)
if not KNOWLEDGE_FILE.exists():
    shutil.copyfile(DEFAULT_KNOWLEDGE_FILE, KNOWLEDGE_FILE)

SYSTEM: list[dict] = []


def rebuild_system() -> None:
    """Đọc lại kiến thức + hướng dẫn bổ sung của admin (gọi sau mỗi lần admin lưu)."""
    global SYSTEM
    knowledge = KNOWLEDGE_FILE.read_text(encoding="utf-8")
    extra = (db.get_setting("extra_instructions", "") or "").strip()
    extra_block = ""
    if extra:
        extra_block = (
            "\n\n# Hướng dẫn bổ sung từ admin\n"
            "(Không được mâu thuẫn với các nguyên tắc bắt buộc ở trên; nếu mâu thuẫn, ưu tiên nguyên tắc bắt buộc.)\n"
            f"{extra}"
        )
    SYSTEM = [
        {
            "type": "text",
            "text": f"{SUPPORT_PROMPT}{extra_block}\n\n<knowledge>\n{knowledge}\n</knowledge>",
            "cache_control": {"type": "ephemeral"},  # prompt caching
        }
    ]


rebuild_system()

MAX_HISTORY = 8  # số tin nhắn gần nhất giữ cho mỗi hội thoại (chẵn: user/assistant)
MAX_SESSIONS = 2000
_history: dict[str, list[dict]] = {}


def get_history(key: str) -> list[dict]:
    return list(_history.get(key, []))


def reset_history(key: str) -> None:
    _history.pop(key, None)


def _text_of(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text").strip()


async def answer(session_key: str, user_text: str, meta: dict | None = None) -> tuple[str, bool]:
    """Trả về (câu trả lời, đã báo admin?).

    meta (tuỳ chọn, từ bot Telegram/Discord): platform, channel_id, message_id, user_name, where.
    Có meta thì ghi nhật ký và, nếu cần, tạo yêu cầu trong hộp thư admin + báo admin.
    """
    if session_key not in _history and len(_history) >= MAX_SESSIONS:
        _history.pop(next(iter(_history)))
    hist = _history.setdefault(session_key, [])

    try:
        resp = await client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=700,
            system=SYSTEM,
            messages=hist + [{"role": "user", "content": user_text}],
        )
    except anthropic.APIError:
        log.exception("Lỗi gọi Claude API")
        if meta:
            db.log_conversation(meta["platform"], meta.get("where", ""), meta.get("user_name", ""),
                                user_text, "(lỗi API) " + ERROR, False)
        return ERROR, False

    reply = _text_of(resp)
    escalate = ADMIN_TAG in reply
    reply = reply.replace(ADMIN_TAG, "").strip()
    if not reply:
        return ERROR, False

    hist.extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}])
    del hist[:-MAX_HISTORY]

    if meta:
        db.log_conversation(meta["platform"], meta.get("where", ""), meta.get("user_name", ""),
                            user_text, reply, escalate)
        if escalate:
            db.add_escalation(meta["platform"], meta["channel_id"], meta["message_id"],
                              meta.get("user_name", ""), user_text)
            link = f"\nXem & trả lời: {config.ADMIN_PUBLIC_URL}/inbox" if config.ADMIN_PUBLIC_URL else ""
            await hub.notify_admin(
                f"Cần hỗ trợ [{meta['platform']}] {meta.get('user_name', '')} – {meta.get('where', '')}\n"
                f"Hỏi: {user_text[:500]}{link}"
            )
    return reply, escalate
