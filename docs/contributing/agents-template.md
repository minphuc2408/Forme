# Mẫu rule cho dự án khác

Đây là mẫu để sao chép và điều chỉnh, không phải instruction tự động nạp.
Tạo `AGENTS.md` ở gốc dự án mới, thay các ô `[ ... ]` bằng dữ kiện đã xác minh.
Không mang đường dẫn/module Threads Studio sang một dự án khác.

```markdown
# Quy tắc dự án [tên]

## Mục tiêu và phạm vi
- Dự án làm [việc gì] cho [ai].
- Chỉ sửa phần phục vụ yêu cầu; giữ code đang hoạt động và thay đổi của người dùng.
- Giữ cấu trúc, naming và phong cách hiện có; tránh refactor ngoài phạm vi.
- Không tự publish, push, xóa dữ liệu hoặc cài công cụ không được yêu cầu.

## Bắt đầu
- Đọc [đường dẫn mục lục docs], sau đó chỉ đọc tài liệu module liên quan.
- Kiểm tra instruction áp dụng và trạng thái Git nếu có Git.
- Nếu có index CodeGraph dùng được, dùng trước; nếu không, tìm bằng rg.
- Đọc điểm sửa và caller trước khi đổi hành vi.

## Môi trường
- Runtime: [ngôn ngữ/phiên bản].
- Cài dependency: [lệnh đã xác minh].
- Chạy: [lệnh đã xác minh].
- Kiểm tra: [lệnh hiện có; nói rõ nếu chưa có].
- Không bịa lệnh test/lint hoặc kết quả kiểm tra.

## Bản đồ
- [thư mục]: [trách nhiệm và điểm vào].
- [thư mục]: [trách nhiệm và điểm vào].
- Dữ liệu sinh ra: [đường dẫn không sửa bằng tay].

## Ràng buộc
- Giữ [schema/hợp đồng dữ liệu/điều kiện nghiệp vụ quan trọng].
- Không lưu secrets hoặc dữ liệu thật vào source, docs và log.
- Ưu tiên helper, stdlib và dependency sẵn có.
- Quy định tạo file/test/dependency: [thỏa thuận của dự án này].

## Hoàn tất
- Kiểm tra đúng luồng bị ảnh hưởng với mức chi phí phù hợp.
- Cập nhật tài liệu nếu hành vi thay đổi; mỗi file docs tối đa 200 dòng.
- Báo đã đổi gì, kiểm tra gì và điều chưa xác minh.
```

Không dùng mẫu này để ghi đè `~/.codex/AGENTS.md` của người khác.
Rule cá nhân toàn máy là lựa chọn riêng; rule dự án nên đi cùng mã nguồn.
Nguồn tham khảo: [OpenAI AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
