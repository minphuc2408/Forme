# Module dựng hình và video

Nguồn: `src/threadstudio/render/card_renderer.py`, `ffmpeg_compositor.py`.

## Vẽ thẻ

Card renderer dùng QImage/QPainter để vẽ avatar, tên, nội dung gốc,
ảnh đính kèm và thông tin tương tác theo `LayoutConfig`.
`render_cards_for_job` ghi PNG cho các đoạn; không tạo nội dung lời đọc.
Preview canvas tái sử dụng renderer nên thay hình thẻ ảnh hưởng cả preview và output.

## Ghép video

`compose_final_video(job, out_dir, prefer_nvenc)`:

1. Lấy các đoạn bật có nội dung.
2. Ghép narration theo timeline và trộn BGM/SFX.
3. Ưu tiên file nền riêng; nếu trống thì chọn ngẫu nhiên video trong thư mục.
4. Nếu bật video phụ và có nguồn, xây reel B-roll tắt tiếng gốc.
5. Ghi JSON media/layout/timeline rồi gọi FFmpeg tạo MP4.

Nếu bật meme sound, pipeline chọn từ nội dung đã duyệt và dành chỗ sau lời đọc
trước khi compositor trộn sound. Sound cuối video cũng có đủ thời gian;
`meme-sound-plan.json` lưu lựa chọn và thời điểm theo `seg_id`.
Xem [kho meme](meme-library.md).

Kích thước đầu ra 1080×1920 (9:16) hoặc 1920×1080 (16:9) theo `LayoutConfig`.
Vị trí/kích thước layout vẫn dùng phần trăm trên khung đã chọn; preview cùng tỷ lệ.
Tùy cấu hình và khả năng encoder, dùng NVENC hoặc libx264.
Không có đoạn hợp lệ hoặc không có nền video là lỗi cần báo.

## Video Template và Random Start

Trong Nguồn Video · Nhạc, nhập/dán đường dẫn hoặc chọn file Minecraft Parkour
qua hộp chọn video. File riêng được ưu tiên hơn thư mục nền; xóa đường dẫn để
quay lại chọn ngẫu nhiên từ thư mục. Thiết lập trước khi đưa job vào hàng đợi.

Khi bật Random Start, với thời lượng nguồn D và thành phẩm T:

- D > T: chọn điểm bắt đầu ngẫu nhiên trong [0, D − T].
- D ≤ T: bắt đầu từ 0; nền ngắn được lặp đủ thời lượng.
- Tắt Random Start: luôn bắt đầu từ 0.

Đoạn nền liên tục được seek bằng FFmpeg ngay khi ghép; không cắt sẵn clip trung gian.
Cover scale và crop giữa để kín khung; Contain giữ toàn hình và thêm viền đen.
Âm thanh gốc video nền không được trộn vào narration.
File không tồn tại, không có luồng video hoặc không đọc được thời lượng gây lỗi;
không dùng thời lượng giả cho nền. Giữ file nguồn nguyên vẹn.

`selected-media.json` giữ trường `background` cũ và thêm điểm bắt đầu, thời lượng
nguồn, cách fit, tỷ lệ và kích thước đầu ra để kiểm tra lần render đó.
Random Start mặc định tắt cho cấu hình/preset cũ.

## File quan trọng

`narration.wav`, `audio/master_mix.wav`, `video-phu/sub_reel.mp4`,
`selected-media.json`, `v2-layout.json`, `timeline.json`, `<slug>.mp4`.
Xem [lưu dữ liệu](../project/data-storage.md).

## Khi sửa

- Giữ thứ tự/mốc thời gian đoạn và codec/sample format giữa TTS với mixer.
- Kiểm tra che tên, theme thẻ, tỷ lệ chữ, ảnh đính kèm và clipping.
- Kiểm tra cả preview lẫn video khi đổi geometry hoặc cover/contain.
- Truyền args subprocess dạng list; không ghép input người dùng vào shell string.
- Không chạy render nặng để kiểm tra tài liệu hoặc sửa cấu hình nhỏ.

Một video ngắn với dữ liệu giả, audio có sẵn và FFprobe thường đủ để xác minh
một thay đổi compositor; chỉ tạo/chạy khi nhiệm vụ cho phép.
