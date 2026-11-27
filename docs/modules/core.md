# Module core

Nguồn: `src/threadstudio/core/`.

## Trách nhiệm

- `models.py`: enum và dataclass dùng chung.
- `config.py`: cấu hình bền vững và các preset mặc định.
- `pipeline.py`: điều phối vòng đời job và các tầng xử lý.

## Thành phần cần biết

| Tên | Vai trò |
|---|---|
| `SegmentItem` | Một bài/bình luận để hiển thị và đọc |
| `VideoJob` | Job sản xuất video và trạng thái |
| `LayoutConfig`, `MediaConfig` | Bố cục phần trăm và các nguồn media |
| `PresetProfile` | Bộ cấu hình có tên |
| `AppSettings.load/save/to_dict` | Đọc/ghi `user_data/settings.json` |
| `BatchPipelineManager.enqueue_jobs` | Nhận và chạy lô |
| `approve_and_render` | Tiếp tục khâu render sau duyệt |
| `cancel_job`, `cancel_all_active` | Đánh dấu dừng |

## Caller và kết quả

UI tạo job, gọi manager và nhận `job_changed`, `review_ready`, `job_finished`,
`counts_changed`. Pipeline gọi scraper, AI, TTS và renderer.
Job/queue nằm trong bộ nhớ; các JSON output phục vụ lưu dữ liệu từng bước.

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
