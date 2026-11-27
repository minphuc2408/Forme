# Module core

Nguồn: `src/threadstudio/core/`.

## Trách nhiệm

- `models.py`: enum và dataclass dùng chung.
- `config.py`: cấu hình bền vững và các preset mặc định.
- `pipeline.py`: điều phối vòng đời job và các tầng xử lý.
- `meme_library.py`: gom audio/JSON thành danh mục, cache file đã xử lý, báo trùng/thiếu.

## Thành phần cần biết

| Tên | Vai trò |
|---|---|
| `SegmentItem` | Một bài/bình luận để hiển thị và đọc |
| `comment_candidates`, `comment_coverage` | Pool bài/bình luận đã tải và phạm vi nguồn trong job |
| `VideoJob` | Job sản xuất video và trạng thái |
| `LayoutConfig`, `MediaConfig` | Bố cục phần trăm và các nguồn media |
| `PresetProfile` | Bộ cấu hình có tên |
| `AppSettings.load/save/to_dict` | Đọc/ghi `user_data/settings.json` |
| `BatchPipelineManager.enqueue_jobs` | Nhận và chạy lô |
| `approve_and_render` | Tiếp tục khâu render sau duyệt |
| `resume_job`, `pause_for_restart` | Tiếp tục job đã dừng/lỗi; tạm dừng để mở lại backend |
| `cancel_job`, `cancel_all_active` | Đánh dấu dừng |

## Caller và kết quả

UI tạo job, gọi manager và nhận `job_changed`, `review_ready`, `job_finished`,
`counts_changed`. Pipeline gọi scraper, AI, TTS và renderer.
Job mới giữ `ai_provider`/`ai_model` riêng; đổi cấu hình không đổi model của job đó.
`ai_usage` giữ các lượt gọi và hạn mức trước/sau; dữ liệu cũ mặc định rỗng.
Xem [token và hạn mức](ai-usage.md) cho thời điểm ghi nhận và giới hạn số liệu.
Pipeline giữ queue trong bộ nhớ. Web có PostgreSQL thì đồng bộ metadata job/đoạn,
phục hồi sau khởi động; JSON output vẫn được giữ. Xem [database](database.md).

`comment_sort` được lưu trong settings/preset và snapshot vào job, mặc định `likes`.
`reselect_comments` chỉ nhận job chờ duyệt/đã lỗi có pool: chọn lại top N từ cache,
chạy lại chuẩn hóa và trở về chờ duyệt; không mở Threads hoặc cuộn lại.
Mỗi ứng viên giữ `seg_id` đã cấp trong job để việc đổi thứ hạng không đổi liên kết.
`SegmentItem` giữ ID nguồn/cha, timestamp, repost và quote riêng; chỉ số thiếu có thể là `None`.

`MediaConfig` thêm file nền riêng, Random Start và cover/contain.
Các trường `meme_sound_*` đi cùng settings/preset/snapshot; `VideoJob.meme_sound_plan`
giữ lựa chọn theo `seg_id`. Xem [kho meme](meme-library.md).
`LayoutConfig.aspect_ratio` chọn 9:16 hoặc 16:9; `canvas_size` và `card_width_px`
là geometry dùng chung giữa preview và compositor. Cấu hình cũ vẫn mặc định 9:16.

## Tiếp tục job đang dở

`VideoJob.checkpoint` đánh dấu đã thu thập, chuẩn hóa, duyệt, chọn meme và ghép MP4.
Sau mỗi bước và mỗi audio hoàn tất, ghi `job-checkpoint.json` bằng file tạm rồi replace.
`checkpoint_at` giúp loader chọn snapshot local mới hơn bản PostgreSQL nếu app bị ngắt
trước checkpoint DB kế tiếp. Bản DB cùng mốc hoặc mới hơn giữ ưu tiên, gồm sửa tay đã lưu.

Job đang chạy khi backend bị ngắt được tự tiếp tục khi mở lại web có PostgreSQL.
Đóng backend có trật tự đánh dấu `resume_on_startup`; giữ nguyên job đang chờ duyệt.
Bấm Dừng/Dừng lô là dừng tay, không tự chạy lại; bấm **Tiếp tục tạo** khi muốn chạy tiếp.
Job lỗi cũng có nút tiếp tục. Chỉ nhận một worker mỗi job; phải chờ worker cũ kết thúc.

Tiếp tục bỏ qua thu thập/AI đã hoàn tất và giữ nội dung đã duyệt. Nếu chưa duyệt,
vẫn trở lại bước duyệt trước khi xuất. Chọn lại bình luận vô hiệu checkpoint chuẩn bị.
Sửa nội dung/bố cục qua web bỏ duyệt cũ và kế hoạch xuất tương ứng.
Meme đã chọn được dùng lại khi dữ liệu đầu vào không đổi, kể cả kế hoạch rỗng.

TTS dùng lại WAV hợp lệ khi hash lời đọc, giọng, tốc độ và cấu hình VieNeu khớp.
Đoạn thiếu/hỏng/đổi đầu vào được tạo lại; timeline và thẻ được dựng lại theo thứ tự hiện tại.
Job cũ chưa có checkpoint chỉ nhận audio khi metadata khớp `content-reviewed.json`.
FFmpeg bị ngắt giữa chừng phải ghép lại bước MP4; không nối tiếp byte MP4 đang ghi dở.
Lượt AI/TTS bị ngắt trước khi có kết quả/checkpoint có thể phải gọi lại.

## Ràng buộc khi sửa

- Không đổi ý nghĩa ID đoạn/trạng thái hoặc bỏ qua bước duyệt.
- Field cấu hình mới cần default cho cấu hình cũ, serialization và UI tương ứng.
- Giữ giới hạn concurrency theo từng semaphore.
- Không cập nhật widget trong worker.
- Đừng hiểu `cancelled` là đã kill toàn bộ subprocess đang chạy.
- `resolved_output_root()`/`user_data_dir()` có tạo thư mục; không dùng tùy tiện trong kiểm tra chỉ đọc.

## Xác minh phù hợp

Kiểm tra enum, schema round-trip bằng dữ liệu giả khi được phép.
Với lỗi luồng job, xem đường đi trạng thái và Qt signals cả thành công/lỗi/hủy.
Không cần gọi AI/TTS thật để kiểm tra một thay đổi serialization.
