# KIẾN THỨC CHÍNH THỨC VỀ KPOWBIT
(Nguồn: kpowbit.com và trade.kpowbit.com. Cập nhật file này mỗi khi dự án có thay đổi.)

## 1. KPOW Network (kpowbit.com)
- KPOW là coin Proof-of-Work dùng thuật toán Ethash, tương thích EVM, dựa trên bản fork của Ethereum Classic core-geth, với luật đồng thuận và phát hành riêng của dự án.
- Tổng cung tối đa: 21.000.000 KPOW.
  - 70% (14.700.000 KPOW) là phần thưởng đào (base reward), phát theo lịch công bố.
  - 30% (6.300.000 KPOW) cho các địa chỉ genesis. Bản đặc tả chỉ xác nhận hai số dư genesis; nhãn "20% hệ sinh thái/thanh khoản" và "10% phát triển" là mục đích cấp dự án, chưa xác nhận về hạn chế chi tiêu hay vesting.
- Block time mục tiêu: 13 giây. Điều chỉnh độ khó theo EMA (cửa sổ làm mượt 8 block).
- Lịch phần thưởng base reward mỗi block:
  - Block 0 – 3.999.999: 2,0 KPOW/block (tổng 8.000.000 KPOW)
  - Block 4.000.000 – 8.399.999: 1,0 KPOW/block (tổng 4.400.000 KPOW)
  - Block 8.400.000 – 12.999.999: 0,5 KPOW/block (tổng 2.300.000 KPOW)
  - Từ block 13.000.000: base reward kết thúc (0 KPOW)
- Uncle reward được quy định riêng bởi giao thức và có thể ảnh hưởng tổng lượng phát hành. Muốn biết lượng phát hành hiện tại, xem dữ liệu on-chain trên explorer.
- Số liệu thời gian thực (block height, hashrate, độ khó, gas price, lượng KPOW đã đào) hiển thị trên kpowbit.com và explorer. Bot KHÔNG biết các số này, phải hướng dẫn người dùng xem explorer.

## 2. Thông số mạng (Mainnet)
- Network name: KPOW Coin
- RPC URL: https://rpc.kpowbit.com
- Chain ID: 112016
- Currency symbol: KPOW
- Block explorer: https://explorer.kpowbit.com
- Cách thêm vào MetaMask (hoặc ví EVM tương tự): Settings → Networks → Add network → Add a network manually → điền các thông số trên → Save. Luôn kiểm tra lại thông số trên kpowbit.com trước khi gửi tiền.

## 3. Cách đào KPOW
- Dùng miner hỗ trợ Ethash và trỏ về một pool hoặc đào solo bằng node.
- Mã nguồn node: https://github.com/KpowBIT-Project/kpow-geth (wallet và bản phát hành: https://github.com/KpowBIT-Project).
- Pool cộng đồng được liệt kê trên website:
  - CoolPool: coolpool.top
  - GTPool: gtpool.io
- Luôn kiểm tra địa chỉ pool và mức phí trên website chính thức của pool trước khi đào. Dự án không đảm bảo lợi nhuận khi đào.
- Bot không có thông tin chi tiết về cấu hình stratum, cổng kết nối, phí pool, hay miner cụ thể nào tương thích. Với các câu hỏi đó: hướng dẫn xem trang pool hoặc hỏi trong cộng đồng, và báo admin.

## 4. Roadmap (chỉ là mục tiêu, không phải cam kết, có thể thay đổi)
- Q3 2026 – Presale & Community: công bố điều khoản bán, phát triển cộng đồng, báo cáo phân bổ minh bạch, tài liệu dự án.
- Q4 2026 – KPOW Network: hạ tầng mạng công khai, tích hợp node và đào, RPC và explorer, kiểm thử mainnet.
- Q1 2027 – Exchange Era: tiếp tục vận hành sàn, tích hợp nạp/rút và giao dịch spot cho mạng KPOW khi đủ điều kiện.
- Q2 2027 – Mining Rental: ý tưởng marketplace cho thuê sức đào, nhà cung cấp, theo dõi hợp đồng, thanh toán.
- 2027+ – Open Utility: mở rộng tích hợp hệ sinh thái, tài nguyên cho nhà phát triển.

## 5. KpowBIT Exchange (trade.kpowbit.com)
- Sàn giao dịch crypto quảng bá hướng "privacy-first", hỗ trợ truy cập No-KYC cho giao dịch crypto tiêu chuẩn: đăng ký bằng email, bảo vệ tài khoản bằng 2FA. Trang chủ ghi rõ "có thể áp dụng thêm kiểm tra khi pháp luật yêu cầu".
- Sản phẩm/dịch vụ: Trade (giao dịch toàn màn hình, ví dụ cặp BTC/USDT), Wallet, Spot Order (lệnh đang mở, lịch sử), Market List, Coin List, bảng phí, Announcements, Submit Listing (nộp hồ sơ niêm yết), Staking, Referral Program, API Documentation, TradingView chart.
- Lending và Airdrop: đang ở trạng thái "coming soon".
- Các trang chính (đều trên trade.kpowbit.com):
  - Ví: /wallet
  - Thị trường: /markets
  - Danh sách coin: /coins
  - Bảng phí nạp/rút/giao dịch: /coins?tab=crypto_fee
  - Thông báo: /announcements
  - Niêm yết: /listing
  - Staking: /stake
  - Giới thiệu bạn bè: /referral-program
  - Liên hệ hỗ trợ: /contact
  - Tài liệu API: /api-docs
  - Bảo mật tài khoản: /profile/security
- Bảo mật được quảng bá: mã hoá TLS, 2FA, lưu trữ an toàn, giám sát 24/7.
- Bot KHÔNG tra cứu được tài khoản, số dư, lệnh, nạp/rút của bất kỳ người dùng nào.

## 6. Kênh chính thức
- Website: https://kpowbit.com
- Sàn: https://trade.kpowbit.com
- Explorer: https://explorer.kpowbit.com
- RPC: https://rpc.kpowbit.com
- GitHub: https://github.com/KpowBIT-Project
- X: https://x.com/KpowBIT
- Telegram: https://t.me/kpowbit
- Discord: https://discord.gg/f7F9RC3qtP

## 7. Lưu ý chung của dự án
- Tài sản số có rủi ro. Website chỉ mang tính thông tin, không đảm bảo lợi nhuận đào hay lợi nhuận đầu tư.

## 8. Những điều bot CHƯA biết (không được bịa, phải báo admin)
- Ngày, giá, điều khoản cụ thể của presale.
- Danh sách và số dư địa chỉ genesis, điều khoản vesting/khoá.
- Mức phí cụ thể (xem bảng phí chính thức), hạn mức nạp/rút, mạng được hỗ trợ cho từng coin.
- Tình trạng một giao dịch, tài khoản, hay yêu cầu hỗ trợ cụ thể.
- Thông tin pháp lý/giấy phép theo từng quốc gia.
- Kế hoạch niêm yết trên sàn khác, giá KPOW, dự đoán giá.
