# PostgreSQL local · Schema thread

Nguồn: `src/threadstudio/core/database.py`, `web_server.py`.

## Kết nối đã cấu hình

- PostgreSQL 17 local, host `127.0.0.1`, port `5432`.
- Database `postgres`, tài khoản `postgres`, schema **`thread`**.
- Schema đã tồn tại trên máy; app chỉ tạo các bảng cần thiết bên trong schema đó.
- Thông tin kết nối nằm ở `user_data/database.json`, bị Git bỏ qua.
- Không đặt mật khẩu vào source React, API state, tài liệu hoặc log.
- Driver Python: `psycopg[binary]>=3.2,<4`, có trong requirements/pyproject.

pgAdmin là công cụ quản lý. Backend Python kết nối trực tiếp PostgreSQL,
không cần mở pgAdmin khi sử dụng app; service PostgreSQL phải chạy.

## Các bảng

| Bảng | Dữ liệu |
|---|---|
| `thread.settings` | Một snapshot cấu hình chung, preset, nguồn media và layout |
| `thread.video_jobs` | ID, URL, tiêu đề, trạng thái, `video_path`, metadata và thời gian |
| `thread.segments` | ID job/đoạn, thứ tự, lời gốc/lời đọc, giọng, bật/tắt và metadata |

Video/audio/ảnh giữ nguyên ở filesystem. Database chỉ lưu đường dẫn và JSON metadata;
không có cột `bytea`, upload binary hoặc PostgreSQL large object.
Giữ `seg_id`, schema JSON và tọa độ phần trăm của model hiện có.
Snapshot JSONB của job giữ provider/model, các lượt token và hạn mức trước/sau.
Không cần bảng mới hoặc migration SQL cho báo cáo AI; số liệu cũ không tự suy ra.

## Lưu và phục hồi

Khi web khởi động, app kiểm tra schema, tạo bảng nếu thiếu, nạp cấu hình DB hoặc
settings JSON mới hơn rồi nạp job đã lưu. Desktop dự phòng vẫn dùng settings JSON.
Lưu cấu hình web ghi PostgreSQL và settings JSON để hai giao diện dùng chung.

Job được ghi trước khi đưa vào xử lý, sau thao tác duyệt/lưu/hủy và checkpoint
khoảng một giây khi có thay đổi. SQL dùng tham số; cả job và các đoạn được cập nhật
trong cùng transaction. Không tự xóa job hoặc dữ liệu ở schema khác.
Các đoạn không còn nằm trong lựa chọn hiện tại được giữ trong bảng; snapshot job
giữ thứ tự/ID đang dùng để phục hồi đúng kịch bản hiện hành.

Khởi động lại phục hồi job và thành phẩm đã lưu. Job đang chạy lúc bị gián đoạn
được tự tiếp tục từ checkpoint; nếu chưa duyệt thì vẫn chờ duyệt trước khi xuất.
Loader nhận `job-checkpoint.json` mới hơn snapshot DB theo `checkpoint_at`, gồm
các WAV vừa hoàn tất trước khi app bị ngắt. JSON local hỏng không thay thế dữ liệu DB.
Job dừng tay/lỗi chỉ chạy tiếp khi bấm **Tiếp tục tạo**, không cần tạo ID job mới.
Snapshot JSONB giữ `checkpoint`, `checkpoint_at`, `resume_on_startup` và hash audio
của từng đoạn; không cần migration SQL. Xem [luồng tiếp tục](core.md).
Bản nháp chưa bấm lưu chỉ ở browser; nhiều tab không chặn ghi đè bản nháp.

Nếu checkpoint mất kết nối, backend giữ snapshot chưa ghi và thử lại; UI Cài đặt
hiện trạng thái kết nối. Lỗi ghi trực tiếp trả lỗi để người dùng biết chưa lưu xong.
Giữ output local; không xóa file để giải quyết lỗi DB.

## Nhập dữ liệu hiện có

- Cấu hình/preset từ `AppSettings` được nhập khi DB chưa có settings.
- Chỉ đọc thư mục output đã cấu hình, theo mẫu `threads-YYYYMMDD-HHMMSS-jobid`.
- Nhập `content-reviewed.json` hoặc `content.json`, lời đọc đã duyệt/chuẩn hóa,
  layout, timeline, thông tin media đã chọn và pool bình luận nếu có.
- File MP4 chỉ được ghi nhận path. Không mở/đọc byte video để nhập database.
- Nhập thêm `ai-usage.json` nếu có; tổng token được tính lại từ các lượt đã ghi.
- Có MP4 thì job hoàn tất; chỉ có kịch bản thì chờ duyệt, không tự render.
- Không ghi đè job đã có cùng ID. Chạy lại không tạo bản ghi trùng.
- Bỏ qua thư mục thiếu metadata hoặc metadata lỗi; báo số lượng, không in nội dung.
- Không đọc profile Edge, cookie, token, lịch sử CLI hoặc schema khác.

## Xem trong pgAdmin

Mở Databases → postgres → Schemas → thread → Tables.
Các truy vấn chỉ đọc hữu ích:

```sql
SELECT job_id, title_slug, stage, video_path
FROM thread.video_jobs ORDER BY created_at DESC;

SELECT job_id, seg_id, position, enabled
FROM thread.segments ORDER BY job_id, position;
```

Trên máy mới, tạo/chọn đúng schema trước rồi tạo file kết nối local với các khóa
`host`, `port`, `dbname`, `user`, `password`, `schema`. Không copy mật khẩu mẫu vào Git.
