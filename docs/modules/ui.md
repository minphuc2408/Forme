# Module giao diện

Mặc định app mở giao diện **React + Tailwind CSS** trên trình duyệt local.
Xem [web local](web.md) cho frontend, API và cách build.
Các phần Fluent Blue/Qt bên dưới mô tả giao diện dự phòng qua `--desktop`.

Nguồn: `src/threadstudio/ui/main_window.py`, `ui/widgets/stage_canvas.py`.

## Cấu trúc màn hình

`ThreadsStudioWindow` dựng shell gồm sidebar, workspace ở giữa, sân khấu 9:16/16:9
bên phải và log panel phía dưới.

Bảy trang hiện có:

1. Hàng đợi/tạo lô.
2. Inspector duyệt nội dung.
3. Giọng đọc và preview.
4. Nguồn media/preset.
5. Cài đặt tài khoản AI/Threads, model và số worker.
6. Kho Meme → Meme Sound: nhập thư mục, tạo danh mục, nghe thử và giới hạn chèn.
7. Kho Meme → Meme Image: trang giữ chỗ cho tính năng phát triển sau.

Kho sound có module UI riêng tại `ui/meme_library_page.py`;
xem [cách nhập và gom JSON mô tả](meme-library.md).
Quét kho chỉ đọc audio/JSON local, hiển thị số file trùng và mô tả thiếu file;
không có nhập HTML, tải web hoặc gọi AI để đoán mô tả từ tên.

`InteractiveStageCanvas` vẽ preview, xử lý kéo vị trí và wheel để đổi scale,
đồng bộ vào `LayoutConfig` qua signals.

Hàng đợi cho chọn tiêu chí tim/phản hồi/đăng lại/trích dẫn trước khi lấy top N.
Inspector giữ bảng riêng của toàn bộ bình luận đã tải sau 10 lần cuộn trong Edge: bấm bốn cột chỉ số
để sort số tăng/giảm, tìm nội dung và xem từng trang. Chỉ số thiếu hiển thị `—`.
Nút chọn lại top N luôn lấy số lớn nhất theo tiêu chí đã chọn, áp dụng bộ lọc tác giả
của job, thay kịch bản hiện tại và chuẩn hóa lại; không đọc trang lại.
Sắp xếp bảng để xem không tự thay thứ tự đoạn video. Chế độ chỉ tác giả vẫn theo thời gian.
Thông tin phạm vi nguồn nhắc kết quả không phải bảo đảm toàn bộ bình luận bài viết.

Nguồn Video · Nhạc cho nhập/chọn một file nền riêng, bật Random Start,
chọn tỷ lệ đầu ra và cover/contain. File riêng ưu tiên hơn thư mục.
Các lựa chọn được lưu/nạp cùng preset và snapshot media/layout của từng job.
Canvas/snapshot đổi đúng tỷ lệ; sân khấu vẫn dùng hình nền lưới minh họa,
không phát trực tiếp video Minecraft đã chọn. Xem video thực ở tab thành phẩm.

## Các luồng cần theo

- `_collect_live_settings`: đọc điều khiển vào cấu hình.
- `_persist_all_settings`: lưu JSON và cập nhật cấu hình worker.
- `_renormalize_current_job`: chuẩn hóa lại bản sao dữ liệu ở worker.
- `_on_ai_normalized`: nhận mapping qua Qt signal và cập nhật job/UI.
- `_on_ai_provider_changed`: chỉ hiện model/nút đăng nhập đúng provider; Offline ẩn cả hai.
- `_start_ai_login`: trên Windows mở cửa sổ CLI riêng để người dùng đăng nhập.
- `_start_threads_login`: worker mở Edge có giao diện với profile riêng để lưu phiên Threads.

Pipeline phát tín hiệu để UI cập nhật hàng đợi và yêu cầu duyệt.
`_AsyncUiBridge` chuyển kết quả các công việc UI helper về main thread.

## Quy ước khi sửa

- Desktop dùng Fluent Blue và Qt compatibility layer; frontend web dùng React/Tailwind.
- Giữ ngôn ngữ giao diện tiếng Việt và thao tác duyệt ngay trên màn hình.
- Dùng `ThemeManager` cho widget/canvas mới; giữ quy ước trong `DESIGN.md`.
- Không gọi mạng/CLI/TTS/FFmpeg chờ kết quả trực tiếp trên main thread.
- Không báo đăng nhập thành công chỉ vì cửa sổ CLI đã được mở.
- ComboBox model phải cho nhập tên mới, nhưng không hứa mọi tài khoản có mọi model.

Đổi setting cần kiểm tra chọn → thu thập → lưu → nạp lại.
Với thay đổi hình ảnh, kiểm tra trực tiếp bố cục và theme phù hợp phạm vi.
