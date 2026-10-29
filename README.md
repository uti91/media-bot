# KPOW Assistant – Quản lý ảo cho Telegram & Discord (kèm trang Admin)

Một backend Python chạy đồng thời bot Telegram, bot Discord và trang quản trị web. Claude API là "bộ não".

## Tính năng

**Bot**
- Hỗ trợ user về KpowBIT (mạng KPOW, đào, pool, thêm ví, tokenomics, roadmap, sàn) dựa trên kho kiến thức.
- Đăng truyện cộng đồng hằng ngày (tự đăng hoặc chờ admin duyệt) + lệnh `/story` `!story`.
- Chào thành viên mới; lệnh tĩnh chính xác `/network` `/links` `/help` `/id` (Discord dùng `!`).
- An toàn: phát hiện người dùng dán seed phrase/private key (xoá tin, không gửi cho AI), giới hạn tốc độ, AI không bịa ngoài kiến thức.

**Trang Admin** (`http://127.0.0.1:8080`)
| Trang | Làm gì |
|---|---|
| Tổng quan | Trạng thái 2 bot, số hội thoại, yêu cầu chờ, truyện đã đăng |
| Cần hỗ trợ | Câu bot không trả lời được. **Trả lời thẳng từ web**, tin được gửi vào đúng cuộc trò chuyện gốc |
| Hội thoại | Xem nhật ký hỏi–đáp để rà chất lượng, lọc theo nền tảng, xoá toàn bộ |
| Kiến thức | Sửa kho kiến thức, **áp dụng ngay không cần khởi động lại**, tự sao lưu và khôi phục |
| Tính cách bot | Thêm hướng dẫn riêng (giọng điệu, cách xưng hô). Không ghi đè được quy tắc an toàn |
| Câu chuyện | Bật/tắt, đổi giờ, chọn tự đăng/chờ duyệt, sửa danh sách chủ đề, tạo và chỉnh bản nháp rồi đăng |
| Thông báo | Đăng tin tuỳ ý lên kênh cộng đồng dưới tên bot |
| Thử bot | Hỏi thử bằng đúng kiến thức đang dùng, không ghi nhật ký |

## 1. Chuẩn bị

**Anthropic API key**: https://console.anthropic.com → API Keys (nên đặt giới hạn chi tiêu hàng tháng).

**Bot Telegram**
1. Chat với **@BotFather** → `/newbot` → lấy token.
2. Thêm bot vào nhóm cộng đồng; cấp quyền admin (Delete messages) để xoá được tin lộ seed phrase.
3. Gõ `/id` trong nhóm để lấy Chat ID (số âm) → `TELEGRAM_COMMUNITY_CHAT_ID`. Tạo thêm một nhóm riêng cho admin, lấy ID tương tự → `TELEGRAM_ADMIN_CHAT_ID`.
4. Nếu bot không thấy tin trong nhóm: BotFather → Bot Settings → Group Privacy → Turn off.

**Bot Discord**
1. https://discord.com/developers/applications → New Application → tab Bot → lấy token.
2. Bật **Message Content Intent** và **Server Members Intent**.
3. OAuth2 → URL Generator: scope `bot`; quyền View Channels, Send Messages, Read Message History, Manage Messages. Mở URL để mời bot.
4. Gõ `!id` trong kênh để lấy Channel ID, điền vào `.env`.

## 2. Cài đặt & chạy

```bash
cd kpowbot
python3 -m venv venv && source venv/bin/activate     # Python 3.10+
pip install -r requirements.txt
cp .env.example .env        # điền key, token, ID và ADMIN_PASSWORD
python main.py
```
Mở `http://127.0.0.1:8080`, đăng nhập bằng `ADMIN_PASSWORD`.

**Kiểm tra nhanh**: vào trang *Thử bot* hỏi "Chain ID của KPOW là gì?" và "Khi nào presale?" (câu sau phải báo sẽ chuyển admin). Rồi nhắn thật trên Telegram/Discord và xem trang *Hội thoại*, *Cần hỗ trợ*.

## 3. Truy cập trang admin an toàn

