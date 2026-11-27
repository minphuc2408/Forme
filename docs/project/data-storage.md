# Dữ liệu và dung lượng

## Trong thư mục dự án

| Đường dẫn | Nội dung |
|---|---|
| `user_data/settings.json` | Cấu hình AI, giọng, worker, layout, media và preset |
| `user_data/threads_profile/` | Profile Chromium/cookie đăng nhập Threads |
| `assets/sample_media/` | Nền, video phụ, nhạc và SFX mẫu |
| `output/<job>/` | Kết quả và dữ liệu trung gian từng job |
| `.venv/` | Python và các dependency của dự án |

`output_root` có thể trỏ ra thư mục khác; bảng trên là mặc định.
Không chia sẻ profile đăng nhập hoặc cấu hình riêng khi báo lỗi.

## Trong output của một job

- `content.json`: nội dung sau thu thập.
- `translation.json`: mapping lời đọc sau chuẩn hóa.
- `content-reviewed.json`, `translation-reviewed.json`: dữ liệu khi bắt đầu render sau duyệt.
- `cards/`, `styled-cards/`: ảnh thẻ.
- `audio/`: WAV từng đoạn và `master_mix.wav`.
- `narration.wav`: lời đọc ghép theo timeline.
- `video-phu/sub_reel.mp4`: video phụ nếu có.
- `media-cache/`: ảnh/avatar tải từ Threads.
- `selected-media.json`, `v2-layout.json`, `timeline.json`: dữ liệu kiểm tra dựng video.
- `<title_slug>.mp4`: video cuối.

Các file trung gian không tự biến mất sau khi có MP4.
Thư mục `clips/` có thể được tạo sẵn; không phải file nào cũng có ở mọi job.

## Dữ liệu ngoài dự án

- Codex thường dùng `%USERPROFILE%\.codex`; có thể khác khi đặt `CODEX_HOME`.
- Antigravity CLI dùng cấu hình `%USERPROFILE%\.gemini\antigravity-cli/settings.json`;
  lịch sử/cache do CLI quản lý riêng, không cam kết không ghi ổ đĩa.
- Không chép token hoặc lịch sử cá nhân vào repository để hỗ trợ người khác đăng nhập.

## CLI tự động hóa của app

App dùng thư mục tạm riêng cho từng lần chuẩn hóa và dọn thư mục tạm khi kết thúc.
Codex có `--ephemeral` để không lưu session rollout của lần gọi đó.
Điều này không có nghĩa mọi log/cache hoặc dữ liệu trên dịch vụ đều bị tắt.
Antigravity CLI vẫn có thể lưu hội thoại/log ngoài thư mục tạm do CLI quản lý.

## Dọn dung lượng

Ảnh, WAV và video trung gian có thể lớn hơn dữ liệu cấu hình.
Kiểm tra dung lượng theo thư mục trước; chỉ xóa job/media khi người dùng yêu cầu rõ.
Không xóa toàn bộ `.codex`/`.gemini`/profile để chữa lỗi vì có thể mất đăng nhập và lịch sử.
`.gitignore` đã bỏ qua `output/`, `user_data/`, `.venv/`, cache Python và build artifacts.
