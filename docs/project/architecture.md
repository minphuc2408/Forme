# Kiến trúc và luồng dữ liệu

## Khởi động

`run_studio.py` → `threadstudio.app.main()` → `ensure_sample_assets()` →
`AppSettings.load()` → `QApplication`/theme → `ThreadsStudioWindow`.

Launcher thêm `src/` vào đường dẫn import; package cũng có entrypoint `threadstudio`.

## Luồng sản xuất

```mermaid
flowchart LR
    A[URL hoặc kịch bản] --> B[Thu thập / tách đoạn]
    B --> C[AI CLI hoặc từ điển offline]
    C --> D{Yêu cầu duyệt?}
    D -->|Có| E[Inspector sửa lời đọc / giọng / bố cục]
    D -->|Không| F[TTS và thẻ ảnh]
    E --> F
    F --> G[Trộn âm thanh và FFmpeg]
    G --> H[MP4 và JSON kiểm tra]
```

`BatchPipelineManager` giữ job trong bộ nhớ và điều phối bằng thread pool.
Các semaphore giới hạn riêng thu thập, AI, TTS và render.

## Trạng thái

`queued` → `scraping` → `normalizing` → `awaiting_review` (nếu bật) →
`synthesizing` → `rendering` → `completed`.

Lỗi đi tới `failed`; yêu cầu dừng đánh dấu `cancelled`.
Hủy hiện được kiểm tra giữa các phần xử lý, không bảo đảm ngắt ngay subprocess đang chạy.
`approve_and_render` cho phép tiếp tục từ `awaiting_review` hoặc `failed`;
không đồng nghĩa tự chạy lại đầy đủ phần thu thập/AI.

## Hợp đồng dữ liệu

- `SegmentItem`: đơn vị lời đọc/thẻ; `seg_id` nối dữ liệu giữa các tầng.
- `raw_text`: nội dung gốc để hiển thị trên thẻ.
- `spoken_text`: nội dung đã chuẩn hóa hoặc do người dùng sửa để TTS đọc.
- `VideoJob`: input, đoạn nội dung, cấu hình media/layout, trạng thái và đường dẫn output.
- `LayoutConfig`: tọa độ/kích thước theo phần trăm trên khung 1080×1920.
- `AppSettings`: cấu hình toàn app; không phải cơ sở dữ liệu khôi phục hàng đợi.

## Ranh giới cần giữ

- Scraper không gọi TTS hoặc render video.
- AI trả mapping `seg_id → lời đọc`; không quyết định giọng hoặc điều khiển UI.
- TTS cập nhật thời lượng, đường dẫn WAV và mốc thời gian từng đoạn.
- Card renderer dùng nội dung gốc; compositor dùng thẻ và âm thanh đã tạo.
- UI nhận Qt signal từ worker rồi mới cập nhật widget.

## Khi thay đổi một hành vi

Theo cả hai caller của chuẩn hóa: pipeline xử lý lô và nút chuẩn hóa lại trong Inspector.
Theo đủ bốn nơi khi đổi cấu hình: field, serialization, load và UI/caller.
Khi đổi layout, kiểm tra preview trong `stage_canvas.py` và output FFmpeg.

Xem [module core](../modules/core.md) và [lưu dữ liệu](data-storage.md).
