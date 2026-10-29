"""Trang quản trị (Flask). Chạy trong một luồng riêng; việc gọi bot/Claude được chuyển về event loop chính."""
import asyncio
import hashlib
import hmac
import logging
import re
import secrets
import shutil
import threading
from datetime import datetime, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, session

import brain
import config
import db
import hub
import stories
from util import RateLimiter

log = logging.getLogger(__name__)

LOOP: asyncio.AbstractEventLoop | None = None
TEST_KEY = "admin-test"
BACKUP_DIR = config.DATA_DIR / "knowledge_backups"
BACKUP_RE = re.compile(r"^kpow_\d{8}_\d{6}\.md$")
login_limiter = RateLimiter(5, window=300)

NAV = [
    ("/", "Tổng quan"),
    ("/inbox", "Cần hỗ trợ"),
    ("/chats", "Hội thoại"),
    ("/knowledge", "Kiến thức"),
    ("/persona", "Tính cách bot"),
    ("/stories", "Câu chuyện"),
    ("/announce", "Thông báo"),
    ("/test", "Thử bot"),
]


def run_async(coro, timeout: float = 120):
    """Chạy coroutine trên event loop chính (nơi Telegram/Discord/Claude đang hoạt động)."""
    if LOOP is None:
        coro.close()
        raise RuntimeError("Event loop chưa sẵn sàng")
    return asyncio.run_coroutine_threadsafe(coro, LOOP).result(timeout)


def _backup_knowledge() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    moment = datetime.now()
    while (BACKUP_DIR / f"kpow_{moment:%Y%m%d_%H%M%S}.md").exists():  # không bao giờ ghi đè bản cũ
        moment += timedelta(seconds=1)
    shutil.copyfile(brain.KNOWLEDGE_FILE, BACKUP_DIR / f"kpow_{moment:%Y%m%d_%H%M%S}.md")
    for old in sorted(BACKUP_DIR.glob("kpow_*.md"), reverse=True)[30:]:
        old.unlink(missing_ok=True)


