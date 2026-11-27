# Tổng quan dự án

Threads Studio Pro là ứng dụng desktop Python/PyQt6 để tạo video đọc thảo luận
Threads bằng tiếng Việt. Đầu vào là URL Threads hoặc kịch bản nhập tay;
đầu ra là MP4 dọc 1080×1920 kèm dữ liệu trung gian để kiểm tra.

## Người dùng và cách làm việc

Người làm video có thể đưa nhiều bài vào hàng đợi, kiểm tra lời đọc,
chọn nhiều giọng, chỉnh bố cục thẻ và video phụ, rồi xuất video.
Hệ thống hỗ trợ chờ duyệt hoặc tiếp tục render tự động.

## Thành phần chính

- `run_studio.py`: launcher từ thư mục dự án.
- `app.py`: chuẩn bị media mẫu, cấu hình, QApplication, theme và cửa sổ chính.
- `core`: dữ liệu, cấu hình và vòng đời job.
- `scrapers`: lấy bài/bình luận hoặc tách kịch bản nhập tay.
- `ai`: biến nội dung thành lời đọc; có OCR qua CLI và từ điển offline.
- `tts`: tạo âm thanh bằng CapCut, Edge hoặc VieNeu.
- `render`: vẽ thẻ và ghép video bằng FFmpeg.
- `ui`: giao diện Fluent Blue và sân khấu kéo thả.

Xem [kiến trúc](architecture.md) để biết cách các phần nối với nhau.

## Công nghệ và môi trường

- Python >=3.10; môi trường máy hiện tại dùng `.venv`.
- Fluent Blue/PyQt6, Playwright Chromium, Pillow, NumPy và thư viện âm thanh.
- FFmpeg/FFprobe để xử lý audio/video; có lựa chọn NVENC hoặc libx264.
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

Các tài liệu không thay thế việc chạy kiểm tra khi thay đổi code.
