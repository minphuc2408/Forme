# Module thu thập nội dung

Nguồn: `src/threadstudio/scrapers/threads_scraper.py`.

## Hai đầu vào

- `scrape_threads_url`: URL → `(title_slug, list[SegmentItem])`.
- `parse_manual_script`: văn bản nhập tay → cùng định dạng kết quả.

Pipeline gọi một trong hai tùy `VideoJob.manual_script`.

## Threads

1. Playwright mở Microsoft Edge (`channel="msedge"`) đã cài trên máy.
2. Dùng profile riêng đã lưu nếu có, hoặc context mới khi chưa đăng nhập.
3. Mở bài và cuộn **10 lần**, mỗi lần chờ 900 ms; hủy được kiểm tra giữa các lần cuộn.
4. Thu JSON phản hồi GraphQL/API và JSON nhúng trong trang; fallback đọc DOM.
5. Đối chiếu shortcode với URL canonical, xác định bài gốc rồi lọc nhánh trả lời.

Không dùng dịch vụ trung gian hay token thu thập. URL chỉ chấp nhận HTTPS của
Threads; bỏ query/fragment và không chấp nhận user/password trong URL.

## Đăng nhập Edge

`open_threads_login_session` mở Edge trực tiếp bằng subprocess với profile riêng
`user_data/threads_edge_profile/`; bước đăng nhập không dùng Playwright, remote
debugging, cờ automation hay `--no-sandbox`. Người dùng tự đăng nhập trên trang.
Đăng nhập rồi đóng tất cả cửa sổ Edge của app để kết thúc bước này và lưu phiên.
App chờ Edge đóng, không tự đóng cửa sổ khi người dùng đang xác minh.
Web hiển thị trạng thái chờ và khóa nút mở Edge lần nữa trong lúc tác vụ còn chạy.
Sau khi Edge đóng, có nút về dựng video; đăng nhập không tự thu thập/tạo video.
Trạng thái hồ sơ local chỉ dựa trên thư mục `Default` có tồn tại, không đọc cookie,
token hoặc nội dung profile. Không dùng sự tồn tại của thư mục để báo đã đăng nhập.
Thông báo đóng/lưu profile không chứng minh
đăng nhập thành công; trang có thể vẫn yêu cầu xác minh khi đọc bài.

Profile này tách khỏi `threads_profile/` cũ và Edge cá nhân; không chép cookie
hoặc tự di chuyển dữ liệu đăng nhập. Có thể cần đăng nhập lại một lần.
Đăng nhập/thu thập mở tuần tự vì Edge không cho hai browser dùng cùng profile.
Không tự cài Edge hoặc âm thầm chuyển sang Chrome/Chromium khi Edge lỗi.
Hai luồng thu thập bằng Playwright bật `chromium_sandbox=True`, không dùng `--no-sandbox`.
Cảnh báo cờ trình duyệt và thông báo từ chối đăng nhập Instagram là hai vấn đề
khác nhau; bật sandbox không chứng minh đăng nhập đã được chấp nhận.

## Xếp hạng và giới hạn

Khử trùng theo ID và theo quan hệ cha/con của bài gốc; loại bài liên quan.
Giữ riêng tim, phản hồi,
đăng lại và trích dẫn; chỉ số không được trả về là `null`, UI/thẻ hiện `—`.
Không suy ra số lượt lưu hoặc chia sẻ từ repost/quote.
Lọc spam rồi sort trên toàn bộ tập đã tải, sau đó mới lấy `max_comments` cho AI/TTS.
Chỉ tải avatar/ảnh của các đoạn đã chọn.

Ba chế độ bình luận nằm trong `CommentMode`:
tác giả; không gồm tác giả; có gồm tác giả. Hai giá trị `top_likes_*` cũ được giữ
để tương thích cấu hình; `comment_sort` chọn tim/phản hồi/đăng lại/trích dẫn.
Chỉ tác giả giữ thứ tự thời gian để kể chuyện.

Chỉ xếp hạng tập bình luận Threads đã tải sau 10 lần cuộn; đăng nhập không bảo đảm
mở mọi nhánh hay có top toàn bài. DOM có thể chỉ hiển thị số làm tròn như `1,5K`;
số thiếu vẫn là `null`, không gán bằng 0. Fallback giữ quan hệ cha chưa biết là trống.
`comment-candidates.json` lưu pool và coverage: `source`, `browser`, `extraction`,
`scroll_count`, `fetched`, `scope`. Không lưu phản hồi mạng thô, cookie hay token.
Context/browser luôn đóng khi hoàn tất, lỗi hoặc hủy; không sửa profile cá nhân.

Inspector có bảng bốn chỉ số và nút chọn lại top N từ pool đã tải.
Chọn lại không mở trang/cuộn mới, nhưng thay kịch bản đang sửa và chạy lại chuẩn hóa.

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
