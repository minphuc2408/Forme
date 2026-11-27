# Model, token và hạn mức AI

Nguồn: `ai/cli_metadata.py`, `ai/usage.py`, `web/src/ai-usage.jsx`.

## Chọn model trên web

Vào AI · Model (`/cau-hinh/ai`), chọn Codex hoặc Antigravity. App đọc danh sách bằng
`model/list` của Codex app-server hoặc `agy models`, không dùng danh sách cố định.
Chọn model có sẵn hoặc **Nhập tên model khác…**, rồi bấm **Lưu cấu hình**.
Mỗi provider giữ model riêng. Job mới chụp provider/model lúc tạo;
đổi cấu hình trong khi job chờ duyệt không đổi model của job đó.
Job cũ chưa có snapshot dùng cấu hình hiện hành khi bắt đầu chuẩn hóa.
Chuẩn hóa lại thủ công trong Inspector dùng provider/model đang cấu hình
và ghi riêng model yêu cầu của lượt đó.

Danh sách phản ánh CLI đang cài và tài khoản đang đăng nhập; chọn tên không
cấp quyền truy cập model hoặc tăng quota. Đọc metadata không gửi lượt sinh nội dung.

## Báo cáo mỗi video

Panel phải dưới sân khấu có **AI · Token và hạn mức** của job đang chọn;
có thể thu gọn và đổi chiều cao phần sân khấu. Hàng đợi cũng hiển thị tổng token vào/ra.

- Token vào, token ra, cache đọc và suy luận lấy từ kết quả CLI.
- Từng lượt ghi công việc, provider/model yêu cầu, số ảnh gửi OCR, thời gian và kết quả.
- Bao gồm chuẩn hóa lời đọc, chuẩn hóa lại và chọn meme sound sau duyệt nếu bật.
- Lượt lỗi vẫn được ghi; chỉ cộng số token nếu CLI đã trả số liệu.
- Dấu `—` là chưa biết; không ước tính token từ số chữ hoặc biến thiếu thành 0.
- Offline dùng từ điển: 0 token, không gọi model; TTS/FFmpeg không tính vào báo cáo này.

Codex dùng sự kiện `turn.completed.usage` của `exec --json`; tổng token vào đã
bao gồm phần cache đọc, không cộng cache thêm lần nữa. Antigravity lấy usage
trong result cuối để tránh cộng lặp các sự kiện cập nhật trung gian.
Nếu có lượt không trả usage, tổng chỉ phản ánh các lượt có số liệu;
UI cho biết bao nhiêu lượt có đủ token vào/ra. Không truy hồi số token của job cũ.

## Hạn mức trước và sau

Mỗi provider được ghi nhận trước lần xử lý AI đầu tiên của job. Khi job kết thúc
thành công hoặc lỗi, app đọc lại hạn mức. Trong lúc chờ duyệt, mốc sau còn trống;
nếu tiếp tục xử lý, mốc sau được cập nhật khi lượt kết thúc tiếp theo hoàn tất.
Mỗi mốc có thời gian ghi nhận, phần trăm đã dùng/còn lại và thời gian reset theo giờ Việt Nam.

Codex đọc `account/rateLimits/read` qua app-server; hiển thị cửa sổ 5 giờ khi CLI
trả `windowDurationMins = 300`, cùng cửa sổ tuần hoặc bucket khác nếu được cung cấp.
Đây là hạn mức tài khoản, không phải ngân sách token cố định của riêng video.
Các tác vụ khác và việc reset trong lúc dựng có thể ảnh hưởng chênh lệch trước/sau;
app không tự quy đổi phần trăm thành số token còn lại.

Antigravity CLI đang cài chưa cung cấp lệnh headless đọc hạn mức tương ứng.
App vẫn ghi token vào/ra thực tế; phần hạn mức ghi rõ chưa đọc được tự động.
Trong AI · Model có nút **Mở CLI xem /usage** để xem hạn mức bằng giao diện CLI.
Nếu đọc metadata lỗi hoặc tài khoản chưa đăng nhập, báo cáo ghi rõ thiếu dữ liệu,
không chặn xử lý video chỉ vì không đọc được hạn mức.

## Lưu trữ

`VideoJob.ai_usage` được lưu trong snapshot JSONB của `thread.video_jobs` và
`ai-usage.json` trong thư mục output job. Khởi động lại web vẫn xem được số liệu.
Importer output đọc báo cáo này nếu có; dữ liệu lịch sử thiếu báo cáo giữ trống.
Không tạo bảng SQL riêng, không lưu prompt/câu trả lời/token đăng nhập/cookie.
Lỗi ghi file báo cáo được log cảnh báo; metadata trong bộ nhớ vẫn được giữ.

Tài liệu giao thức: [Codex app-server](https://developers.openai.com/codex/app-server/),
[Codex JSONL](https://developers.openai.com/codex/noninteractive/),
[Antigravity headless](https://antigravity.google/docs/cli/headless/),
[Antigravity /usage](https://antigravity.google/docs/cli/commands/usage/).
