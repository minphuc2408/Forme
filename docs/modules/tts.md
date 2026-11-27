# Module tạo giọng

Nguồn: `src/threadstudio/tts/router.py`.

## Trách nhiệm và hợp đồng

`TTSRouter` chọn giọng, tạo âm thanh mỗi đoạn và xây timeline liên tục.
Input là `spoken_text` (hoặc `raw_text` nếu chưa có) cùng voice ID.
Output chuẩn hóa thành WAV PCM 16-bit stereo 44.1 kHz.

## Nguồn giọng

- `capcut:<voice>`: catalog và tổng hợp qua `capcut-tts-api`.
- `edge:<voice>`: Edge-TTS, có các lựa chọn tiếng Việt tích hợp sẵn.
- `vieneu:<preset>`: SDK VieNeu cục bộ hoặc endpoint HTTP `/tts`.
- `vieneu:__clone__`: dùng audio/text tham chiếu nếu đã cấu hình.

Catalog CapCut được lấy động, không dựa vào số voice cố định trong tài liệu.
`available_voices()` vẫn thêm các lựa chọn Edge và preset VieNeu khi tải catalog lỗi.

## Các điểm vào

- `assign_voices`: single, round robin hoặc random; cố tránh lặp giọng ngẫu nhiên liền nhau.
- `synthesize_single`: tạo một đoạn, chuẩn hóa WAV và trả thời lượng.
- `synthesize_segments_parallel`: chạy các đoạn bật, điền đường dẫn/thời lượng/start/end.
- `_normalize_to_wav`: FFmpeg xử lý tốc độ, loudness, sample rate và channels.

## Ràng buộc

- Giữ timeline đúng thứ tự đoạn, dù future hoàn thành không đúng thứ tự.
- Không bỏ qua `enabled` hoặc ghi đè voice ID người dùng chọn hợp lệ.
- Nguồn chọn lỗi có thể fallback CapCut; không gọi đó là hoạt động hoàn toàn offline.
- Giọng clone cần đủ dữ liệu tham chiếu và backend phù hợp.
- Preview và pipeline đều dùng router; kiểm tra cả hai khi sửa hành vi chung.

Chỉ gọi TTS thật khi nhiệm vụ cho phép sử dụng mạng/model và tạo file âm thanh.
