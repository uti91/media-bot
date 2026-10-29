"""SQLite: cài đặt, nhật ký hội thoại, hộp thư cần hỗ trợ, truyện."""
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, platform TEXT, place TEXT,
    user_name TEXT, question TEXT, answer TEXT, escalated INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_conv_ts ON conversations(ts);
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, platform TEXT,
    channel_id INTEGER, message_id INTEGER, user_name TEXT, question TEXT,
    status TEXT DEFAULT 'open', admin_reply TEXT, resolved_ts TEXT);
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, title TEXT, body TEXT,
    status TEXT NOT NULL, source TEXT, posted_ts TEXT);
"""

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ago(**kw) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kw)).isoformat(timespec="seconds")


def init() -> None:
    global _conn
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(config.DATA_DIR / "kpowbot.db", check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(SCHEMA)
    _conn.commit()


def _all(sql: str, params=()) -> list[dict]:
    with _lock:
        return [dict(r) for r in _conn.execute(sql, params).fetchall()]


def _one(sql: str, params=()) -> dict | None:
    rows = _all(sql, params)
    return rows[0] if rows else None


def _exec(sql: str, params=()) -> int:
    with _lock:
        cur = _conn.execute(sql, params)
        _conn.commit()
        return cur.lastrowid


def _scalar(sql: str, params=()) -> int:
    with _lock:
        return _conn.execute(sql, params).fetchone()[0]


# ---- settings ----
def get_setting(key: str, default: str | None = None) -> str | None:
    row = _one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    _exec("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def delete_setting(key: str) -> None:
    _exec("DELETE FROM settings WHERE key=?", (key,))


# ---- conversations ----
def log_conversation(platform, place, user_name, question, answer, escalated) -> int:
    return _exec(
        "INSERT INTO conversations(ts,platform,place,user_name,question,answer,escalated) VALUES(?,?,?,?,?,?,?)",
        (now_iso(), platform, place, user_name, question[:2000], answer[:4000], 1 if escalated else 0),
    )


def list_conversations(platform: str | None = None, only_escalated: bool = False, limit: int = 100) -> list[dict]:
    where, params = [], []
    if platform:
        where.append("platform=?"); params.append(platform)
    if only_escalated:
        where.append("escalated=1")
    sql = "SELECT * FROM conversations" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?"
    return _all(sql, (*params, limit))


def purge_conversations(older_than_days: int | None = None) -> int:
    if older_than_days is None:
        n = _scalar("SELECT COUNT(*) FROM conversations")
        _exec("DELETE FROM conversations")
    else:
        cutoff = _ago(days=older_than_days)
        n = _scalar("SELECT COUNT(*) FROM conversations WHERE ts<?", (cutoff,))
        _exec("DELETE FROM conversations WHERE ts<?", (cutoff,))
    return n


# ---- escalations ----
def add_escalation(platform, channel_id, message_id, user_name, question) -> int:
    return _exec(
        "INSERT INTO escalations(ts,platform,channel_id,message_id,user_name,question) VALUES(?,?,?,?,?,?)",
        (now_iso(), platform, channel_id, message_id, user_name, question[:2000]),
    )


def list_escalations(status: str = "open", limit: int = 100) -> list[dict]:
    return _all("SELECT * FROM escalations WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit))


def get_escalation(eid: int) -> dict | None:
    return _one("SELECT * FROM escalations WHERE id=?", (eid,))


def resolve_escalation(eid: int, reply: str | None = None) -> None:
    _exec("UPDATE escalations SET status='resolved', admin_reply=?, resolved_ts=? WHERE id=?", (reply, now_iso(), eid))


def count_open_escalations() -> int:
    return _scalar("SELECT COUNT(*) FROM escalations WHERE status='open'")


# ---- stories ----
def add_story(title: str, body: str, status: str, source: str) -> int:
    return _exec("INSERT INTO stories(ts,title,body,status,source) VALUES(?,?,?,?,?)", (now_iso(), title, body, status, source))


def list_stories(limit: int = 40) -> list[dict]:
    return _all("SELECT * FROM stories ORDER BY id DESC LIMIT ?", (limit,))


def get_story(sid: int) -> dict | None:
    return _one("SELECT * FROM stories WHERE id=?", (sid,))


def update_story_body(sid: int, body: str) -> None:
    _exec("UPDATE stories SET body=?, title=? WHERE id=? AND status='draft'",
          (body, (body.splitlines() or [""])[0].strip()[:200], sid))


def mark_story_posted(sid: int, body: str) -> None:
    _exec("UPDATE stories SET status='posted', body=?, posted_ts=? WHERE id=?", (body, now_iso(), sid))


def delete_story(sid: int) -> None:
    _exec("DELETE FROM stories WHERE id=? AND status='draft'", (sid,))


def recent_story_titles(n: int = 5) -> list[str]:
    return [r["title"] for r in _all("SELECT title FROM stories ORDER BY id DESC LIMIT ?", (n,)) if r["title"]]


# ---- stats ----
def stats() -> dict:
    return {
        "conv_24h": _scalar("SELECT COUNT(*) FROM conversations WHERE ts>=?", (_ago(hours=24),)),
        "conv_total": _scalar("SELECT COUNT(*) FROM conversations"),
        "open_esc": count_open_escalations(),
        "stories_7d": _scalar("SELECT COUNT(*) FROM stories WHERE status='posted' AND posted_ts>=?", (_ago(days=7),)),
        "drafts": _scalar("SELECT COUNT(*) FROM stories WHERE status='draft'"),
    }


init()
