# Web local · React + Tailwind CSS

## Thành phần

- `web/src/main.jsx`: shell React, hàng đợi, Inspector, giọng, media, cài đặt,
  kho meme và sân khấu kéo thả/phím mũi tên.
- `web/src/fields.jsx`: field cấu hình và ràng buộc nhập liệu theo model hiện có.
- `web/src/ai-usage.jsx`: danh sách model, token từng lượt và hạn mức trước/sau.
- `web/src/workspace.jsx`: route History API, localStorage, resize và thẻ kéo thả.
- `web/src/studio.css`: Tailwind CSS và token sáng/tối/high-contrast.
- `web/vite.config.js`: build vào `src/threadstudio/ui/web/`.
- `src/threadstudio/web_server.py`: aiohttp phục vụ frontend và API cùng origin.
- `app.py`: mặc định chạy web; `--desktop` giữ giao diện Fluent Blue cũ.

Backend giữ `BatchPipelineManager`, scraper, AI CLI, TTS, kho meme và FFmpeg.
Qt vẫn cần cho pipeline và QImage/QPainter; không có cửa sổ desktop khi chạy web.
Không có server Node khi chạy bản build.

## Trang chủ và menu

Trang chủ theo mẫu, hỗ trợ sáng/tối: tiêu đề **Dựng video mới**, ô Link bài viết/Tự viết,
Cấu hình, Sản phẩm và Tạo video. Không có thanh điểm/query/tin nhắn/thông báo,
tài khoản/login/logout, preset Mặc định hoặc grid Bài hot trong kho nguồn.
Hàng đợi và sân khấu ở trang công cụ. Nhật ký là dock dưới có thể mở/đóng, kéo đổi cao.

Sidebar tách hai khu vực: menu tham khảo (Thư viện/Sáng tạo)
và **Công cụ của bạn** (các menu studio hiện có). Video đã tạo xem MP4 từ path
đã lưu; Cấu hình video/Cài đặt mở các công cụ cấu hình tương ứng.
Kho tài nguyên hiển thị nguồn local; Công cụ dẫn tới các chức năng đã có.
Đã bỏ menu/trang Tiếp thị liên kết, Tiện ích trình duyệt, Gói dịch vụ và Hộp thư hỗ trợ.
Trang Hướng dẫn được thay bằng thanh các bước và nút chuyển tiếp ngay trong công việc.

## Route và luồng tạo video

| Route | Công việc |
|---|---|
| `/tao-video` | Nhập link/kịch bản, tùy chọn duyệt và che tên tài khoản |
| `/cau-hinh/giong-doc` | Giọng, tốc độ, TTS và clone |
| `/cau-hinh/nguon` | Đường dẫn video/nhạc/đầu ra, cách dùng media và preset |
| `/cau-hinh/bo-cuc` | Bố cục mặc định, tỷ lệ và theme thẻ |
| `/cau-hinh/ai` | Provider/model và đăng nhập AI |
| `/hang-doi` | Thu thập, xử lý và tiến độ |
| `/kich-ban/{job_id}` | Duyệt, sửa và sắp xếp thẻ |
| `/video` | Thành phẩm |
| `/cau-hinh/he-thong` | PostgreSQL, đăng nhập Threads, worker, NVENC và dừng backend |
| `/kho-sound`, `/kho-anh`, `/tai-nguyen`, `/cong-cu` | Kho và công cụ hiện có |

Nút tiếp tục dẫn từ Nội dung → Giọng → Nguồn → Bố cục → AI → Xử lý → Duyệt → Thành phẩm.
Cấu hình được lưu khi bấm tiếp tục. Trong luồng này, job sẵn sàng duyệt/hoàn tất
tự chuyển tới bước tương ứng; không tự duyệt nội dung thay người dùng.
History API hỗ trợ Back/Forward; backend phục vụ URL sâu theo whitelist, không fallback API lỗi.

localStorage giữ route, job/đoạn đang chọn, theme, trạng thái log, độ rộng sidebar,
panel phải/danh sách thẻ và chiều cao sân khấu/log. Không lưu token hoặc bản nháp lời đọc.
Mở `/` phục hồi route gần nhất; mở URL cụ thể ưu tiên URL. Bản nháp chưa lưu vẫn chỉ ở tab.
Mặc định sáng, nút sáng/tối ở góc phải navbar; màu video xem trước độc lập theme app.

Inspector dùng thẻ kéo chuột để sắp xếp, hoặc Alt + phím lên/xuống; giữ `seg_id`.
Bấm Lưu kịch bản để ghi thứ tự; không cho đổi lúc job đang chạy. Bảng bình luận
vẫn phân trang/sort/top N, đã bỏ tìm tài khoản/nội dung. Các cột của bảng không đổi thứ tự video.
Sidebar, danh sách thẻ và panel phải có tay kéo đổi rộng; sân khấu và log đổi cao.
Tay kéo hỗ trợ phím mũi tên. Màn hình nhỏ xếp panel phải xuống dưới.
Token AI nằm dưới sân khấu bên phải, theo job đang chọn và cập nhật cùng tiến độ.

## Chạy và phát triển

Từ gốc: `.\.venv\Scripts\python.exe run_studio.py`.
App tự mở `http://127.0.0.1:8000`.
`--port 8001` đổi cổng, `--no-browser` không mở tab tự động.

Khi sửa frontend, dùng Node >=22.12; từ thư mục `web/`:

```powershell
npm ci
npm run build
```

`npm run dev` build lại khi source đổi; vẫn xem qua server Python và tải lại tab.
Bản build được đóng gói cùng package Python qua `tool.setuptools.package-data`.

