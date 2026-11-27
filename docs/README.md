# Tài liệu Threads Studio Pro

Các tài liệu này mô tả code hiện có, không phải danh sách tính năng dự kiến.
Mỗi file tối đa 200 dòng. Chỉ mở phần liên quan đến nhiệm vụ.

## Người mới bắt đầu

1. [Tổng quan dự án](project/overview.md).
2. [Cài đặt và chạy](contributing/getting-started.md).
3. [Làm việc với Codex](contributing/codex-workflow.md).
4. [Quy tắc chung cho agent](../AGENTS.md).

## Sản phẩm và kiến trúc

- [Tính năng và giới hạn](project/features.md).
- [Luồng xử lý và ranh giới module](project/architecture.md).
- [Dữ liệu, cấu hình và dung lượng](project/data-storage.md).
- [Mục tiêu sản phẩm](../PRODUCT.md).
- [Thiết kế giao diện](../DESIGN.md).

## Module

| Module | Tài liệu |
|---|---|
| Cấu hình, model, điều phối job | [core](modules/core.md) |
| Chuẩn hóa văn bản và OCR | [ai](modules/ai.md) |
| Thu thập nội dung | [scraping](modules/scraping.md) |
| Giọng đọc | [tts](modules/tts.md) |
| Thẻ và video | [rendering](modules/rendering.md) |
| Giao diện | [ui](modules/ui.md) |

## Phát triển và công cụ

- [Các kiểm tra phù hợp](contributing/validation.md).
- [Mẫu AGENTS.md cho dự án khác](contributing/agents-template.md).
- [Cài riêng Antigravity CLI](tools/antigravity-cli.md).
- [CodeGraph: truy vấn và đồng bộ](tools/codegraph.md).

Giữ rule trong `AGENTS.md`; giữ mô tả và ví dụ trong `docs/`.
Không nhân bản toàn bộ mã nguồn hoặc lịch sử hội thoại vào tài liệu.
