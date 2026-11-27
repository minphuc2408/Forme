# Dùng Codex cho dự án này

## Rule khác với tài liệu và huấn luyện

Tên file Codex nhận biết là **`AGENTS.md`**, có chữ **S**.
Đây là instruction nạp vào ngữ cảnh làm việc, không huấn luyện lại model.
Các file `docs/*.md` là tài liệu để đọc khi cần; không tự trở thành rule chỉ vì tồn tại.
Root `AGENTS.md` dẫn agent tới đúng tài liệu để tránh phải đọc mọi thứ mỗi lần.

Theo [hướng dẫn chính thức OpenAI](https://learn.chatgpt.com/docs/agent-configuration/agents-md):

- Có hướng dẫn cá nhân trong Codex home và hướng dẫn dự án theo thư mục làm việc.
- `AGENTS.override.md` được ưu tiên hơn `AGENTS.md` tại cùng cấp.
- Rule ở thư mục sâu hơn có thể cụ thể hóa rule phía trên khi được nạp.
- Cần bắt đầu phiên mới sau khi đổi instruction để kiểm tra file được nạp.

Không chỉnh rule toàn máy của người khác để áp dụng quy ước riêng của dự án.
Thư mục hiện tại chưa có `.git/`: hãy mở Codex từ gốc dự án để root rule được tìm thấy.
Nếu mở agent ngay trong thư mục con, yêu cầu đọc root `AGENTS.md` trước khi sửa.

## Quy trình cho người mới

1. Mở dự án từ thư mục chứa `AGENTS.md`.
2. Yêu cầu AI tóm tắt mục tiêu và chỉ ra file/caller có liên quan.
3. Mô tả hành vi mong muốn bằng ví dụ đầu vào/đầu ra.
4. Nêu rõ ràng điều không được thay đổi.
5. Cho AI thực hiện sửa nhỏ, rồi xem thay đổi và kết quả kiểm tra.
6. Chạy thử đúng luồng người dùng bị ảnh hưởng trước khi dùng với dữ liệu quan trọng.

Ví dụ mở CLI:

```powershell
cd D:\threadstudio-main
codex
```

Không cần sửa file cấu hình Codex hoặc chọn model cố định cho mọi người.
Người nhận dự án vẫn cần đăng nhập và có quyền chạy model/công cụ trên máy của họ.

## Prompt bắt đầu để kiểm tra rule

```text
Đọc AGENTS.md và docs/README.md. Nêu mục tiêu dự án, module liên quan
và các giới hạn đang áp dụng. Chưa sửa file, chưa gọi AI/TTS online.
Nếu không biết instruction nào đã được tự động nạp, nói rõ điều đó.
```

## Prompt giao một thay đổi cụ thể

```text
Mục tiêu: [hành vi muốn có].
Ví dụ: input [A] phải cho kết quả [B].
Phạm vi: [module hoặc màn hình]. Giữ nguyên [những phần cần giữ].
Đọc caller và tài liệu liên quan, thực hiện thay đổi tối thiểu.
Không tạo test mới, không gọi dịch vụ online nếu chưa cần cho nhiệm vụ.
Cuối cùng báo file đã sửa, cách kiểm tra và phần chưa xác minh.
```

Thay nội dung trong ngoặc vuông; tránh yêu cầu mơ hồ như “sửa hết app cho tốt”.
Với việc chỉ muốn đánh giá, nói “chỉ đọc và đề xuất, chưa sửa file”.

## Duy trì rule

- Rule chung và ổn định ở root; chi tiết module ở `docs/modules/`.
- Chỉ thêm `AGENTS.md` con nếu thư mục có quy ước khác thực sự.
- Không cần một rule cho mọi file và không sao chép toàn bộ docs vào instruction.
- Khi sửa hành vi, cập nhật tài liệu tương ứng trong cùng nhiệm vụ.
- Mỗi tài liệu tối đa 200 dòng; chia theo chủ đề khi vượt giới hạn.
- Không nhúng token, cookie, đường dẫn cá nhân hoặc lịch sử hội thoại vào rule dùng chung.

Rule hỗ trợ AI hiểu dự án; nó không thay thế sandbox, review hoặc kiểm tra thực tế.
Tôi không biết đầy đủ chi tiết huấn luyện nội bộ của OpenAI;
bộ hướng dẫn này dựa vào tài liệu công khai và mã nguồn dự án đã kiểm tra.