## API và trạng thái

- `GET /api/state`: cấu hình, danh sách giọng, tóm tắt job/task và 300 dòng log gần nhất.
- `GET /api/jobs/{job_id}`: các đoạn, layout, pool và phạm vi bình luận.
- `POST /api/action`: tạo lô, lưu cấu hình/job, duyệt, hủy, chuẩn hóa lại, chọn lại
  bình luận, nghe thử, login, đọc/quét/sửa kho sound và lưu preset.
  Có action đọc model/hạn mức trong worker và mở CLI Antigravity xem `/usage`.
- `POST /api/card`: PNG từ chính renderer Qt dùng khi xuất video.
- `GET /media/{file_id}`: audio/video đã được backend đăng ký bằng ID tạm.

React polling trạng thái khoảng 1,1 giây. Không tự ghi đè bản nháp đang sửa.
Lời đọc/nội dung gốc, bật/tắt, giọng và thứ tự đoạn được lưu cùng layout của job.
Chỉ job chờ duyệt/đã lỗi mới chỉnh sửa; chuẩn hóa đang chạy sẽ khóa chỉnh sửa.
Số worker không đổi trong lúc có job đang xử lý để giữ giới hạn semaphore.
Các thao tác nặng chạy trong worker; không gọi AI/TTS/FFmpeg trong callback UI.

Nhập đường dẫn local cho nguồn video/audio/thư mục; browser không đọc file tùy ý.
Nghe thử, chọn giọng và login vẫn qua Python, dùng các provider/tài khoản cũ.
Danh sách giọng đầy đủ tải khi bấm nút; ID đã lưu vẫn được giữ trước khi tải.
Trong AI · Model, model tải từ CLI một lần mỗi provider khi mở trang;
nút tải lại đọc mới cả model và hạn mức. Vẫn có mục nhập ID model khác.
Bấm Lưu cấu hình để áp dụng cho job mới; lựa chọn không cấp thêm quyền/quota.
Panel phải có **AI · Token và hạn mức**, có thể thu gọn; hàng đợi hiện
tổng token vào/ra. Xem [báo cáo AI](ai-usage.md) cho nguồn số liệu và giới hạn.

Trong Cài đặt có phần **Threads · Phiên đăng nhập**: chờ hoàn tất/đóng Edge,
hồ sơ local đã có và nút về dựng video. Nút mở Edge bị khóa khi đang chờ;
thông báo hướng dẫn không tự ẩn trong lúc bước đăng nhập chưa kết thúc.
Tải lại tab vẫn nhận trạng thái tác vụ từ backend. Sau khởi động lại, app chỉ
báo hồ sơ có tồn tại, không tự suy ra tài khoản đã đăng nhập hoặc đọc cookie.
Phiên do Edge lưu trong profile riêng trên máy, không đưa vào PostgreSQL.

## Phạm vi local và giới hạn

Server chỉ bind `127.0.0.1`; kiểm tra Host/Origin và mã phiên cho POST.
Không mở CORS hoặc phục vụ toàn bộ thư mục dự án/output/profile.
Media dùng ID do backend cấp; frontend không gọi endpoint đọc đường dẫn tùy ý.
Không đọc nội dung device JSON, token/cookie/profile để đưa lên UI.
Build không dùng CDN hoặc font ngoài; Threads/AI/TTS online vẫn cần mạng như cũ.

Đóng tab không dừng Python. Trong Cài đặt, bấm **Dừng studio**, hoặc dùng Ctrl+C.
Backend đánh dấu hủy và chờ worker kết thúc; có thể phải đóng cửa sổ Edge login.
Khi có cấu hình PostgreSQL, metadata job được lưu định kỳ và phục hồi khi mở app.
Job đang chạy khi backend bị ngắt sẽ tự tiếp tục từ bước chưa xong; job chờ duyệt
vẫn chờ duyệt. Dừng backend giữ cờ tự tiếp tục, không đổi job chờ duyệt sang Đã dừng.
Bấm Dừng/Dừng lô để dừng tay; job dừng tay/lỗi có nút **Tiếp tục tạo** ở hàng đợi
và Inspector. Nút bị khóa đến khi worker cũ dừng hẳn để tránh tạo trùng.
Action `resume` tiếp tục cùng job ID, giữ lời đã duyệt và dùng lại WAV còn phù hợp;
không nhận thêm bản nháp chưa lưu. Xem [checkpoint và audio](core.md).
Bản nháp chưa lưu chỉ ở tab hiện tại; browser cảnh báo khi đóng.
Nhiều tab xem chung hàng đợi/cấu hình nhưng không cộng tác đồng bộ bản nháp.

Sân khấu giữ tọa độ phần trăm, tỷ lệ 9:16/16:9 và kích thước thẻ theo model.
Nền trơn/video phụ là minh họa. Ảnh bố cục tải bằng browser; video thực xem ở
Thành phẩm. Meme Image vẫn là trang giữ chỗ.

Xem [PostgreSQL local](database.md) cho kết nối, bảng và nhập metadata cũ.

## Xác minh phù hợp

Build bằng `npm run build`; parse/import backend Python.
Kiểm tra local bằng kịch bản nhập tay và AI Offline để không tiêu quota.
Kiểm tra tạo lô → chờ duyệt → sửa/lưu/thứ tự đoạn/bố cục và POST không hợp lệ.
TTS/AI/login thật và render video cần kiểm tra riêng với tài khoản/media được phép.
Không đánh đồng UI/HTTP hoạt động với việc provider online đã được xác minh.
