# CodeGraph của dự án

CodeGraph đã được khởi tạo tại gốc dự án, lưu index trong `.codegraph/`.
Index hiện chỉ lập chỉ mục mã nguồn Python; không đưa `.venv`, output hay profile vào graph.

## Khi đọc hoặc sửa code

Ưu tiên MCP `codegraph_explore`, truyền `projectPath` trỏ tới gốc dự án hiện tại.
Ví dụ query: `_call_cli_batch _on_ai_provider_changed AppSettings`.
Kết quả trả source và quan hệ caller; không cần đọc lại phần source đã có trong kết quả.
Nếu query bị cắt, dùng tên symbol cụ thể hơn.

Nếu MCP không dùng được, thử CLI dự phòng từ gốc dự án:

```powershell
codegraph explore "normalize_segments_batch _call_cli_batch"
```

Trên PowerShell bị chặn script launcher, dùng `codegraph.cmd` thay `codegraph`.
Nếu CodeGraph không khả dụng qua cả MCP và CLI hoặc chưa có index, dùng `rg`/`rg --files`
trong thư mục liên quan; bỏ qua `.venv/`, `output/`, `user_data/`, binary và cache.
Nói rõ giới hạn của CodeGraph khi dùng tìm kiếm thường.

## Đồng bộ sau thay đổi

```powershell
codegraph sync
codegraph status
```

`sync` cập nhật các file đã đổi; `status` phải báo index hiện hành.
Chạy lại trước khi truy vấn nếu graph chưa phản ánh thay đổi mới.
Không cần `init` mỗi lần mở dự án; không tự rebuild hoặc nâng cấp công cụ chỉ để sync.

Máy mới chưa có `.codegraph/` thì chủ dự án cần cho phép khởi tạo:

```powershell
codegraph init .
```

## Phạm vi và bảo trì

Rule dùng graph trước và sync sau sửa mã nằm trong [AGENTS.md](../../AGENTS.md).
Index là dữ liệu cục bộ, không thay thế code hoặc tài liệu.
`.codegraph/.gitignore` do công cụ tạo đã bỏ qua database/log/file tạm.
Không tự cài thêm MCP vào cấu hình toàn máy: phiên làm việc này đã có MCP truy cập dự án.
Graph không đảm bảo hiểu đầy đủ Qt signals hoặc dispatch runtime; kiểm tra caller liên quan khi cần.
