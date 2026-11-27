# Tổng quan dự án

Threads Studio Pro là ứng dụng web local React + Tailwind với backend Python để tạo video đọc thảo luận
Threads bằng tiếng Việt. Đầu vào là URL Threads hoặc kịch bản nhập tay;
đầu ra là MP4 dọc 1080×1920 hoặc ngang 1920×1080 kèm dữ liệu trung gian để kiểm tra.

## Người dùng và cách làm việc

Người làm video có thể đưa nhiều bài vào hàng đợi, kiểm tra lời đọc,
chọn nhiều giọng, chỉnh bố cục thẻ và video phụ, rồi xuất video.
Hệ thống hỗ trợ chờ duyệt hoặc tiếp tục render tự động.

## Thành phần chính

- `run_studio.py`: launcher từ thư mục dự án.
- `app.py`: chuẩn bị media mẫu/cấu hình, mặc định chạy web; `--desktop` mở Qt cũ.
- `web_server.py`: API aiohttp, hàng đợi Python, ảnh thẻ và media trên loopback.
- `web/`: source React + Tailwind, build bằng Vite vào `ui/web/`.
- `core`: dữ liệu, cấu hình và vòng đời job.
- `scrapers`: lấy bài/bình luận hoặc tách kịch bản nhập tay.
- `ai`: biến nội dung thành lời đọc; có OCR qua CLI và từ điển offline.
- `tts`: tạo âm thanh bằng CapCut, Edge hoặc VieNeu.
- `render`: vẽ thẻ và ghép video bằng FFmpeg.
- `ui`: bản build web và giao diện Fluent Blue dự phòng.

Xem [kiến trúc](architecture.md) để biết cách các phần nối với nhau.

## Công nghệ và môi trường

- Python >=3.10; môi trường máy hiện tại dùng `.venv`.
- React/Tailwind, aiohttp, Qt renderer, Playwright Edge, Pillow, NumPy và thư viện âm thanh.
- FFmpeg/FFprobe để xử lý audio/video; có lựa chọn NVENC hoặc libx264.
- Edge đọc trực tiếp Threads, cuộn 10 lần và xếp hạng bình luận đã tải; không cần token thu thập.
- AI bằng Codex CLI đăng nhập ChatGPT hoặc Antigravity CLI đăng nhập Google.
- Windows là môi trường sử dụng hiện tại; không tuyên bố đã xác minh toàn bộ OS khác.

## Những điều cần phân biệt

- Model AI xử lý nội dung không tạo ra giọng nói; TTS tạo âm thanh riêng.
- Offline ở phần AI nghĩa là dùng từ điển, không đồng nghĩa cả pipeline offline.
- Có CLI trên máy không có nghĩa CLI đã được nối vào app.
- Antigravity CLI đã thay Gemini CLI trong app, không cần cài App/IDE.
- Số giọng và model khả dụng phụ thuộc thư viện, dịch vụ và quyền tài khoản.

## Trạng thái kiểm chứng

Ngày 26/11/2026: đã xác minh luồng Python gọi Codex Luna với văn bản/ảnh,
giao diện chọn provider/model và các nhánh lỗi CLI bằng kiểm tra tạm.
Gemini CLI cũ bị Google từ chối; app đã chuyển sang Antigravity CLI.
Luồng văn bản của Antigravity đã được kiểm tra thực tế.
Đây là ghi nhận tại thời điểm kiểm tra, không phải cam kết dịch vụ luôn khả dụng.

Luồng thu thập đã chuyển sang Edge trực tiếp; xem [module scraping](../modules/scraping.md).
Đã kiểm tra Edge thật cuộn 10 lần và xếp lượt thích trên bài công khai;
nhánh đăng nhập/profile riêng được kiểm tra bằng mock, chưa dùng tài khoản thật.
UI nhập file nền, tỷ lệ và preset đã được kiểm tra; một video khoảng một phút
đã render thật từ nền Minecraft và bình luận công khai với sound do AI chọn.

Các tài liệu không thay thế việc chạy kiểm tra khi thay đổi code.
