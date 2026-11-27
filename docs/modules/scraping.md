# Module thu thập nội dung

Nguồn: `src/threadstudio/scrapers/threads_scraper.py`.

## Hai đầu vào

- `scrape_threads_url`: URL → `(title_slug, list[SegmentItem])`.
- `parse_manual_script`: văn bản nhập tay → cùng định dạng kết quả.

Pipeline gọi một trong hai tùy `VideoJob.manual_script`.

## Threads

`open_threads_login_session` mở Chromium có giao diện, lưu profile do caller cung cấp.
Người dùng đăng nhập rồi đóng cửa sổ để kết thúc luồng lưu phiên.
Khi scraping, code dùng profile tồn tại hoặc browser context mới.
Thu thập response GraphQL/API và JSON nhúng trong HTML; có DOM fallback.
Sau đó chọn bình luận, lọc spam, tải avatar/ảnh và tạo ID đoạn có thứ tự.

Ba chế độ bình luận nằm trong `CommentMode`:
tác giả; lượt thích không gồm tác giả; lượt thích có gồm tác giả.
Không coi dữ liệu trang đầu hoặc số lượt cuộn cố định là toàn bộ bình luận.

## Kịch bản nhập tay

Chia đoạn bằng dòng trống hoặc dòng `---`.
Hỗ trợ `@username: nội dung` và `username | số_lượt_thích: nội dung`.
Đoạn đầu là `root`; các đoạn tiếp theo là `cmt_01`, `cmt_02`, ...
Input trống gây lỗi, không tạo một job giả thành công.

## Khi sửa

- Giữ format kết quả để pipeline không phải đoán loại nguồn.
- Tách lỗi tải trang, lỗi parse và không có dữ liệu khi điều tra.
- Không đưa cookie/profile thật vào fixture hay tài liệu.
- Khi cần thay selector, kiểm tra JSON và DOM fallback đều còn hợp lý.
- Live scraping phụ thuộc mạng/tài khoản và phải nằm trong phạm vi được phép.

Kiểm tra parser bằng dữ liệu giả trước khi cần dùng tài khoản Threads thật.
