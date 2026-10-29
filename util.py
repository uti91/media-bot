import re
import time
from collections import defaultdict, deque


def split_message(text: str, limit: int) -> list[str]:
    """Cắt tin nhắn dài thành nhiều phần, ưu tiên cắt ở xuống dòng / dấu cách."""
    chunks: list[str] = []
    text = text.strip()
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


class RateLimiter:
    def __init__(self, max_calls: int, window: float = 60.0):
        self.max_calls = max_calls
        self.window = window
        self._calls: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._calls[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            return False
        q.append(now)
        return True


_HEX_KEY = re.compile(r"\b(0x)?[0-9a-fA-F]{64}\b")


def leaked_secret(text: str) -> bool:
    """Phát hiện người dùng lỡ dán seed phrase (12/15/18/21/24 từ) hoặc private key (64 hex)."""
    if _HEX_KEY.search(text):
        return True
    words = text.split()
    if len(words) in (12, 15, 18, 21, 24):
        return all(w.isalpha() and w.islower() and 3 <= len(w) <= 8 for w in words)
    return False
