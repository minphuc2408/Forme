"""Loopback-only browser interface over the existing Python production pipeline."""
from __future__ import annotations

import asyncio
from collections import deque
import copy
from dataclasses import asdict, fields
import json
import logging
import math
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
from typing import Any
from urllib.parse import urlsplit
import webbrowser

from aiohttp import ClientError, ClientSession, ClientTimeout, web
from fluent_blue.compatibility.qt import QtCore, QtGui
from psycopg import Error as PostgreSQLError

from .ai.text_normalizer import cli_command, cli_environment, normalize_segments_batch
from .ai.cli_metadata import capture_quota_before, read_cli_metadata
from .ai.usage import track_ai_usage, usage_summary, write_usage
from .core.config import AppSettings, project_root
from .core.database import StudioDatabase
from .core.meme_library import (
    load_sound_catalog_data, resolve_sound_file, scan_sound_library, sound_library_root, update_sound, update_emotion_group,
)
from .core.models import (
    CommentMode, LayoutConfig, MediaConfig, PresetProfile, SegmentItem, STAGE_LABELS_VI, VideoJob, VoiceAssignMode,
)
from .core.pipeline import BatchPipelineManager
from .render.card_renderer import render_threads_card_qimage
from .scrapers.threads_scraper import open_threads_login_session, sample_video1_script
from .tts.router import TTSRouter, _EDGE_VOICES, _VIENEU_PRESETS

logger = logging.getLogger("threadstudio")
STATIC_ROOT = Path(__file__).parent / "ui" / "web"
EDITABLE_STAGES = {"awaiting_review", "failed"}
MEDIA_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac"}


def _port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.5)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def _port_owners(port: int) -> list[dict[str, Any]]:
    script = f"""
        $ErrorActionPreference = 'Stop'
        @(Get-NetTCPConnection -LocalPort {int(port)} -State Listen -ErrorAction SilentlyContinue |
          Where-Object {{ $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '::', '::ffff:127.0.0.1') }} |
          Select-Object -ExpandProperty OwningProcess -Unique |
          ForEach-Object {{
            $studioProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $_"
            if ($studioProcess) {{
              [pscustomobject]@{{ ProcessId = $studioProcess.ProcessId; CommandLine = $studioProcess.CommandLine;
                Created = $studioProcess.CreationDate.ToUniversalTime().Ticks.ToString() }}
            }}
          }}) | ConvertTo-Json -Compress
    """
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=12,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f"Chưa xác định được phiên đang giữ cổng {port}.")
    owners = json.loads(result.stdout.strip() or "[]")
    return owners if isinstance(owners, list) else [owners]


def _wait_or_stop_previous(owners: list[dict[str, Any]]) -> bool:
    # Creation time protects against terminating a different process after PID reuse.
    script = "$ErrorActionPreference = 'Stop'; $studioForced = $false\n"
    for owner in owners:
        ident, created = int(owner["ProcessId"]), int(owner["Created"])
        script += f"""
            $studioProcess = Get-CimInstance Win32_Process -Filter 'ProcessId = {ident}'
            if ($studioProcess -and $studioProcess.CreationDate.ToUniversalTime().Ticks -eq {created}) {{
              Wait-Process -Id {ident} -Timeout 10 -ErrorAction SilentlyContinue
              $studioProcess = Get-CimInstance Win32_Process -Filter 'ProcessId = {ident}'
              if ($studioProcess -and $studioProcess.CreationDate.ToUniversalTime().Ticks -eq {created}) {{
                & taskkill.exe /PID {ident} /T /F | Out-Null
                if ($LASTEXITCODE -ne 0) {{ throw 'Could not stop the previous Studio process' }}
                $studioForced = $true
              }}
            }}
        """
    script += "ConvertTo-Json -InputObject $studioForced -Compress"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=15 + 10 * len(owners), creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError("Chưa dừng được phiên Studio cũ. Kiểm tra quyền của terminal đang chạy app.")
    return json.loads(result.stdout.strip() or "false") is True


