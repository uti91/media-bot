"""Các nội dung cố định (không gọi AI) để đảm bảo chính xác tuyệt đối."""

NETWORK_INFO = """🔧 Thêm mạng KPOW vào ví EVM (MetaMask, v.v.):

• Network name: KPOW Coin
• RPC URL: https://rpc.kpowbit.com
• Chain ID: 112016
• Currency symbol: KPOW
• Block explorer: https://explorer.kpowbit.com

⚠️ Luôn đối chiếu lại với trang chính thức kpowbit.com trước khi gửi tiền."""

LINKS = """🔗 Kênh chính thức KpowBIT:

• Website: https://kpowbit.com
• Sàn giao dịch: https://trade.kpowbit.com
• Explorer: https://explorer.kpowbit.com
• GitHub: https://github.com/KpowBIT-Project
• X: https://x.com/KpowBIT
• Telegram: https://t.me/kpowbit
• Discord: https://discord.gg/f7F9RC3qtP

⚠️ Admin thật sẽ không bao giờ nhắn riêng để xin seed phrase / private key hay mời chuyển tiền."""

HELP = """👋 Mình là KPOW Assistant, quản lý ảo của cộng đồng KpowBIT.

Bạn có thể hỏi mình về: mạng KPOW, cách đào, pool, thêm mạng vào ví, tokenomics, roadmap, và cách dùng sàn KpowBIT.

Lệnh nhanh:
/network (hoặc !network) – thông số mạng để thêm vào ví
/links (hoặc !links) – các link chính thức
/story (hoặc !story) – nghe một câu chuyện cộng đồng
/id (hoặc !id) – xem ID của chat/kênh hiện tại

Trong nhóm, hãy @mention mình hoặc trả lời tin nhắn của mình nhé."""

SECRET_WARNING = """🚨 Tin nhắn của bạn có vẻ chứa seed phrase hoặc private key!

Hãy coi như đã bị lộ: chuyển tài sản sang ví mới ngay và đừng bao giờ chia sẻ thông tin này với bất kỳ ai, kể cả admin. Mình đã không xử lý nội dung đó và sẽ cố gắng xoá tin nhắn."""

RATE_LIMITED = "Bạn nhắn hơi nhanh, đợi mình một chút rồi hỏi tiếp nhé 🙏"
STORY_COOLDOWN = "Câu chuyện vừa được kể xong, quay lại sau ít phút nhé 📖"
ERROR = "Xin lỗi, mình đang gặp sự cố. Bạn thử lại sau ít phút hoặc nhắn admin giúp mình nhé 🙏"


def member_welcome(name: str) -> str:
    return (
        f"🎉 Chào mừng {name} đến với cộng đồng KpowBIT!\n\n"
        "• Gõ /help (hoặc !help) để xem mình giúp được gì\n"
        "• Thông số mạng KPOW: /network\n"
        "• Link chính thức: /links\n\n"
        "Hãy giới thiệu bản thân một chút để mọi người làm quen nhé. "
        "Lưu ý: admin thật sẽ không bao giờ nhắn riêng xin seed phrase hay mời chuyển tiền."
    )
