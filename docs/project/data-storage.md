# Dữ liệu và dung lượng

## Trong thư mục dự án

| Đường dẫn | Nội dung |
|---|---|
| `user_data/settings.json` | Cấu hình AI, giọng, worker, layout, media và preset |
| `user_data/database.json` | Kết nối PostgreSQL local; có mật khẩu, bị Git bỏ qua |
| `user_data/threads_edge_profile/` | Profile Edge/cookie Threads riêng của app; profile cũ được giữ nguyên |
| `assets/sample_media/` | Nền, video phụ, nhạc và SFX mẫu |
| `assets/meme-sound/` | Kho sound, JSON mô tả chính và `catalog.json`; `imports/` giữ JSON gốc khi gom kho |
| `output/<job>/` | Kết quả và dữ liệu trung gian từng job |
| `.venv/` | Python và các dependency của dự án |

`output_root` có thể trỏ ra thư mục khác; bảng trên là mặc định.
Không chia sẻ profile đăng nhập hoặc cấu hình riêng khi báo lỗi.

## Trong output của một job

- `content.json`: nội dung sau thu thập.
- `comment-candidates.json`: pool bài/bình luận cùng số lần cuộn, nguồn JSON/DOM
  và phạm vi đã tải; chỉ số có thể `null`, không chứa cookie/profile.
- `translation.json`: mapping lời đọc sau chuẩn hóa.
- `content-reviewed.json`, `translation-reviewed.json`: dữ liệu khi bắt đầu render sau duyệt.
- `cards/`, `styled-cards/`: ảnh thẻ.
- `audio/`: WAV từng đoạn và `master_mix.wav`.
- `narration.wav`: lời đọc ghép theo timeline.
- `video-phu/sub_reel.mp4`: video phụ nếu có.
- `media-cache/`: ảnh/avatar tải từ Threads.
- `selected-media.json`, `v2-layout.json`, `timeline.json`: dữ liệu kiểm tra dựng video.
- `meme-sound-plan.json`: sound và mốc chèn theo `seg_id` khi bật tính năng meme.
- `ai-usage.json`: token từng lượt, provider/model yêu cầu và hạn mức trước/sau;
  không lưu prompt, câu trả lời hoặc dữ liệu xác thực. Xem [báo cáo AI](../modules/ai-usage.md).
- `job-checkpoint.json`: snapshot tiến độ và audio đã hoàn tất để tiếp tục sau khi ngắt;
  thay thế nguyên tử qua file `.tmp`. Không chia sẻ nếu có nội dung riêng tư.
- `<title_slug>.mp4`: video cuối.

`selected-media.json` lưu thêm điểm bắt đầu nền, thời lượng nguồn, cách fit,
tỷ lệ và kích thước đầu ra. Đường dẫn `background` hiện có vẫn giữ nguyên.
Settings/preset giữ đường dẫn file nền, Random Start, tỷ lệ và tiêu chí sort.
Luồng Threads không yêu cầu token dịch vụ lấy bình luận và không dùng profile Edge cá nhân.

Các file trung gian không tự biến mất sau khi có MP4.
Thư mục `clips/` có thể được tạo sẵn; không phải file nào cũng có ở mọi job.

## Dữ liệu ngoài dự án

PostgreSQL local dùng database `postgres`, schema `thread` đã có trên máy:
`settings` giữ cấu hình/preset, `video_jobs` giữ job/path MP4, `segments` giữ lời
gốc/lời đọc và metadata. Không ghi byte video/audio/ảnh vào database.
Snapshot job giữ cả báo cáo AI, kể cả sau khi khởi động lại web.
Web lưu lại job và phục hồi sau khởi động; desktop dự phòng vẫn dùng queue bộ nhớ.
Job đang chạy được tự tiếp tục; dừng tay/lỗi chờ bấm Tiếp tục tạo. Checkpoint local
mới hơn DB được nạp để tránh bỏ mất audio vừa hoàn tất. Xem [core](../modules/core.md).
Metadata từ thư mục output chuẩn được nhập một lần, không ghi đè job đã có.
Xem [module database](../modules/database.md).

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
