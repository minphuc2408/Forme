# Kiểm tra thay đổi

Dự án chưa cấu hình lệnh test/lint mặc định trong `pyproject.toml`.
Không ghi đã chạy `pytest`, lint hoặc CI nếu không có và chưa chạy thật.
Theo yêu cầu chủ dự án, không tạo file test hoặc chạy Java khi chưa được yêu cầu.

## Chọn kiểm tra theo thay đổi

| Thay đổi | Kiểm tra phù hợp |
|---|---|
| Tài liệu/rule | Link nội bộ, đường dẫn code, số dòng, thông tin có đúng code |
| Python | Parse cú pháp các file đã sửa, kiểm tra caller và input/output liên quan |
| Config/model | Giá trị mặc định, nạp dữ liệu cũ, serialization, UI đọc/ghi |
| AI CLI | Model, OAuth, env API key, ảnh, stdout/JSON, timeout và lỗi provider |
| UI | Khởi tạo, signals, không block main thread, chọn/lưu/nạp setting |
| TTS | Giọng, format WAV, thời lượng và timeline |
| Render/layout | Preview và video ngắn; codec/kích thước/audio qua FFprobe |

Không chạy những hàng không liên quan chỉ để tăng số kiểm tra.

## Kiểm tra Python không tạo bytecode

Ví dụ chỉ kiểm tra cú pháp một file, không import module hoặc gọi dịch vụ:

```powershell
.\.venv\Scripts\python.exe -B -c "import ast,pathlib; p=pathlib.Path('src/threadstudio/ai/text_normalizer.py'); ast.parse(p.read_text(encoding='utf-8')); print('Syntax OK')"
```

Thay đường dẫn bằng file thực sự đã sửa.
Không dùng chạy app như một kiểm tra “chỉ đọc”: app có thể tạo media/cấu hình.

## UI

Có thể dùng `QT_QPA_PLATFORM=offscreen` để kiểm tra khởi tạo ở môi trường không màn hình.
Lúc tạo cửa sổ, catalog voice và kiểm tra NVENC có thể chạm mạng/subprocess;
nếu chỉ kiểm tra logic UI, cần stub các phần đó thay vì dùng tài khoản thật.
Offscreen không xác minh chất lượng hiển thị, thao tác chuột hoặc âm thanh.

## AI CLI

Đọc đủ hai caller: pipeline lô và chuẩn hóa lại trong Inspector.
Kiểm tra bằng dữ liệu giả/mocks khi có thể, không để key thật xuất hiện trong log.
Live call tiêu quota, cần mạng và phiên đăng nhập; chỉ làm trong phạm vi nhiệm vụ được phép.
Không đánh dấu provider hoạt động chỉ vì `--version` hoặc `login status` thành công.
Ghi riêng: cài CLI, đăng nhập, gửi văn bản, gửi ảnh, parse kết quả.

## Kiểm tra media

Khi được phép render mẫu, dùng nội dung ngắn và output riêng dễ nhận diện.
FFprobe một file được chỉ định:

```powershell
ffprobe -v error -show_streams -show_format -of json "DUONG_DAN_VIDEO.mp4"
```

Không xóa output/profile/cache để “làm sạch” trước hoặc sau kiểm tra khi chưa được yêu cầu.

## Cách báo kết quả

Nêu thay đổi → kiểm tra đã chạy → kết quả → hạn chế.
Phân biệt đọc code, parse cú pháp, mô phỏng và chạy dịch vụ thật.
Ghi rõ khi bị giới hạn môi trường hoặc dịch vụ ngoài dự án.
