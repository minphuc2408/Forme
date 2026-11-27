# Cài đặt và chạy cho người mới

Chạy lệnh từ thư mục gốc chứa `run_studio.py` và `pyproject.toml`.
Ví dụ dùng PowerShell trên Windows; thay đường dẫn theo máy của bạn.

## Yêu cầu

- Python >=3.10; khuyến nghị 3.11 như môi trường hiện tại.
- FFmpeg và FFprobe có trên PATH.
- Node.js >=20 nếu cài Codex CLI qua npm; Antigravity CLI dùng binary riêng.
- Chromium của Playwright nếu cào URL Threads.
- Internet cho nguồn AI/TTS online và thu thập Threads.

## Môi trường Python

Nếu đã có `.venv`, dùng lại, không tạo đè.
Trên máy mới, chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m playwright install chromium
ffmpeg -version
ffprobe -version
```

`requirements.txt` trỏ CapCut TTS tới repository Git; cần Git nếu dùng cách cài này.
Không cần activate `.venv` khi gọi trực tiếp interpreter như trên.
VieNeu là lựa chọn bổ sung, không nằm trong dependency mặc định:

```powershell
.\.venv\Scripts\python.exe -m pip install vieneu
```

Chỉ cài các thành phần còn thiếu và đã được người dùng yêu cầu.

## AI xử lý lời đọc

- Codex: đăng nhập bằng ChatGPT có quyền sử dụng; app không dùng API key.
- Antigravity CLI: đăng nhập Google; quyền model/quota thuộc Google.
- Offline: từ điển nội bộ, không OCR, không cần CLI.

Nếu cần cài trên máy mới:

```powershell
npm install -g @openai/codex
codex login
codex login status
```

Cài riêng Antigravity CLI theo [hướng dẫn CLI](../tools/antigravity-cli.md), rồi chạy `agy`
để đăng nhập Google. Không tự thêm API key hoặc đổi phương thức tính phí.

## Chạy app

```powershell
.\.venv\Scripts\python.exe run_studio.py
```

Lần đầu, app tạo media mẫu nếu thiếu; việc này cần FFmpeg và ghi vào `assets/sample_media/`.
Vào Cài Đặt chọn provider/model. Mặc định Codex Luna.
Vào Giọng Đọc chọn voice, rồi dùng kịch bản nhập tay hoặc bài mẫu để thử luồng duyệt.
Offline ở phần AI không ngăn TTS gọi dịch vụ online.

Muốn đọc URL thật, dùng nút Đăng nhập Threads và hoàn tất trình duyệt.
Muốn render, kiểm tra nền video, giọng, thời lượng và thư mục output trước.

## Khi gặp lỗi

- Import lỗi: kiểm tra đang dùng đúng `.venv/Scripts/python.exe`.
- Không có FFmpeg/FFprobe: kiểm tra PATH và mở terminal mới sau cài đặt.
- AI lỗi: kiểm tra đăng nhập, tên model, quyền tài khoản và quota.
- Threads trống: thử đăng nhập, kiểm tra URL và log thu thập.
- Mất hàng đợi sau khi đóng app: queue hiện ở bộ nhớ, chưa có luồng khôi phục.

Xem [cách kiểm tra](validation.md) trước khi nhờ AI sửa lỗi.