def create_app() -> Flask:
    app = Flask(__name__)
    secret = config.ADMIN_SECRET or hashlib.sha256(f"kpowbot|{config.ADMIN_PASSWORD}".encode()).hexdigest()
    app.config.update(
        SECRET_KEY=secret,
        SESSION_COOKIE_NAME="kpow_admin",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=config.ADMIN_COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=1_000_000,
    )
    if config.ADMIN_BEHIND_PROXY:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # ---------- bảo mật ----------
    @app.before_request
    def guard():
        if request.endpoint in ("login", "static"):
            return None
        if not session.get("auth"):
            return redirect("/login")
        if request.method == "POST":
            sent = request.form.get("csrf", "")
            if not hmac.compare_digest(sent, session.get("csrf", "")):
                abort(403)
        return None

    @app.after_request
    def headers(resp):
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        return resp

    @app.context_processor
    def inject():
        return {
            "nav": NAV,
            "csrf_token": session.get("csrf", ""),
            "open_count": db.count_open_escalations() if session.get("auth") else 0,
        }

    @app.template_filter("ts")
    def ts_filter(iso):
        if not iso:
            return ""
        try:
            return datetime.fromisoformat(iso).astimezone(config.TIMEZONE).strftime("%d/%m %H:%M")
        except ValueError:
            return iso

    # ---------- đăng nhập ----------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            if not login_limiter.allow(request.remote_addr or "?"):
                flash("Thử quá nhiều lần. Vui lòng đợi 5 phút.", "err")
                return render_template("login.html"), 429
            pw = request.form.get("password", "")
            if hmac.compare_digest(pw.encode(), config.ADMIN_PASSWORD.encode()):
                session.clear()
                session["auth"] = True
                session["csrf"] = secrets.token_hex(16)
                session.permanent = True
                return redirect("/")
            flash("Sai mật khẩu.", "err")
        return render_template("login.html")

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect("/login")

    # ---------- tổng quan ----------
    @app.get("/")
    def dashboard():
        return render_template(
            "dashboard.html",
            s=db.stats(),
            st=hub.status(),
            cfg=stories.get_settings(),
            last_story=db.get_setting("story_last_date"),
            tg_target=config.TELEGRAM_COMMUNITY_CHAT_ID,
            dc_target=config.DISCORD_STORY_CHANNEL_ID,
            tg_admin=config.TELEGRAM_ADMIN_CHAT_ID,
            dc_admin=config.DISCORD_ADMIN_CHANNEL_ID,
        )

    # ---------- hộp thư cần hỗ trợ ----------
    @app.get("/inbox")
    def inbox():
        status = request.args.get("status", "open")
        if status not in ("open", "resolved"):
            status = "open"
        return render_template("inbox.html", rows=db.list_escalations(status), status=status)

    @app.post("/inbox/<int:eid>/reply")
    def inbox_reply(eid):
        row = db.get_escalation(eid)
        text = request.form.get("text", "").strip()
        if not row:
            flash("Không tìm thấy yêu cầu.", "err")
        elif not text:
            flash("Chưa nhập nội dung trả lời.", "err")
        else:
            try:
                run_async(hub.reply_in(row["platform"], row["channel_id"], row["message_id"], "👤 Admin: " + text))
                db.resolve_escalation(eid, text)
                flash("Đã gửi trả lời và đánh dấu đã xử lý.", "ok")
            except Exception as e:
                log.exception("Gửi trả lời thất bại")
                flash(f"Gửi thất bại: {e}", "err")
        return redirect("/inbox")

    @app.post("/inbox/<int:eid>/resolve")
    def inbox_resolve(eid):
        if db.get_escalation(eid):
            db.resolve_escalation(eid)
            flash("Đã đánh dấu đã xử lý.", "ok")
        return redirect("/inbox")

    # ---------- nhật ký hội thoại ----------
    @app.get("/chats")
    def chats():
        platform = request.args.get("platform", "")
        platform = platform if platform in ("telegram", "discord") else None
        only_esc = request.args.get("esc") == "1"
        return render_template(
            "chats.html",
            rows=db.list_conversations(platform, only_esc),
            platform=platform or "",
            only_esc=only_esc,
            retention=config.LOG_RETENTION_DAYS,
        )

    @app.post("/chats/purge")
    def chats_purge():
        n = db.purge_conversations(None)
        flash(f"Đã xoá {n} hội thoại.", "ok")
        return redirect("/chats")

    # ---------- kiến thức ----------
    @app.get("/knowledge")
    def knowledge():
        backups = sorted(BACKUP_DIR.glob("kpow_*.md"), reverse=True)[:10] if BACKUP_DIR.exists() else []
        return render_template(
            "knowledge.html",
            content=brain.KNOWLEDGE_FILE.read_text(encoding="utf-8"),
            backups=[b.name for b in backups],
        )

    @app.post("/knowledge")
    def knowledge_save():
        text = request.form.get("content", "").replace("\r\n", "\n").strip()
        if len(text) < 50:
            flash("Nội dung quá ngắn, không lưu để tránh xoá nhầm.", "err")
        elif len(text) > 150_000:
            flash("Nội dung quá dài (tối đa 150.000 ký tự).", "err")
        else:
            _backup_knowledge()
            brain.KNOWLEDGE_FILE.write_text(text + "\n", encoding="utf-8")
            brain.rebuild_system()
            flash("Đã lưu. Bot dùng kiến thức mới ngay từ tin nhắn tiếp theo.", "ok")
        return redirect("/knowledge")

    @app.post("/knowledge/restore")
    def knowledge_restore():
        name = request.form.get("name", "")
        path = BACKUP_DIR / name
        if not BACKUP_RE.match(name) or not path.is_file():
            flash("Bản sao lưu không hợp lệ.", "err")
        else:
            _backup_knowledge()
            shutil.copyfile(path, brain.KNOWLEDGE_FILE)
            brain.rebuild_system()
            flash(f"Đã khôi phục {name}.", "ok")
        return redirect("/knowledge")

    @app.post("/knowledge/reset")
    def knowledge_reset():
        _backup_knowledge()
        shutil.copyfile(brain.DEFAULT_KNOWLEDGE_FILE, brain.KNOWLEDGE_FILE)
        brain.rebuild_system()
        flash("Đã đặt lại về bản kiến thức mặc định đi kèm mã nguồn.", "ok")
        return redirect("/knowledge")

    # ---------- tính cách ----------
    @app.get("/persona")
    def persona():
        from prompts import SUPPORT_PROMPT
        return render_template("persona.html", extra=db.get_setting("extra_instructions", ""), core=SUPPORT_PROMPT)

    @app.post("/persona")
    def persona_save():
        extra = request.form.get("extra", "").replace("\r\n", "\n").strip()
        if len(extra) > 5000:
            flash("Tối đa 5.000 ký tự.", "err")
        else:
            db.set_setting("extra_instructions", extra)
            brain.rebuild_system()
            flash("Đã lưu hướng dẫn bổ sung.", "ok")
        return redirect("/persona")

    # ---------- câu chuyện ----------
    @app.get("/stories")
    def stories_page():
        return render_template(
            "stories.html",
            cfg=stories.get_settings(),
            themes="\n".join(stories.get_themes()),
            rows=db.list_stories(40),
            tg_target=config.TELEGRAM_COMMUNITY_CHAT_ID,
            dc_target=config.DISCORD_STORY_CHANNEL_ID,
        )

    @app.post("/stories/settings")
    def stories_settings():
        try:
            hour = int(request.form.get("hour", "19"))
        except ValueError:
            hour = 19
        stories.save_settings(request.form.get("enabled") == "on", hour, request.form.get("mode", "auto"))
        flash("Đã lưu cài đặt truyện hằng ngày.", "ok")
        return redirect("/stories")

    @app.post("/stories/themes")
    def stories_themes():
        lines = [ln.strip()[:300] for ln in request.form.get("themes", "").splitlines() if ln.strip()][:50]
        stories.set_themes(lines)
        flash("Đã lưu danh sách chủ đề." if lines else "Đã đặt lại chủ đề mặc định.", "ok")
        return redirect("/stories")

    @app.post("/stories/generate")
    def stories_generate():
        theme = request.form.get("theme", "").strip() or None
        try:
            run_async(stories.generate_story(status="draft", source="manual", theme=theme))
            flash("Đã tạo bản nháp mới. Xem và chỉnh sửa bên dưới.", "ok")
        except Exception as e:
            log.exception("Tạo truyện thất bại")
            flash(f"Tạo truyện thất bại: {e}", "err")
        return redirect("/stories")

    @app.post("/stories/<int:sid>/save")
    def story_save(sid):
        body = request.form.get("body", "").replace("\r\n", "\n").strip()
        if not body:
            flash("Nội dung trống.", "err")
        else:
            db.update_story_body(sid, body)
            flash("Đã lưu bản nháp.", "ok")
        return redirect("/stories")

    @app.post("/stories/<int:sid>/post")
    def story_post(sid):
        body = request.form.get("body", "").replace("\r\n", "\n")
        try:
            res = run_async(stories.publish_story(sid, body))
            names = {"telegram": "Telegram", "discord": "Discord"}
            flash("Đã đăng: " + ", ".join(f"{names[k]} {'✅' if v else '❌'}" for k, v in res.items()), "ok")
        except Exception as e:
            flash(str(e), "err")
        return redirect("/stories")

    @app.post("/stories/<int:sid>/delete")
    def story_delete(sid):
        db.delete_story(sid)
        flash("Đã xoá bản nháp.", "ok")
        return redirect("/stories")

    # ---------- thông báo ----------
    @app.get("/announce")
    def announce():
        return render_template("announce.html", tg_target=config.TELEGRAM_COMMUNITY_CHAT_ID,
                               dc_target=config.DISCORD_STORY_CHANNEL_ID)

    @app.post("/announce")
    def announce_post():
        text = request.form.get("text", "").strip()
        tg, dc = request.form.get("tg") == "on", request.form.get("dc") == "on"
        if not text:
            flash("Chưa nhập nội dung.", "err")
        elif not (tg or dc):
            flash("Hãy chọn ít nhất một nền tảng.", "err")
        else:
            res = run_async(hub.broadcast(text, telegram=tg, discord=dc))
            if not res:
                flash("Nền tảng đã chọn chưa được cấu hình ID kênh trong .env.", "err")
            else:
                names = {"telegram": "Telegram", "discord": "Discord"}
                ok = any(res.values())
                flash("Kết quả: " + ", ".join(f"{names[k]} {'✅' if v else '❌'}" for k, v in res.items()),
                      "ok" if ok else "err")
        return redirect("/announce")

    # ---------- thử bot ----------
    @app.get("/test")
    def test_page():
        return render_template("test.html", history=brain.get_history(TEST_KEY), esc=request.args.get("esc") == "1")

    @app.post("/test")
    def test_post():
        text = request.form.get("text", "").strip()[:1000]
        esc = False
        if text:
            try:
                _, esc = run_async(_test_answer(text))
            except Exception as e:
                flash(f"Lỗi: {e}", "err")
        return redirect("/test?esc=1" if esc else "/test")

    @app.post("/test/reset")
    def test_reset():
        brain.reset_history(TEST_KEY)
        return redirect("/test")

    return app


async def _test_answer(text: str):
    """Hỏi thử bot bằng đúng kiến thức đang dùng; KHÔNG ghi nhật ký, KHÔNG báo admin."""
    return await brain.answer(TEST_KEY, text)


def start_in_thread(loop: asyncio.AbstractEventLoop):
    global LOOP
    LOOP = loop
    app = create_app()
    try:
        from waitress import create_server
        server = create_server(app, host=config.ADMIN_HOST, port=config.ADMIN_PORT, threads=4)
        target = server.run
    except ImportError:
        from werkzeug.serving import make_server
        server = make_server(config.ADMIN_HOST, config.ADMIN_PORT, app, threaded=True)
        target = server.serve_forever
    threading.Thread(target=target, daemon=True, name="admin-web").start()
    return server
