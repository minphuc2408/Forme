# Kho meme sound

Nguồn: `core/meme_library.py`, `ai/meme_selector.py`, `ui/meme_library_page.py`.

## Cách dùng

1. Vào nhóm **Kho Meme → Meme Sound** trên sidebar.
2. Đặt audio và JSON mô tả trong `assets/meme-sound` (mặc định),
   hoặc nhập đường dẫn kho riêng. Có thể chia thành nhiều thư mục con.
3. Bấm **Nhập / Quét lại kho** để gom các JSON và audio vào một danh mục.
   Ưu tiên khớp đường dẫn, rồi tên file/tên sound; mô tả mơ hồ không tự ghép.
   File không đổi dùng lại thông tin đã xử lý; bước quét không gọi AI.
4. UI báo số sound, file trùng nội dung và mô tả chưa có file tương ứng.
5. Có thể nghe thử, bật/tắt một sound hoặc hiệu chỉnh mô tả khi cần.
6. Bật **AI tự chọn sound sau lời bình luận đã duyệt**, chỉnh âm lượng/giới hạn,
   bấm **Lưu cấu hình**, rồi tạo job mới.

App chỉ dùng kho local: không tải web, nhập HTML, nghe file để nhận dạng
hoặc đoán mô tả từ tên. Thiếu mô tả thì bổ sung JSON hoặc hiệu chỉnh trong UI.

**Meme Image · Sắp có** hiện chỉ là trang giữ chỗ, chưa xử lý ảnh.

## Lưu danh mục

Trong thư mục kho đã chọn:

- `sounds/`: thư mục audio sau khi gom kho.
- `sound_library.json`: JSON mô tả chính, mỗi mục có `id`, `title`,
  `description`, `filename`, `path` tương đối và `source_url` nếu có.
- `imports/`: giữ nguyên JSON nguồn ban đầu; không đọc lại khi quét để tránh lặp.
- `catalog.json`: danh mục dùng trong app, ID theo SHA-256 nội dung, đường dẫn,
  thời lượng, mô tả, trạng thái bật/tắt, chữ ký size/mtime và báo cáo trùng/thiếu.

Importer nhận danh sách bản ghi trong các file `*.json`, kể cả ở thư mục con;
bỏ qua `catalog.json` và `imports/`. Không bắt buộc đặt tên JSON theo số thứ tự.
Đường dẫn trong mỗi JSON tính từ thư mục chứa JSON đó. Tên file là fallback
khi đường dẫn nguồn cũ không đúng; dữ liệu xung đột được đánh dấu cần kiểm tra.

File trùng nội dung chỉ xuất hiện một lần trong danh mục. File bị xóa khỏi
thư mục sẽ biến mất khi quét lại; không xóa file âm thanh từ app.
Tên/ngữ cảnh khác của cùng một sound được gom vào mục chính để AI vẫn đọc được.
Mô tả sửa thủ công và trạng thái bật/tắt được giữ theo ID nội dung, kể cả khi đổi thư mục.
File lỗi hoặc chưa có mô tả chưa được đưa vào danh sách AI lựa chọn.
Mô tả thiếu file được giữ để dùng khi bổ sung MP3, không đưa sound chưa có vào AI.

## Nhóm cảm xúc trên web

Danh mục chia thành nhóm Vui vẻ, Bất ngờ, Ngại ngùng, Mỉa mai, Buồn, Giận dữ,
Đồng cảm và Chưa phân nhóm. Có thể thêm nhóm riêng; app không đoán nhóm từ tên file.
Chọn nhóm trong mỗi sound rồi Lưu sound. Mỗi nhóm có ngữ cảnh dùng chung và
bật/tắt cho AI chọn; tắt nhóm loại mọi sound thuộc nhóm khỏi lượt chọn kế tiếp,
không sửa cờ bật/tắt riêng của từng sound. Kế hoạch đã chọn của job đang dở vẫn được giữ.

`catalog.json` thêm `emotion_groups` (tên → mô tả/bật tắt); mỗi sound có
`emotion_group` tùy chọn. Dữ liệu cũ tự hiện ở Chưa phân nhóm; quét lại vẫn giữ nhóm
theo ID nội dung. Desktop sửa mô tả/cờ riêng vẫn giữ trường nhóm đã lưu từ web.
AI nhận cả mô tả riêng, tên nhóm và ngữ cảnh nhóm; không thay thế mô tả sound bằng nhãn cảm xúc.

## Chọn và chèn sound

- Dùng provider/model Codex hoặc Antigravity hiện đang chọn trong Cài đặt.
  Offline bỏ qua meme; không tự đổi provider hay dùng API key.
- Chọn sau khi duyệt, đọc bài gốc, quan hệ trả lời và thứ tự bình luận.
  Lời đã duyệt là nội dung phát; văn bản gốc giữ tiếng lóng/emoji để hiểu sắc thái.
- Kho tối đa 160 sound sẵn sàng được gửi đủ mô tả trong một lần chọn, tránh
  mất ứng viên chỉ vì không trùng từ khóa. Kho lớn hơn lọc có trọng số xuống 40;
  cách lọc này vẫn có thể bỏ sót từ đồng nghĩa, chưa dùng embedding.
- Đối chiếu ý định/punchline với ngữ cảnh sound: bất ngờ, mỉa mai, phản bác,
  tự trào... Ưu tiên điểm nhấn trong toàn video; chưa chắc hoặc trái sắc thái thì bỏ qua.
- AI trả đủ `seg_id`, mỗi giá trị là ID sound hoặc `null`.
  ID ngoài danh mục/thiếu đoạn gây lỗi rõ; không chọn ngẫu nhiên thay thế.
- Không chèn vào bài gốc, không lặp cùng sound trong một video, giữ giới hạn
  số sound và cho phép bỏ qua toàn bộ khi không phù hợp.
- Sau TTS, tính lại timeline từ thời lượng lời đọc: nghỉ 0,08 giây, phát sound,
  rồi giữ khoảng nghỉ trước bình luận tiếp theo. Giữ thẻ trong lúc phát sound.
- Mixer cắt sound theo giới hạn thời lượng, fade ngắn cuối clip và trộn theo
  âm lượng riêng. BGM/SFX chuyển cảnh hiện có vẫn hoạt động riêng.
- `meme-sound-plan.json` trong output lưu lựa chọn/mốc chèn theo `seg_id`;
  `timeline.json` chứa mốc thời gian đã dành chỗ cho sound.

## Cấu hình và giới hạn

Các trường `meme_sound_*` nằm trong `MediaConfig`, nên được lưu/nạp cùng
settings, preset và snapshot riêng của từng job. Tính năng mặc định tắt để
giữ hành vi cấu hình cũ; mặc định 40% âm lượng, tối đa 3 sound/video,
tối đa 6 giây/sound (có thể chỉnh trên UI).

Quét file, FFprobe và CLI chạy trong worker, kết quả về UI qua Qt signals.
Dữ liệu danh mục được ghi atomically; lỗi nhập không xóa danh mục cũ.
AI chọn từ mô tả đã nhập, không bảo đảm nhận ra mọi meme văn hóa hoặc mỉa mai.
