# Module AI

Nguồn: `src/threadstudio/ai/text_normalizer.py`.

`call_cli_json` dùng chung lớp gọi CLI cho chuẩn hóa và `ai/meme_selector.py`.
Meme selector đọc bài gốc, quan hệ trả lời, lời bình luận đã duyệt và mô tả JSON
để chọn sound sau duyệt; không chọn chỉ vì trùng từ khóa. Khi không phù hợp, trả `null`;
không thay đổi `raw_text`/`spoken_text`, không nghe file âm thanh.
Xem [kho meme](meme-library.md). Chuẩn hóa và chọn meme kiểm tra JSON riêng theo schema.

## Đầu vào và đầu ra

`normalize_segments_batch(segments, ai_provider, ai_model, include_emotion_cues)`
trả `dict[str, str]` theo `seg_id` và cập nhật `SegmentItem.spoken_text`.
Giữ nguyên `raw_text` để thẻ vẫn hiển thị nội dung gốc.

## Công việc

- Mở rộng teencode/viết tắt và làm lời đọc tiếng Việt tự nhiên hơn.
- Giữ giọng điệu, không bịa thêm ý.
- Bỏ ký hiệu mặt cười hoặc thêm cue cảm xúc khi phù hợp cấu hình VieNeu.
- Đọc nội dung chữ quan trọng trong ảnh chat/meme được gửi.

## Provider hiện có

| Provider | Cách gọi | Xác thực |
|---|---|---|
| `codex` | `codex exec --json`, stdin, sự kiện JSONL | ChatGPT, bắt buộc `forced_login_method=chatgpt` |
| `antigravity` | `agy`, stream-json qua stdin/stdout; ảnh qua file tạm | Tài khoản Google đã đăng nhập |
| `offline` | `normalize_teencode_offline` | Không cần tài khoản |

`cli_command` tìm executable; trên Windows có fallback Codex trong VS Code và `agy` trong LocalAppData.
Không nối prompt thành câu lệnh shell.
`cli_environment` loại các biến API key liên quan khỏi môi trường con.

## Kiểm soát luồng CLI

- CWD tạm riêng để tránh nạp instruction dự án vào nội dung cần đọc.
- Codex dùng `--ignore-user-config`, `--ephemeral`, sandbox read-only.
- Antigravity chặn lệnh/ghi file/web bằng permission rules; cho phép đọc ảnh trong thư mục tạm.
- Codex lấy JSON trả lời từ `agent_message` cuối; lỗi trong sự kiện không được bỏ qua.
- Antigravity stream phải có result `SUCCESS`; parser kiểm tra cả lỗi trong envelope.
- Timeout 180 giây; nhận UTF-8 và kiểm tra mã thoát.
- Kết quả phải là JSON object có lời đọc chuỗi không rỗng cho mọi `seg_id`.
- Thiếu ID, JSON lỗi, timeout hoặc lỗi provider phải báo rõ; không âm thầm đổi provider.
- Tối đa một ảnh ở mỗi đoạn trong hai đoạn đầu, dưới 3.500.000 byte/ảnh.

## Hai caller bắt buộc kiểm tra

- Pipeline tự động trong `core/pipeline.py`.
- Chuẩn hóa lại trong Inspector của `ui/main_window.py`, chạy ở worker riêng.
- Web Inspector trong `web_server.py`, chạy qua worker bất đồng bộ.

`usage.py` ghi token CLI theo job/công việc, kể cả lượt lỗi nếu CLI trả số liệu.
`cli_metadata.py` đọc danh sách model và hạn mức bằng giao thức CLI chính thức,
không mở lịch sử hoặc file đăng nhập. Xem [token và hạn mức](ai-usage.md).

## Giới hạn và hướng mở rộng

Luna là mặc định Codex. UI cho chọn gợi ý hoặc nhập model khác theo quyền tài khoản.
Đăng nhập không đảm bảo còn quota hoặc model được hỗ trợ.
Cấu hình cũ chọn `gemini` được chuyển sang `antigravity`; model Gemini CLI cũ không được dùng lại.
Mỗi provider giữ model riêng khi đổi lựa chọn trong UI. Web tải model từ CLI,
vẫn cho nhập ID khác; provider/model được snapshot khi tạo job.

Nếu thêm provider, cần sửa resolver, payload/ảnh, parser, cấu hình, UI và cả hai caller;
không chỉ đổi tên executable. Không gắn provider mới vào luồng API-key fallback.