async def _prepare_port(port: int) -> None:
    if not await asyncio.to_thread(_port_busy, port):
        return
    if sys.platform != "win32":
        raise RuntimeError(f"Cổng {port} đang được sử dụng. Dừng phiên cũ rồi chạy lại Studio.")
    owners = await asyncio.to_thread(_port_owners, port)
    if not await asyncio.to_thread(_port_busy, port):
        return
    studio_command = re.compile(r"\b(?:run_studio\.py|threadstudio(?:\.app|\.exe)?)(?:[\s\"']|$)", re.IGNORECASE)
    if not owners or any(int(owner["ProcessId"]) in {0, 4, os.getpid()} or not studio_command.search(owner.get("CommandLine") or "") for owner in owners):
        raise RuntimeError(f"Cổng {port} đang do ứng dụng khác sử dụng. Đổi --port hoặc dừng ứng dụng giữ cổng này.")
    logger.info("Cổng %d có phiên Studio cũ · Đang dừng phiên cũ trước khi khởi động lại...", port)
    base = f"http://127.0.0.1:{port}"
    try:
        async with ClientSession(timeout=ClientTimeout(total=3)) as session:
            async with session.get(base, allow_redirects=False) as response:
                html = await response.text()
            token = re.search(r'<meta\s+name="studio-token"\s+content="([A-Za-z0-9_-]+)"', html)
            if token and "Threads Studio" in html:
                async with session.post(base + "/api/action", json={"action": "shutdown"},
                                        headers={"X-Studio-Token": token[1], "Origin": base}, allow_redirects=False) as response:
                    await response.read()
    except (ClientError, TimeoutError, OSError):
        pass
    forced = await asyncio.to_thread(_wait_or_stop_previous, owners)
    for _ in range(30):
        if not await asyncio.to_thread(_port_busy, port):
            logger.info("Đã giải phóng cổng %d%s.", port, " · Phiên cũ không thoát kịp nên đã được dừng" if forced else "")
            return
        await asyncio.sleep(0.1)
    raise RuntimeError(f"Cổng {port} chưa được giải phóng sau khi dừng Studio cũ.")


def _patch_config(target: Any, patch: dict[str, Any]) -> None:
    """Validate browser JSON before applying it to an isolated settings snapshot."""
    if not isinstance(patch, dict):
        raise ValueError("Cấu hình phải là một đối tượng JSON.")
    known = {item.name for item in fields(target)}
    for key, value in patch.items():
        if key not in known or key == "presets":
            raise ValueError(f"Trường cấu hình không hợp lệ: {key}")
        current = getattr(target, key)
        if isinstance(current, (LayoutConfig, MediaConfig)):
            _patch_config(current, value)
        elif isinstance(current, bool):
            if type(value) is not bool:
                raise ValueError(f"{key} phải là bật/tắt.")
            setattr(target, key, value)
        elif isinstance(current, (float, int)):
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{key} phải là số hữu hạn.")
            if isinstance(current, int) and int(value) != value:
                raise ValueError(f"{key} phải là số nguyên.")
            setattr(target, key, type(current)(value))
        elif isinstance(current, list):
            if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v.strip() for v in value):
                raise ValueError("Hãy chọn ít nhất một giọng đọc hợp lệ.")
            setattr(target, key, list(dict.fromkeys(value)))
        else:
            if not isinstance(value, str) or len(value) > 20000:
                raise ValueError(f"{key} phải là văn bản hợp lệ.")
            setattr(target, key, value)


def _validate_settings(settings: AppSettings) -> None:
    choices = {
        "ai_provider": {"codex", "antigravity", "offline"}, "theme": {"light", "dark", "high-contrast"},
        "comment_mode": {v.value for v in CommentMode}, "comment_sort": {"likes", "replies", "reposts", "quotes"},
        "voice_assign_mode": {v.value for v in VoiceAssignMode},
    }
    for key, allowed in choices.items():
        if getattr(settings, key) not in allowed:
            raise ValueError(f"Lựa chọn {key} không hợp lệ.")
    if settings.ai_provider != "offline":
        model = settings.codex_model if settings.ai_provider == "codex" else settings.antigravity_model
        if not model.strip():
            raise ValueError("Hãy chọn hoặc nhập tên model AI.")
    bounds = {"max_comments": (1, 25), "voice_speed": (0.75, 1.8),
              **{f"max_{stage}_workers": (1, 12) for stage in ("scrape", "ai", "tts", "render")}}
    for key, (low, high) in bounds.items():
        if not low <= getattr(settings, key) <= high:
            raise ValueError(f"{key} phải nằm trong khoảng {low}–{high}.")
    cfg = settings.layout
    if cfg.aspect_ratio not in {"9:16", "16:9"} or cfg.card_theme not in {"light", "dark"}:
        raise ValueError("Tỷ lệ hoặc theme thẻ không hợp lệ.")
    if cfg.sub_fit not in {"cover", "contain"} or settings.media.bg_fit not in {"cover", "contain"}:
        raise ValueError("Cách fit phải là cover hoặc contain.")
    layout_bounds = {"card_scale_pct": (55, 122), "card_radius_px": (0, 64), "sub_radius_px": (0, 64),
                     "sub_w_pct": (25, 100), "sub_h_pct": (12, 65)}
    layout_bounds.update({f"{layer}_{axis}_pct": (5, 95) for layer in ("card", "sub") for axis in ("x", "y")})
    for key, (low, high) in layout_bounds.items():
        if not low <= getattr(cfg, key) <= high:
            raise ValueError(f"{key} phải nằm trong khoảng {low}–{high}.")
    for key, (low, high) in {"bgm_volume_pct": (0, 100), "sfx_volume_pct": (0, 100),
                             "meme_sound_volume_pct": (0, 100), "meme_sound_max_per_video": (0, 20),
                             "meme_sound_max_duration_sec": (0.1, 30)}.items():
        if not low <= getattr(settings.media, key) <= high:
            raise ValueError(f"{key} phải nằm trong khoảng {low}–{high}.")


