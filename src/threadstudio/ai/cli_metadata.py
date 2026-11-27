"""Read-only model and quota metadata through supported CLI interfaces."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import tempfile
import threading
import time
from typing import Any

from .text_normalizer import cli_command, cli_environment
from .usage import utc_now
from ..core.models import VideoJob


def _codex_metadata(include_models: bool) -> dict[str, Any]:
    process = subprocess.Popen(
        cli_command("codex") + ["app-server", "--listen", "stdio://", "-c", 'forced_login_method="chatgpt"'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", env=cli_environment(), cwd=tempfile.gettempdir(),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    responses: queue.Queue = queue.Queue()

    def read() -> None:
        try:
            for line in process.stdout:
                try:
                    message = json.loads(line)
                    if isinstance(message, dict) and "id" in message:
                        responses.put(message)
                except ValueError:
                    continue
        finally:
            responses.put(None)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline = time.monotonic() + 20

    def send(payload: dict) -> None:
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()

    def rpc(ident: int, method: str, params: Any = None) -> dict:
        send({"id": ident, "method": method, "params": params})
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Metadata CLI quá thời gian.")
            message = responses.get(timeout=remaining)
            if message is None:
                raise RuntimeError("CLI đóng kết nối metadata.")
            if message.get("id") == ident:
                if message.get("error"):
                    raise RuntimeError("CLI chưa trả được metadata. Kiểm tra đăng nhập ChatGPT và phiên bản Codex.")
                return message.get("result", {})
            if "method" in message:
                send({"id": message["id"], "error": {"code": -32601, "message": "Only metadata reads are supported"}})

    try:
        rpc(1, "initialize", {"clientInfo": {"name": "threadstudio_usage", "version": "2.0.0"}, "capabilities": {"experimentalApi": True}})
        send({"method": "initialized"})
        models = []
        if include_models:
            result = rpc(2, "model/list", {"limit": 100, "includeHidden": False})
            models = [{"id": item["model"], "name": item.get("displayName") or item["model"]}
                      for item in result.get("data", []) if isinstance(item, dict) and isinstance(item.get("model"), str)]
        try:
            limits = rpc(3, "account/rateLimits/read")
            buckets = limits.get("rateLimitsByLimitId") or {"codex": limits.get("rateLimits")}
            windows = []
            for key, bucket in buckets.items():
                if not isinstance(bucket, dict):
                    continue
                for field in ("primary", "secondary"):
                    window = bucket.get(field)
                    if not isinstance(window, dict):
                        continue
                    used, duration, reset = window.get("usedPercent"), window.get("windowDurationMins"), window.get("resetsAt")
                    if type(used) not in (int, float) or type(duration) is not int or duration <= 0 or not 0 <= used <= 100:
                        continue
                    windows.append({"bucket": str(key), "name": bucket.get("limitName") or str(key), "window_minutes": duration,
                                    "used_percent": used, "remaining_percent": 100 - used,
                                    "resets_at": reset if type(reset) is int else None})
            quota = {"status": "available" if windows else "unavailable", "windows": windows,
                     "message": "" if windows else "CLI chưa trả về hạn mức tài khoản."}
        except (RuntimeError, TimeoutError, queue.Empty):
            quota = {"status": "unavailable", "windows": [], "message": "Chưa đọc được hạn mức Codex. Kiểm tra đăng nhập ChatGPT."}
        return {"provider": "codex", "models": models, "quota": quota, "captured_at": utc_now(), "source": "codex_app_server"}
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        process.stdin.close()
        reader.join(timeout=1)
        if not reader.is_alive():
            process.stdout.close()


def read_cli_metadata(provider: str, *, include_models: bool = False) -> dict[str, Any]:
    if provider == "offline":
        return {"provider": provider, "models": [], "captured_at": utc_now(), "quota": {"status": "not_applicable", "windows": [], "message": "Từ điển Offline không dùng token AI."}}
    try:
        if provider == "codex":
            return _codex_metadata(include_models)
        if provider != "antigravity":
            raise ValueError("Provider không hợp lệ.")
        models = []
        if include_models:
            result = subprocess.run(cli_command(provider) + ["models"], capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", cwd=tempfile.gettempdir(), env=cli_environment(), timeout=20,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if result.returncode:
                raise RuntimeError("Chưa đọc được danh sách model Antigravity. Kiểm tra đăng nhập Google.")
            for line in result.stdout.splitlines():
                parts = line.strip().split("\t", 1)
                if len(parts) == 2 and parts[0] and not any(char.isspace() for char in parts[0]):
                    models.append({"id": parts[0], "name": parts[1].strip()})
        return {"provider": provider, "models": models, "captured_at": utc_now(), "source": "antigravity_models",
                "quota": {"status": "unavailable", "windows": [], "message": "Antigravity CLI hiện cung cấp quota qua bảng /usage tương tác; chưa có số quota tự động cho app. Mở agy rồi gõ /usage để xem."}}
    except (OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired, queue.Empty, ValueError, TypeError, KeyError, AttributeError):
        return {"provider": provider, "models": [], "captured_at": utc_now(), "source": "cli_unavailable",
                "quota": {"status": "unavailable", "windows": [], "message": "Chưa đọc được metadata CLI. Kiểm tra CLI đã cài, tài khoản đăng nhập và kết nối mạng."}}


def capture_quota_before(job: VideoJob, provider: str) -> None:
    before = job.ai_usage.setdefault("quota_before", {})
    if provider not in before:
        before[provider] = read_cli_metadata(provider)
    job.ai_usage.pop("quota_after", None)


def capture_quota_after(job: VideoJob) -> None:
    if job.ai_usage.get("quota_before"):
        job.ai_usage["quota_after"] = {provider: read_cli_metadata(provider) for provider in job.ai_usage["quota_before"]}
