# Antigravity CLI — chỉ cài CLI

Antigravity CLI của Google có lệnh `agy`, tách riêng Antigravity App và IDE.
Trong nhiệm vụ này chỉ cài CLI, không cài desktop app/IDE/extension/SDK.

## Cài trên máy mới

Mở [trang CLI chính thức](https://antigravity.google/product/antigravity-cli)
và mục **Antigravity CLI** của [trang tải](https://antigravity.google/download).
Lệnh PowerShell được Google cung cấp:

```powershell
irm https://antigravity.google/cli/install.ps1 | iex
```

Khi thực hiện thay người dùng, tải script về thư mục tạm và đọc trước khi chạy.
Installer tải binary theo kiến trúc máy, kiểm tra SHA-512 từ manifest,
rồi cài `agy.exe` và thiết lập môi trường.
Chỉ chạy installer chính thức cho CLI, không tải installer App/IDE.

## Máy hiện tại

Đã cài và xác minh phiên bản **1.5.18** ngày 26/11/2026.
Binary ở `%LOCALAPPDATA%\agy\bin\agy.exe`.
Thư mục binary đã có trong PATH người dùng; mở terminal mới để nhận PATH mới.

```powershell
agy --version
agy --help
```

Nếu terminal đang mở chưa tìm thấy lệnh:

```powershell
& "$env:LOCALAPPDATA\agy\bin\agy.exe" --version
```

## Lần sử dụng đầu

Chạy `agy` và làm theo hướng dẫn terminal về giao diện, workspace và đăng nhập.
Không coi kiểm tra `--version` là đã đăng nhập hoặc có quota model.
Đã lấy danh sách model và chạy thành công luồng chuẩn hóa văn bản qua tài khoản trên máy.
Không cần cài desktop app chỉ để có executable CLI.

Tài liệu bắt đầu: [Google Getting Started, tab CLI](https://antigravity.google/docs/getting-started?tab=cli).
CLI có lệnh `models`, chế độ `--print` và output JSON; quyền sử dụng phụ thuộc tài khoản.

## Quan hệ với Threads Studio

App hiện gọi Codex CLI, Antigravity CLI hoặc từ điển Offline.
Antigravity dùng stream-json, file ảnh tạm, tài khoản Google và model riêng.
Gợi ý Flash cho tác vụ nhanh; Hydrogen cho nội dung/ảnh khó.
Không cài Antigravity App/IDE và không dùng API key.
