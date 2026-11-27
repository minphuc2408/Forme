# Threads Studio Pro

Ứng dụng web local React + Tailwind CSS, backend Python, biến bài viết và bình luận Threads hoặc kịch bản
nhập tay thành video dọc 1080×1920, có lời đọc tiếng Việt, thẻ bình luận,
video phụ, nhạc nền và hiệu ứng âm thanh.

## Bắt đầu

- Người dùng mới: [cài đặt và chạy](docs/contributing/getting-started.md).
- Người sửa code hoặc dùng Codex: đọc [AGENTS.md](AGENTS.md), rồi [mục lục docs](docs/README.md).
- Xem [tính năng và giới hạn](docs/project/features.md), [kiến trúc](docs/project/architecture.md).

## Chạy nhanh trên Windows

Cần Python >=3.10, Microsoft Edge đã cài và FFmpeg/FFprobe trên PATH.
Nếu đã có `.venv`, dùng lại; trên máy mới:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe run_studio.py
```

Lần đầu app tạo media mẫu nếu thiếu. Xem hướng dẫn cài đặt để thiết lập
CLI AI, giọng đọc, Microsoft Edge và VieNeu tùy nhu cầu.

App tự mở `http://127.0.0.1:8000`; giữ terminal chạy khi sử dụng.
Giao diện React đã build nằm trong package Python, không cần Node khi chỉ chạy app.
Khi sửa frontend hoặc chưa có bản build:

```powershell
cd web
npm ci
npm run build
```

Chạy từ gốc bằng `run_studio.py --port 8001` nếu cổng mặc định bận;
`--no-browser` tắt tự mở trình duyệt, `--desktop` mở giao diện Qt cũ.
Xem [giao diện web local](docs/modules/web.md).

Trang chủ dùng bố cục tối với hai khu vực menu riêng. PostgreSQL local lưu cấu hình,
job và kịch bản trong schema `thread`; video chỉ lưu path. File kết nối riêng ở
`user_data/database.json` không đưa vào Git. Xem [database](docs/modules/database.md).

## Luồng sử dụng

1. Nhập URL Threads hoặc kịch bản chia đoạn.
2. Chọn provider/model AI và giọng TTS.
3. Chọn media, bố cục và chế độ chờ duyệt.
4. Xem/sửa lời đọc trong Inspector rồi xuất MP4.

AI chuẩn hóa văn bản và đọc chữ trong ảnh; TTS tạo giọng nói riêng.
Mặc định AI là Codex Luna, đăng nhập ChatGPT; Antigravity CLI dùng tài khoản Google.
Không dùng API key. Có lựa chọn từ điển Offline nhưng lựa chọn này không OCR.
Số voice/model khả dụng phụ thuộc tài khoản và dịch vụ.

Antigravity CLI `agy` đã thay Gemini CLI trong app; model và nút đăng nhập đổi theo provider.
Xem [hướng dẫn chỉ cài CLI](docs/tools/antigravity-cli.md).

## Tìm đúng tài liệu

| Chủ đề | Tài liệu |
|---|---|
| Mục tiêu và cấu trúc | [Tổng quan](docs/project/overview.md) |
| Luồng job và hợp đồng dữ liệu | [Kiến trúc](docs/project/architecture.md) |
| Tính năng, giới hạn, ảnh UI | [Tính năng](docs/project/features.md) |
| Cấu hình, output và dung lượng | [Lưu dữ liệu](docs/project/data-storage.md) |
| Core, AI, scraping, TTS, rendering, UI | [Mục lục module](docs/README.md#module) |
| Người mới dùng Codex | [Quy trình](docs/contributing/codex-workflow.md) |
| Kiểm tra thay đổi | [Validation](docs/contributing/validation.md) |
| Rule mẫu cho dự án khác | [Mẫu AGENTS.md](docs/contributing/agents-template.md) |
| Thiết kế sản phẩm/giao diện | [PRODUCT.md](PRODUCT.md), [DESIGN.md](DESIGN.md) |

## Công nghệ và nguồn

- React + Tailwind CSS, build bằng Vite: giao diện web local.
- aiohttp: API Python và phục vụ frontend trên loopback.
- [Fluent Blue](https://github.com/danieldev23/fluent-blue): UI desktop dự phòng và Qt compatibility.
- [Playwright Python](https://github.com/microsoft/playwright-python): trình duyệt và scraping.
- [CapCut TTS API](https://github.com/K07VN/capcut-tts-api),
  [Edge-TTS](https://github.com/rany2/edge-tts),
  [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS): tạo giọng.
- [TNKRE.DEV](https://tnkre.dev), [Decompile](https://decompile.tnkre.dev): liên kết gốc của dự án.

Giấy phép [MIT](LICENSE). Không đưa cookie, token, profile, `.venv/`,
`user_data/` hoặc output riêng tư vào source được chia sẻ.