Mặc định trang admin chỉ mở trên chính máy chủ (`127.0.0.1`). Có hai cách dùng từ xa:
- **SSH tunnel (đơn giản, an toàn nhất)**: `ssh -L 8080:127.0.0.1:8080 user@server` rồi mở `http://127.0.0.1:8080` trên máy bạn.
- **Reverse proxy HTTPS** (Caddy/nginx): proxy tới `127.0.0.1:8080`, rồi đặt `ADMIN_COOKIE_SECURE=true`, `ADMIN_BEHIND_PROXY=true`, `ADMIN_PUBLIC_URL=https://admin.ten-mien-cua-ban`. Không nên mở cổng 8080 thẳng ra Internet qua HTTP.

Bảo vệ có sẵn: mật khẩu ≥ 8 ký tự, giới hạn 5 lần đăng nhập sai/5 phút, cookie HttpOnly + SameSite=Strict, token CSRF cho mọi thao tác ghi, tự đăng xuất sau 12 giờ, chặn nhúng khung (clickjacking). Hãy dùng mật khẩu dài và độc nhất.

## 4. Chạy 24/7

**Docker**
```bash
docker build -t kpowbot .
docker run -d --name kpowbot --restart unless-stopped --env-file .env \
  -v kpowbot-data:/app/data -p 127.0.0.1:8080:8080 kpowbot
```
Volume `kpowbot-data` giữ database, kiến thức đã sửa và bản sao lưu khi cập nhật container.

**systemd** (`/etc/systemd/system/kpowbot.service`)
```ini
[Unit]
Description=KPOW Assistant
After=network-online.target

[Service]
WorkingDirectory=/opt/kpowbot
ExecStart=/opt/kpowbot/venv/bin/python main.py
Restart=always
User=kpowbot

[Install]
WantedBy=multi-user.target
```
`sudo systemctl enable --now kpowbot`

## 5. Quy trình vận hành gợi ý
1. **Tuần đầu**: để `STORY_MODE=approve`, đọc từng bản nháp trước khi đăng. Khi tin tưởng chất lượng thì chuyển sang tự đăng ở trang *Câu chuyện*.
2. **Mỗi ngày**: mở *Cần hỗ trợ*, trả lời các câu bot chuyển lên.
3. **Mỗi tuần**: xem *Hội thoại*, thấy câu nào bot trả lời yếu hoặc thiếu thông tin thì bổ sung vào *Kiến thức*. Đây là cách nâng chất lượng nhanh nhất.
4. Có tin mới (presale, phí, pool, roadmap) thì sửa *Kiến thức* ngay và dùng *Thử bot* để kiểm tra, rồi đăng *Thông báo*.

## 6. Lưu ý
- **Không commit `.env`** (đã có trong `.gitignore`).
- Nhật ký hội thoại có chứa nội dung người dùng nhắn. Mặc định tự xoá sau 30 ngày (`LOG_RETENTION_DAYS`); bạn nên thông báo điều này trong luật nhóm. Nhật ký không lưu tin nhắn bị phát hiện chứa seed phrase.
- Lịch sử hội thoại với AI (để hiểu ngữ cảnh) chỉ nằm trong RAM, mất khi khởi động lại.
- Bot được dặn không dự đoán giá, không hứa lợi nhuận, không tư vấn đầu tư. Đừng nới lỏng các quy tắc này.
- Truyện luôn gắn nhãn "hư cấu"; đừng dùng AI bịa lời chứng thực của người thật.
- Với dự án crypto, nên tham khảo tư vấn pháp lý về cách truyền thông (đặc biệt về No-KYC) ở các quốc gia bạn nhắm tới.

## Cấu trúc
```
main.py            # chạy 2 bot + admin + lịch đăng truyện
admin_web.py       # trang admin (Flask), templates/*.html
brain.py           # gọi Claude, prompt caching, nhật ký, báo admin
db.py              # SQLite: cài đặt, hội thoại, hộp thư, truyện
stories.py         # tạo / duyệt / đăng truyện
prompts.py         # quy tắc cốt lõi của bot (sửa cần khởi động lại)
telegram_bot.py, discord_bot.py, hub.py, static_texts.py, util.py, config.py
knowledge/kpow.md  # kiến thức mặc định; bản đang dùng nằm ở data/kpow.md
```