class StudioWebServer(logging.Handler):
    def __init__(self, settings: AppSettings, *, port: int = 8000, use_database: bool = True) -> None:
        super().__init__()
        self.settings = settings
        self.port = port
        self.pipeline = BatchPipelineManager(settings)
        self.database = StudioDatabase.load() if use_database else None
        self._database_lock = asyncio.Lock()
        self._saved_jobs: dict[str, str] = {}
        self.token = secrets.token_urlsafe(32)
        self.logs: deque[str] = deque(maxlen=300)
        self.tasks: dict[str, dict[str, Any]] = {}
        self.running: set[asyncio.Task] = set()
        self.busy_jobs: set[str] = set()
        self.busy_actions: set[str] = set()
        self.threads_login: dict[str, Any] = {"state": "idle"}
        self.threads_profile_dir = self.settings.user_data_dir() / "threads_edge_profile"
        self.files: dict[str, Path] = {}
        self.voices = [asdict(v) for v in (*_EDGE_VOICES, *_VIENEU_PRESETS)]
        self.ai_metadata: dict[str, dict[str, Any]] = {}
        self.stopped = asyncio.Event()
        self.app = web.Application(middlewares=[self._guard], client_max_size=4 * 1024 * 1024)
        self.app.add_routes([
            web.get("/", self.index), web.get("/assets/{path:.*}", self.static),
            web.get("/api/state", self.state), web.get("/api/jobs/{job_id}", self.job_detail),
            web.post("/api/action", self.action), web.post("/api/card", self.card),
            web.get("/media/{file_id}", self.media),
            web.get("/{path:.*}", self.page),
        ])
        logger.addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        self.logs.append(self.format(record))

    @web.middleware
    async def _guard(self, request: web.Request, handler: Any) -> web.StreamResponse:
        allowed = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        if request.host not in allowed or request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise web.HTTPForbidden(text="Chỉ cho phép truy cập từ web local của app.")
        origin = request.headers.get("Origin")
        if origin and origin not in {f"http://{host}" for host in allowed}:
            raise web.HTTPForbidden(text="Nguồn yêu cầu không hợp lệ.")
        if request.method not in {"GET", "HEAD"}:
            if not secrets.compare_digest(request.headers.get("X-Studio-Token", ""), self.token):
                raise web.HTTPForbidden(text="Hãy tải lại trang để tiếp tục.")
        try:
            response = await handler(request)
        except web.HTTPException:
            raise
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            response = web.json_response({"error": str(exc)}, status=400)
        except Exception as exc:
            logger.error("Web: %s", exc)
            response = web.json_response({"error": str(exc)}, status=500)
        response.headers.update({
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        })
        return response

    async def index(self, request: web.Request) -> web.Response:
        if not (STATIC_ROOT / "index.html").is_file():
            raise web.HTTPServiceUnavailable(text="Chưa build giao diện React. Chạy npm ci rồi npm run build trong thư mục web/.")
        html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8").replace("__STUDIO_TOKEN__", self.token)
        return web.Response(text=html, content_type="text/html")

    async def page(self, request: web.Request) -> web.Response:
        path = request.match_info["path"].strip("/")
        pages = {"tao-video", "hang-doi", "kich-ban", "video", "tai-nguyen", "cong-cu", "kho-sound", "kho-anh",
                 "cau-hinh/giong-doc", "cau-hinh/nguon", "cau-hinh/bo-cuc", "cau-hinh/ai", "cau-hinh/he-thong"}
        if path not in pages and not (path.startswith("kich-ban/") and len(path.split("/")) == 2):
            raise web.HTTPNotFound(text="Trang không tồn tại.")
        return await self.index(request)

    async def static(self, request: web.Request) -> web.FileResponse:
        path = (STATIC_ROOT / "assets" / request.match_info["path"]).resolve()
        if not path.is_relative_to((STATIC_ROOT / "assets").resolve()) or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    def file_url(self, value: str | Path) -> str:
        if not value:
            return ""
        path = Path(value).resolve()
        if not path.is_file() or path.suffix.lower() not in MEDIA_SUFFIXES:
            return ""
        # Stable within the session; callers only receive an opaque media handle.
        existing = next((key for key, item in self.files.items() if item == path), None)
        if existing is None:
            existing = secrets.token_urlsafe(18)
            self.files[existing] = path
        return f"/media/{existing}"

    async def media(self, request: web.Request) -> web.FileResponse:
        path = self.files.get(request.match_info["file_id"])
        if path is None or not path.is_file():
            raise web.HTTPNotFound(text="File không còn tồn tại.")
        return web.FileResponse(path)

    def job(self, job_id: str, *, editable: bool = False) -> VideoJob:
        job = self.pipeline.jobs.get(job_id)
        if job is None:
            raise web.HTTPNotFound(text="Không tìm thấy job.")
        if editable and (job.stage not in EDITABLE_STAGES or job_id in self.busy_jobs or self.pipeline.is_running(job_id)):
            raise web.HTTPConflict(text="Chỉ sửa job đang chờ duyệt/đã lỗi và không có thao tác đang chạy.")
        if editable and job_id in self.pipeline._cancelled:
            raise web.HTTPConflict(text="Job đã dừng; hãy tạo job mới.")
        return job

    def job_summary(self, job: VideoJob) -> dict[str, Any]:
        return {"job_id": job.job_id, "title_slug": job.title_slug, "source_url": job.source_url,
                "stage": job.stage, "stage_label": STAGE_LABELS_VI.get(job.stage, job.stage),
                "progress_pct": job.progress_pct, "status_detail": job.status_detail,
                "error_message": job.error_message, "segment_count": len(job.segments),
                "output_mp4": job.output_mp4, "video_url": self.file_url(job.output_mp4),
                "busy": job.job_id in self.busy_jobs or (job.stage in {"cancelled", "failed"} and self.pipeline.is_running(job.job_id)),
                "can_resume": self.pipeline.can_resume(job.job_id) and job.job_id not in self.busy_jobs,
                "resume_on_startup": job.resume_on_startup, "ai_provider": job.ai_provider, "ai_model": job.ai_model,
                "ai_summary": usage_summary(job.ai_usage)}

    async def state(self, request: web.Request) -> web.Response:
        return web.json_response({"settings": self.settings.to_dict(), "voices": self.voices,
                                  "jobs": [self.job_summary(self.pipeline.jobs[jid]) for jid in self.pipeline.job_order],
                                  "tasks": self.tasks, "logs": list(self.logs), "ai_metadata": self.ai_metadata,
                                  "active_count": self.pipeline.active_count(), "review_count": self.pipeline.review_count(),
                                  "threads_login": {**self.threads_login,
                                                    "profile_available": (self.threads_profile_dir / "Default").is_dir()},
                                  "database": self.database.status() if self.database else {"enabled": False, "connected": False}})

    def _initialize_database(self) -> None:
        if self.database is None:
            return
        self.database.initialize()
        stored = self.database.load_settings()
        path = project_root() / "user_data" / "settings.json"
        if stored and (not path.is_file() or path.stat().st_mtime <= stored["updated_at"].timestamp()):
            payload = dict(stored["payload"])
            presets = payload.pop("presets", [])
            candidate = copy.deepcopy(self.settings)
            _patch_config(candidate, payload)
            candidate.presets = [PresetProfile.from_dict(item) for item in presets]
            _validate_settings(candidate)
            vars(self.settings).update(vars(candidate))
            self.pipeline._rebuild_semaphores()
        else:
            self.database.save_settings(self.settings.to_dict())
        imported, skipped = self.database.import_outputs(self.settings)
        jobs = self.database.load_jobs()
        self.pipeline.jobs = {job.job_id: job for job in jobs}
        self.pipeline.job_order = [job.job_id for job in jobs]
        logger.info("PostgreSQL · schema %s · %d job đã lưu · nhập %d output local · bỏ qua %d thư mục metadata lỗi.",
                    self.database.schema, len(jobs), imported, skipped)

    async def _persist_jobs(self) -> None:
        if self.database is None:
            return
        async with self._database_lock:
            snapshots = [asdict(self.pipeline.jobs[jid]) for jid in self.pipeline.job_order]
            encoded = {item["job_id"]: json.dumps(item, sort_keys=True, ensure_ascii=False) for item in snapshots}
            changed = [item for item in snapshots if encoded[item["job_id"]] != self._saved_jobs.get(item["job_id"])]
            if changed:
                await asyncio.to_thread(self.database.save_jobs, changed)
                self._saved_jobs.update(encoded)

    async def _database_worker(self) -> None:
        error_reported = False
        while not self.stopped.is_set():
            try:
                await self._persist_jobs()
                if self.database and self.database.connected:
                    error_reported = False
            except Exception:
                if not error_reported:
                    logger.error("Mất kết nối PostgreSQL; metadata chưa ghi sẽ được thử lưu lại.")
                    error_reported = True
                if self.database:
                    self.database.connected = False
            try:
                await asyncio.wait_for(self.stopped.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

    async def job_detail(self, request: web.Request) -> web.Response:
        job = self.job(request.match_info["job_id"])
        return web.json_response({**self.job_summary(job), "segments": [seg.to_dict() for seg in job.segments],
                                  "layout": job.layout.to_dict(), "comment_candidates": copy.deepcopy(job.comment_candidates),
                                  "ai_usage": copy.deepcopy(job.ai_usage),
                                  "comment_coverage": copy.deepcopy(job.comment_coverage),
                                  "comment_sort": job.comment_sort, "max_comments": job.max_comments})

    async def save_settings(self, patch: dict[str, Any]) -> None:
        candidate = copy.deepcopy(self.settings)
        _patch_config(candidate, patch)
        _validate_settings(candidate)
        worker_keys = [f"max_{stage}_workers" for stage in ("scrape", "ai", "tts", "render")]
        changed_workers = any(getattr(candidate, key) != getattr(self.settings, key) for key in worker_keys)
        if changed_workers and (self.pipeline.active_count() or self.busy_jobs):
            raise web.HTTPConflict(text="Chờ các job đang xử lý hoàn tất trước khi đổi số worker.")
        if self.database:
            await asyncio.to_thread(self.database.save_settings, candidate.to_dict())
        candidate.save()
        vars(self.settings).update(vars(candidate))
        if changed_workers:
            self.pipeline._rebuild_semaphores()

    def start_task(self, label: str, work: Any, *, key: str = "") -> str:
        if key and key in self.busy_actions:
            raise web.HTTPConflict(text="Thao tác này đang chạy.")
        task_id = secrets.token_hex(8)
        for old in list(self.tasks):
            if len(self.tasks) < 30:
                break
            if self.tasks[old]["state"] != "running":
                self.tasks.pop(old)
        self.tasks[task_id] = {"label": label, "state": "running"}
        self.busy_actions.add(key)

        async def run() -> None:
            try:
                result = await work()
                self.tasks[task_id].update(state="done", result=result)
                logger.info("%s: hoàn tất.", label)
            except Exception as exc:
                self.tasks[task_id].update(state="failed", error=str(exc))
                logger.error("%s: %s", label, exc)
            finally:
                self.busy_actions.discard(key)

        task = asyncio.create_task(run())
        self.running.add(task)
        task.add_done_callback(self.running.discard)
        return task_id

    async def card(self, request: web.Request) -> web.Response:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("Yêu cầu phải là JSON object.")
        layout = copy.deepcopy(self.settings.layout)
        _patch_config(layout, body.get("layout", {}))
        candidate = copy.deepcopy(self.settings)
        candidate.layout = layout
        _validate_settings(candidate)
        job_id = body.get("job_id", "")
        if job_id:
            job = self.job(job_id)
            segment = next((s for s in job.segments if s.seg_id == body.get("seg_id")), None)
            if segment is None:
                raise ValueError("Không tìm thấy đoạn để xem trước.")
            segment = copy.deepcopy(segment)
        else:
            segment = SegmentItem("preview", True, "threads_studio", raw_text="Biến cuộc trò chuyện thành câu chuyện.\nChọn một đoạn để xem trước thẻ Threads.", likes=7800, replies=223, reposts=866)
        if "raw_text" in body:
            if not isinstance(body["raw_text"], str) or len(body["raw_text"]) > 50000:
                raise ValueError("Nội dung thẻ quá dài.")
            segment.raw_text = body["raw_text"]
        image = render_threads_card_qimage(segment, layout, base_width=920)
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise RuntimeError("Không tạo được ảnh thẻ.")
        return web.Response(body=bytes(buffer.data()), content_type="image/png")

    def save_job(self, body: dict[str, Any]) -> VideoJob:
        job = self.job(str(body.get("job_id", "")), editable=True)
        self.pipeline._restore_progress(job)
        previous = [(seg.seg_id, seg.raw_text, seg.spoken_text, seg.voice_id, seg.enabled) for seg in job.segments]
        previous_layout = job.layout.to_dict()
        segments = body.get("segments")
        updates: list[tuple[SegmentItem, dict]] = []
        if segments is not None:
            known = {seg.seg_id: seg for seg in job.segments}
            if not isinstance(segments, list) or len(segments) != len(known):
                raise ValueError("Phải giữ đủ các đoạn trong job.")
            seen = set()
            for item in segments:
                if not isinstance(item, dict) or item.get("seg_id") not in known or item["seg_id"] in seen:
                    raise ValueError("ID đoạn không hợp lệ hoặc bị trùng.")
                seen.add(item["seg_id"])
                patch = {key: item[key] for key in ("raw_text", "spoken_text", "voice_id", "enabled") if key in item}
                for key, value in patch.items():
                    if (key == "enabled" and type(value) is not bool) or (key != "enabled" and (not isinstance(value, str) or len(value) > 50000)):
                        raise ValueError("Nội dung đoạn không hợp lệ.")
                voice_id = patch.get("voice_id", "")
                if voice_id and (voice_id.partition(":")[0] not in {"edge", "capcut", "vieneu"} or not voice_id.partition(":")[2]):
                    raise ValueError("ID giọng đọc không hợp lệ.")
                updates.append((known[item["seg_id"]], patch))
        layout = copy.deepcopy(job.layout)
        _patch_config(layout, body.get("layout", {}))
        candidate = copy.deepcopy(self.settings)
        candidate.layout = layout
        _validate_settings(candidate)
        for segment, patch in updates:
            for key, value in patch.items():
                setattr(segment, key, value)
        if segments is not None:
            job.segments = [segment for segment, _ in updates]
            job.selected_voices = list(dict.fromkeys([*job.selected_voices, *(seg.voice_id for seg in job.segments if seg.voice_id)]))
        job.layout = layout
        current = [(seg.seg_id, seg.raw_text, seg.spoken_text, seg.voice_id, seg.enabled) for seg in job.segments]
        if current != previous or job.layout.to_dict() != previous_layout:
            for key in ("approved", "meme_input", "composed", "legacy_audio"):
                job.checkpoint.pop(key, None)
        job.save_checkpoint()
        return job

    async def action(self, request: web.Request) -> web.Response:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("Yêu cầu phải là JSON object.")
        name = body.get("action")
        result: Any = None
        if name == "settings":
            await self.save_settings(body.get("settings", {}))
            result = self.settings.to_dict()
        elif name == "ai_metadata":
            provider = body.get("provider")
            if provider not in {"codex", "antigravity", "offline"}:
                raise ValueError("Provider metadata không hợp lệ.")

            async def metadata() -> dict:
                previous = self.ai_metadata.get(provider, {})
                self.ai_metadata[provider] = {**previous, "loading": True}
                try:
                    data = await asyncio.to_thread(read_cli_metadata, provider, include_models=True)
                    self.ai_metadata[provider] = {**data, "loading": False}
                    return data
                finally:
                    self.ai_metadata[provider]["loading"] = False

            result = {"task_id": self.start_task("Đọc model và hạn mức AI", metadata, key=f"ai_metadata_{provider}")}
        elif name == "demo":
            result = sample_video1_script()
        elif name == "quota_terminal":
            if body.get("provider") != "antigravity" or sys.platform != "win32":
                raise ValueError("Mở agy trong terminal và gõ /usage để xem hạn mức Antigravity.")
            subprocess.Popen(cli_command("antigravity"), cwd=os.environ.get("TEMP", str(project_root())),
                             env=cli_environment(), creationflags=subprocess.CREATE_NEW_CONSOLE)
            result = "Đã mở Antigravity CLI. Gõ /usage rồi Enter để xem quota 5 giờ và theo tuần. App chưa đọc tự động được bảng này."
        elif name == "enqueue":
            raw = str(body.get("text", "")).strip()
            if not raw:
                raise ValueError("Hãy nhập URL Threads hoặc kịch bản.")
            inputs = [part.strip() for part in (raw.split("===") if body.get("mode") == "manual" else raw.splitlines()) if part.strip()]
            if not 1 <= len(inputs) <= 50:
                raise ValueError("Mỗi lô nhận từ 1 đến 50 bài.")
            urls = body.get("mode") != "manual"
            if urls:
                for value in inputs:
                    parsed = urlsplit(value)
                    if parsed.scheme != "https" or parsed.hostname not in {"threads.com", "www.threads.com", "threads.net", "www.threads.net"} or parsed.username or parsed.port:
                        raise ValueError("Hãy dùng URL https://www.threads.com/... hoặc chuyển sang Kịch bản nhập tay.")
            await self.save_settings(body.get("settings", {}))
            cfg = self.settings
            jobs = [VideoJob(source_url=value if urls else "", manual_script="" if urls else value,
                             require_review=cfg.require_review_default, comment_mode=cfg.comment_mode,
                             comment_sort=cfg.comment_sort, max_comments=cfg.max_comments, voice_speed=cfg.voice_speed,
                             voice_assign_mode=cfg.voice_assign_mode, selected_voices=list(cfg.selected_voices),
                             ai_provider=cfg.ai_provider, ai_model=cfg.codex_model if cfg.ai_provider == "codex" else cfg.antigravity_model,
                             layout=copy.deepcopy(cfg.layout), media=copy.deepcopy(cfg.media)) for value in inputs]
            if self.database:
                await asyncio.to_thread(self.database.save_jobs, [asdict(job) for job in jobs])
            self.pipeline.enqueue_jobs(jobs)
            result = [job.job_id for job in jobs]
        elif name in {"save_job", "approve", "normalize", "reselect"}:
            job = self.save_job(body)
            if name == "approve":
                if not job.enabled_segments:
                    raise ValueError("Cần bật ít nhất một đoạn có nội dung trước khi xuất video.")
                self.pipeline.approve_and_render(job.job_id)
            elif name == "reselect":
                if body.get("comment_sort") not in {"likes", "replies", "reposts", "quotes"}:
                    raise ValueError("Tiêu chí bình luận không hợp lệ.")
                count = body.get("max_comments", 6)
                if type(count) is not int or not 1 <= count <= 25:
                    raise ValueError("Số bình luận phải từ 1 đến 25.")
                if not self.pipeline.reselect_comments(job.job_id, body["comment_sort"], count):
                    raise ValueError("Job chưa có pool bình luận để chọn lại.")
            elif name == "normalize":
                segments = copy.deepcopy(job.segments)
                provider = self.settings.ai_provider
                model = self.settings.codex_model if provider == "codex" else self.settings.antigravity_model
                self.busy_jobs.add(job.job_id)

                async def normalize() -> None:
                    try:
                        await asyncio.to_thread(capture_quota_before, job, provider)
                        with track_ai_usage(job, "Chuẩn hóa lại trong Inspector"):
                            mapping = await asyncio.to_thread(normalize_segments_batch, segments, ai_provider=provider,
                                                              ai_model=model, include_emotion_cues=any(v.startswith("vieneu:") for v in job.selected_voices))
                        if job.stage in EDITABLE_STAGES and job.job_id not in self.pipeline._cancelled:
                            for segment in job.segments:
                                segment.spoken_text = mapping[segment.seg_id]
                            job.checkpoint["normalized"] = True
                            for key in ("approved", "meme_input", "composed", "legacy_audio"):
                                job.checkpoint.pop(key, None)
                    finally:
                        job.save_checkpoint()
                        write_usage(job)
                        self.busy_jobs.discard(job.job_id)

                result = {"task_id": self.start_task("Chuẩn hóa lời đọc", normalize)}
        elif name == "resume":
            job = self.job(str(body.get("job_id", "")))
            if job.job_id in self.busy_jobs or not self.pipeline.resume_job(job.job_id):
                raise web.HTTPConflict(text="Job chưa thể tiếp tục; chờ tác vụ cũ dừng hẳn hoặc chọn job đã dừng/lỗi.")
            result = job.job_id
        elif name == "approve_all":
            result = 0
            for jid in list(self.pipeline.job_order):
                job = self.pipeline.jobs[jid]
                if job.stage == "awaiting_review" and jid not in self.busy_jobs and job.enabled_segments:
                    self.pipeline.approve_and_render(jid)
                    result += 1
        elif name == "cancel":
            self.pipeline.cancel_job(self.job(str(body.get("job_id", ""))).job_id)
        elif name == "cancel_all":
            self.pipeline.cancel_all_active()
        elif name == "voices":
            async def voices() -> int:
                catalog = await asyncio.to_thread(TTSRouter.available_voices)
                self.voices = [asdict(v) for v in catalog]
                return len(self.voices)
            result = {"task_id": self.start_task("Tải danh sách giọng", voices, key="voices")}
        elif name == "preview_voice":
            text, voice_id = body.get("text", ""), body.get("voice_id", "")
            if not isinstance(text, str) or not text.strip() or len(text) > 5000 or not isinstance(voice_id, str) or ":" not in voice_id:
                raise ValueError("Nhập lời đọc (tối đa 5.000 ký tự) và chọn giọng.")
            router = self.pipeline._make_tts_router()
            output = self.settings.user_data_dir() / f"preview_voice_{secrets.token_hex(6)}.wav"
            speed = self.settings.voice_speed

            async def preview() -> dict:
                await asyncio.to_thread(router.synthesize_single, text, voice_id, output, speed=speed)
                return {"audio_url": self.file_url(output)}
            result = {"task_id": self.start_task("Nghe thử giọng đọc", preview, key="preview_voice")}
        elif name == "login":
            provider = body.get("provider")
            if provider == "threads":
                profile = self.threads_profile_dir

                async def login() -> str:
                    self.threads_login = {"state": "waiting"}
                    try:
                        await asyncio.to_thread(open_threads_login_session, profile)
                    except Exception as exc:
                        self.threads_login = {"state": "failed", "message": str(exc)}
                        raise
                    message = "Edge đã đóng. Hồ sơ của app được giữ trên máy và sẽ được dùng lại khi đọc Threads."
                    self.threads_login = {"state": "closed", "message": message}
                    return message
                result = {"task_id": self.start_task("Đăng nhập Threads", login, key="login_threads")}
            elif provider in {"codex", "antigravity"}:
                if sys.platform != "win32":
                    raise ValueError("Chạy codex login hoặc agy trong terminal để đăng nhập.")
                command = cli_command(provider)
                if provider == "codex":
                    command += ["-c", 'forced_login_method="chatgpt"', "login"]
                subprocess.Popen(command, cwd=os.environ.get("TEMP", str(project_root())),
                                 env=cli_environment(), creationflags=subprocess.CREATE_NEW_CONSOLE)
                result = "Đã mở cửa sổ CLI. Hoàn tất đăng nhập trong cửa sổ đó; app chưa xác minh phiên đăng nhập."
            else:
                raise ValueError("Provider đăng nhập không hợp lệ.")
        elif name in {"catalog", "scan_sounds", "update_sound", "update_emotion_group"}:
            folder = str(body.get("folder", self.settings.media.meme_sound_dir))
            sound_id = str(body.get("sound_id", ""))
            if name == "update_sound" and (type(body.get("enabled")) is not bool or not isinstance(body.get("description"), str)):
                raise ValueError("Mô tả/trạng thái sound không hợp lệ.")

            async def catalog() -> dict:
                if name == "scan_sounds":
                    root = sound_library_root(folder)
                    if root == sound_library_root():
                        root.mkdir(parents=True, exist_ok=True)
                    await asyncio.to_thread(scan_sound_library, folder)
                elif name == "update_sound":
                    await asyncio.to_thread(update_sound, folder, sound_id, enabled=body["enabled"], description=body["description"], emotion_group=body.get("emotion_group"))
                elif name == "update_emotion_group":
                    await asyncio.to_thread(update_emotion_group, folder, body.get("name"), enabled=body.get("enabled"), description=body.get("description"))
                data = await asyncio.to_thread(load_sound_catalog_data, folder)
                for item in data["sounds"]:
                    try:
                        item["audio_url"] = self.file_url(resolve_sound_file(folder, item))
                    except RuntimeError:
                        item["audio_url"] = ""
                return {**data, "folder": folder}
            result = {"task_id": self.start_task("Đọc kho meme sound", catalog, key="catalog")}
        elif name == "preset_save":
            preset_name = str(body.get("name", "")).strip()
            if not preset_name or len(preset_name) > 120:
                raise ValueError("Nhập tên preset (tối đa 120 ký tự).")
            await self.save_settings(body.get("settings", {}))
            cfg = self.settings
            preset = PresetProfile(name=preset_name, comment_mode=cfg.comment_mode, comment_sort=cfg.comment_sort,
                                   max_comments=cfg.max_comments, voice_speed=cfg.voice_speed, voice_assign_mode=cfg.voice_assign_mode,
                                   selected_voices=list(cfg.selected_voices), layout=copy.deepcopy(cfg.layout), media=copy.deepcopy(cfg.media))
            cfg.presets.append(preset)
            try:
                if self.database:
                    await asyncio.to_thread(self.database.save_settings, cfg.to_dict())
                cfg.save()
            except Exception:
                cfg.presets.pop()
                raise
            result = cfg.to_dict()
        elif name == "open_outputs":
            if sys.platform != "win32":
                raise ValueError("Mở thư mục output bằng trình quản lý file trên máy.")
            os.startfile(str(self.settings.resolved_output_root()))
        elif name == "shutdown":
            self.stopped.set()
        else:
            raise ValueError("Thao tác không hợp lệ.")
        if name in {"save_job", "approve", "reselect", "approve_all", "cancel", "cancel_all", "resume"}:
            await self._persist_jobs()
        return web.json_response({"result": result})

    async def serve(self, *, open_browser: bool = True) -> None:
        runner = web.AppRunner(self.app, access_log=None)
        database_worker = None
        try:
            try:
                await _prepare_port(self.port)
            except (subprocess.SubprocessError, ValueError) as exc:
                raise RuntimeError(f"Chưa kiểm tra/giải phóng được cổng {self.port}. Thử chạy lại lệnh khởi động.") from exc
            if self.database:
                await asyncio.to_thread(self._initialize_database)
                database_worker = asyncio.create_task(self._database_worker())
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", self.port)
            await site.start()
            for job in list(self.pipeline.jobs.values()):
                if job.resume_on_startup:
                    self.pipeline.resume_job(job.job_id)
            url = f"http://127.0.0.1:{self.port}"
            logger.info("Threads Studio Pro · %s · Ctrl+C để dừng", url)
            if open_browser:
                await asyncio.to_thread(webbrowser.open, url)
            await self.stopped.wait()
        finally:
            self.stopped.set()
            self.pipeline.pause_for_restart()
            if database_worker:
                try:
                    await self._persist_jobs()
                except Exception:
                    logger.error("Chưa lưu được trạng thái tạm dừng vào PostgreSQL. Checkpoint local vẫn được giữ.")
            await runner.cleanup()
            if self.running:
                logger.info("Đang chờ các thao tác nền kết thúc; đóng cửa sổ Edge đăng nhập nếu còn mở.")
                await asyncio.gather(*self.running, return_exceptions=True)
            await asyncio.to_thread(self.pipeline._executor.shutdown, wait=True, cancel_futures=True)
            for job in self.pipeline.jobs.values():
                job.save_checkpoint()
            if database_worker:
                await database_worker
                try:
                    await self._persist_jobs()
                except Exception:
                    logger.error("Chưa lưu được trạng thái cuối vào PostgreSQL. Output local vẫn được giữ.")
            logger.removeHandler(self)


def run_web_studio(settings: AppSettings, *, port: int = 8000, open_browser: bool = True) -> int:
    # QImage/QPainter and the existing pipeline retain Qt; no desktop window is created.
    qt_app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(["threadstudio-web"])
    qt_app.setApplicationName("Threads Studio Pro")
    studio = StudioWebServer(settings, port=port)
    try:
        asyncio.run(studio.serve(open_browser=open_browser))
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        logger.error("Không mở được web local: %s. Thử --port 8001 nếu cổng đang được sử dụng.", exc)
        return 1
    except (PostgreSQLError, RuntimeError, ValueError) as exc:
        logger.error("Không khởi động được studio: %s", exc)
        return 1
    return 0
