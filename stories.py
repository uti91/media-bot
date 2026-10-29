import json
import logging

import config
import db
import hub
from brain import _text_of, client
from prompts import STORY_PROMPT

log = logging.getLogger(__name__)

DEFAULT_THEMES = [
    "Người mới đào block đầu tiên và cảm giác khi thấy mình trở thành một phần của mạng lưới",
    "Một nhóm bạn ở xa cùng ghép máy đào cũ lại, học hỏi từng bước qua kênh chat cộng đồng",
    "Đêm khuya, một thành viên giúp người lạ thêm mạng KPOW vào ví thành công",
    "Câu chuyện về sự kiên nhẫn: mỗi 13 giây một block mới, từng viên gạch nhỏ xây nên chuỗi",
    "Một nhà phát triển trẻ đọc mã nguồn mở của mạng và gửi đóng góp đầu tiên",
    "Người đào lâu năm kể lại cho người mới nghe vì sao thích sự minh bạch của Proof-of-Work",
    "Một thành viên phát hiện và cảnh báo cả nhóm về một tin nhắn lừa đảo, cộng đồng cùng nhau giữ an toàn",
    "Ngày đầu tiên của một người mới tham gia nhóm: ngại ngùng, rồi được chào đón nồng nhiệt",
    "Cuộc thi nhỏ trong cộng đồng: ai giải thích lịch phần thưởng 2 → 1 → 0,5 dễ hiểu nhất",
    "Hai người ở hai múi giờ khác nhau cùng canh một block explorer và bắt chuyện",
]

DISCLAIMER = "\n\n📖 Truyện hư cấu, nhằm mục đích giải trí và kết nối cộng đồng. Không phải lời khuyên đầu tư."


def get_themes() -> list[str]:
    raw = db.get_setting("themes")
    if raw:
        try:
            themes = [t.strip() for t in json.loads(raw) if isinstance(t, str) and t.strip()]
            if themes:
                return themes
        except json.JSONDecodeError:
            pass
    return list(DEFAULT_THEMES)


def set_themes(themes: list[str]) -> None:
    if themes:
        db.set_setting("themes", json.dumps(themes, ensure_ascii=False))
    else:
        db.delete_setting("themes")  # về mặc định


def get_settings() -> dict:
    mode = db.get_setting("story_mode", config.STORY_MODE)
    return {
        "enabled": db.get_setting("story_enabled", "1" if config.STORY_ENABLED else "0") == "1",
        "hour": int(db.get_setting("story_hour", str(config.STORY_HOUR))),
        "mode": mode if mode in ("auto", "approve") else "auto",
    }


def save_settings(enabled: bool, hour: int, mode: str) -> None:
    db.set_setting("story_enabled", "1" if enabled else "0")
    db.set_setting("story_hour", str(max(0, min(23, hour))))
    db.set_setting("story_mode", mode if mode in ("auto", "approve") else "auto")


async def generate_story(status: str = "draft", source: str = "auto", theme: str | None = None) -> dict:
    """Tạo truyện và lưu vào database. status: draft (chờ đăng) hoặc adhoc (theo yêu cầu, không đăng kênh)."""
    if theme:
        chosen = theme.strip()[:300]
    else:
        themes = get_themes()
        idx = int(db.get_setting("story_index", "0"))
        chosen = themes[idx % len(themes)]
        db.set_setting("story_index", str(idx + 1))
    avoid = "; ".join(db.recent_story_titles(5)) or "(chưa có)"
    resp = await client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=900,
        system=STORY_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Chủ đề hôm nay: {chosen}\n"
                       f"Tránh trùng tiêu đề, nhân vật hoặc ý tưởng với các truyện gần đây: {avoid}",
        }],
    )
    body = _text_of(resp)
    if not body:
        raise RuntimeError("Claude trả về truyện rỗng")
    title = body.splitlines()[0].strip()[:200]
    sid = db.add_story(title, body, status, source)
    return {"id": sid, "title": title, "body": body}


async def publish_story(story_id: int, body: str | None = None) -> dict[str, bool]:
    """Đăng một bản nháp lên các kênh cộng đồng rồi đánh dấu đã đăng."""
    row = db.get_story(story_id)
    if not row or row["status"] != "draft":
        raise ValueError("Không tìm thấy bản nháp (có thể đã đăng hoặc đã xoá)")
    text = (body if body is not None else row["body"]).strip()
    if not text:
        raise ValueError("Nội dung truyện đang trống")
    results = await hub.broadcast(text + DISCLAIMER)
    if not any(results.values()):
        raise RuntimeError(
            "Không đăng được lên kênh nào. Kiểm tra TELEGRAM_COMMUNITY_CHAT_ID / "
            "DISCORD_STORY_CHANNEL_ID và quyền của bot."
        )
    db.mark_story_posted(story_id, text)
    return results
