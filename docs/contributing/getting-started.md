# Cài đặt và chạy cho người mới

Chạy lệnh từ thư mục gốc chứa `run_studio.py` và `pyproject.toml`.
Ví dụ dùng PowerShell trên Windows; thay đường dẫn theo máy của bạn.

## Yêu cầu

- Python >=3.10; khuyến nghị 3.11 như môi trường hiện tại.
- FFmpeg và FFprobe có trên PATH.
- Node.js >=20 nếu cài Codex CLI qua npm; Antigravity CLI dùng binary riêng.
- Microsoft Edge Stable đã cài nếu đọc URL Threads; Playwright dùng channel `msedge`.
- Internet cho nguồn AI/TTS online và thu thập Threads.

## Môi trường Python

Nếu đã có `.venv`, dùng lại, không tạo đè.
Trên máy mới, chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
ffmpeg -version
ffprobe -version
```

`requirements.txt` trỏ CapCut TTS tới repository Git; cần Git nếu dùng cách cài này.
Không cần activate `.venv` khi gọi trực tiếp interpreter như trên.
Không cần tải Chromium riêng cho luồng Threads. Nếu chưa có Edge, cài Edge trước;
app không tự cài hoặc thay đổi trình duyệt cá nhân.
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

App mở giao diện React + Tailwind tại `http://127.0.0.1:8000`.
Giữ terminal chạy; đóng tab không dừng backend. Bấm **Dừng studio** hoặc Ctrl+C
để dừng. Web có PostgreSQL sẽ phục hồi job đã lưu; tải lại tab không khôi phục bản nháp chưa lưu.
`--port 8001` đổi cổng, `--no-browser` không tự mở tab, `--desktop` mở UI Qt cũ.
Web chỉ lắng nghe loopback; không cần hosting/tên miền và không mở cho mạng LAN.

Nếu thiếu bản build hoặc vừa sửa frontend, dùng Node.js >=22.12:

```powershell
cd web
npm ci
npm run build
cd ..
```

Không cần Node khi chỉ dùng bản frontend đã build. Xem [module web](../modules/web.md).

Máy đã cấu hình PostgreSQL local trong `user_data/database.json`, schema `thread`.
Giữ service PostgreSQL chạy; xem trạng thái trong Cài đặt → Lưu trữ local.
Không chia sẻ file kết nối có mật khẩu. Xem [database](../modules/database.md).

Lần đầu, app tạo media mẫu nếu thiếu; việc này cần FFmpeg và ghi vào `assets/sample_media/`.
Vào Cài Đặt chọn provider/model. Mặc định Codex Luna.
Vào Giọng Đọc chọn voice, rồi dùng kịch bản nhập tay hoặc bài mẫu để thử luồng duyệt.
Offline ở phần AI không ngăn TTS gọi dịch vụ online.

App đọc trực tiếp Threads và cuộn 10 lần; không cần token dịch vụ lấy bình luận.
Nếu trang yêu cầu đăng nhập, dùng nút Đăng nhập Threads để mở Edge của app.
Profile Edge mới tách khỏi profile cũ và Edge cá nhân, nên có thể cần đăng nhập lại.
Muốn render, kiểm tra nền video, giọng, thời lượng và thư mục output trước.

## Khi gặp lỗi

- Import lỗi: kiểm tra đang dùng đúng `.venv/Scripts/python.exe`.
- Không có FFmpeg/FFprobe: kiểm tra PATH và mở terminal mới sau cài đặt.
- AI lỗi: kiểm tra đăng nhập, tên model, quyền tài khoản và quota.
- Threads trống: thử đăng nhập, kiểm tra URL và log thu thập.
- Mất job sau khi đóng app: kiểm tra cấu hình/kết nối PostgreSQL; desktop dự phòng không phục hồi queue.

Xem [cách kiểm tra](validation.md) trước khi nhờ AI sửa lỗi.
