# Module AI

Nguồn: `src/threadstudio/ai/text_normalizer.py`.

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
| `codex` | `codex exec`, stdin, kết quả stdout | ChatGPT, bắt buộc `forced_login_method=chatgpt` |
| `antigravity` | `agy`, stream-json qua stdin/stdout; ảnh qua file tạm | Tài khoản Google đã đăng nhập |
| `offline` | `normalize_teencode_offline` | Không cần tài khoản |

`cli_command` tìm executable; trên Windows có fallback Codex trong VS Code và `agy` trong LocalAppData.
Không nối prompt thành câu lệnh shell.
`cli_environment` loại các biến API key liên quan khỏi môi trường con.

## Kiểm soát luồng CLI

- CWD tạm riêng để tránh nạp instruction dự án vào nội dung cần đọc.
- Codex dùng `--ignore-user-config`, `--ephemeral`, sandbox read-only.
- Antigravity chặn lệnh/ghi file/web bằng permission rules; cho phép đọc ảnh trong thư mục tạm.
- Stream phải có result `SUCCESS`; parser kiểm tra cả lỗi trong envelope.
- Timeout 180 giây; nhận UTF-8 và kiểm tra mã thoát.
- Kết quả phải là JSON object có lời đọc chuỗi không rỗng cho mọi `seg_id`.
- Thiếu ID, JSON lỗi, timeout hoặc lỗi provider phải báo rõ; không âm thầm đổi provider.
- Tối đa một ảnh ở mỗi đoạn trong hai đoạn đầu, dưới 3.500.000 byte/ảnh.

## Hai caller bắt buộc kiểm tra

- Pipeline tự động trong `core/pipeline.py`.
- Chuẩn hóa lại trong Inspector của `ui/main_window.py`, chạy ở worker riêng.

## Giới hạn và hướng mở rộng

Luna là mặc định Codex. UI cho chọn gợi ý hoặc nhập model khác theo quyền tài khoản.
Đăng nhập không đảm bảo còn quota hoặc model được hỗ trợ.
Cấu hình cũ chọn `gemini` được chuyển sang `antigravity`; model Gemini CLI cũ không được dùng lại.
Mỗi provider giữ model riêng khi đổi lựa chọn trong UI.

Nếu thêm provider, cần sửa resolver, payload/ảnh, parser, cấu hình, UI và cả hai caller;
không chỉ đổi tên executable. Không gắn provider mới vào luồng API-key fallback.
