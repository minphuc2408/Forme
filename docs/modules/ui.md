# Module giao diện

Nguồn: `src/threadstudio/ui/main_window.py`, `ui/widgets/stage_canvas.py`.

## Cấu trúc màn hình

`ThreadsStudioWindow` dựng shell gồm sidebar, workspace ở giữa, sân khấu 9:16
bên phải và log panel phía dưới.

Năm trang hiện có:

1. Hàng đợi/tạo lô.
2. Inspector duyệt nội dung.
3. Giọng đọc và preview.
4. Nguồn media/preset.
5. Cài đặt tài khoản AI/Threads, model và số worker.

`InteractiveStageCanvas` vẽ preview, xử lý kéo vị trí và wheel để đổi scale,
đồng bộ vào `LayoutConfig` qua signals.

## Các luồng cần theo

- `_collect_live_settings`: đọc điều khiển vào cấu hình.
- `_persist_all_settings`: lưu JSON và cập nhật cấu hình worker.
- `_renormalize_current_job`: chuẩn hóa lại bản sao dữ liệu ở worker.
- `_on_ai_normalized`: nhận mapping qua Qt signal và cập nhật job/UI.
- `_on_ai_provider_changed`: chỉ hiện model/nút đăng nhập đúng provider; Offline ẩn cả hai.
- `_start_ai_login`: trên Windows mở cửa sổ CLI riêng để người dùng đăng nhập.
- `_start_threads_login`: worker mở Chromium có giao diện để lưu phiên Threads.

Pipeline phát tín hiệu để UI cập nhật hàng đợi và yêu cầu duyệt.
`_AsyncUiBridge` chuyển kết quả các công việc UI helper về main thread.

## Quy ước khi sửa

- Dùng Fluent Blue và Qt compatibility layer hiện có; không thêm hệ UI khác.
- Giữ ngôn ngữ giao diện tiếng Việt và thao tác duyệt ngay trên màn hình.
- Dùng `ThemeManager` cho widget/canvas mới; giữ quy ước trong `DESIGN.md`.
- Không gọi mạng/CLI/TTS/FFmpeg chờ kết quả trực tiếp trên main thread.
- Không báo đăng nhập thành công chỉ vì cửa sổ CLI đã được mở.
- ComboBox model phải cho nhập tên mới, nhưng không hứa mọi tài khoản có mọi model.

Đổi setting cần kiểm tra chọn → thu thập → lưu → nạp lại.
Với thay đổi hình ảnh, kiểm tra trực tiếp bố cục và theme phù hợp phạm vi.
