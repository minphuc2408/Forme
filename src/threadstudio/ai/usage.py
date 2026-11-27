"""Per-job CLI usage without storing prompts, responses or authentication data."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Iterator

from ..core.models import VideoJob

_ACTIVE_USAGE: ContextVar[tuple[VideoJob, str] | None] = ContextVar("threadstudio_ai_usage", default=None)
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens", "total_tokens")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def track_ai_usage(job: VideoJob, operation: str) -> Iterator[None]:
    token = _ACTIVE_USAGE.set((job, operation))
    try:
        yield
    finally:
        _ACTIVE_USAGE.reset(token)


def record_usage(record: dict[str, Any]) -> None:
    active = _ACTIVE_USAGE.get()
    if active is not None:
        job, operation = active
        job.ai_usage.setdefault("calls", []).append({**record, "operation": operation})


def token_counts(usage: Any, provider: str) -> dict[str, int | None]:
    usage = usage if isinstance(usage, dict) else {}
    aliases = {"cached_input_tokens": "cache_read_tokens", "reasoning_tokens": "thinking_tokens"} if provider == "antigravity" else {"reasoning_tokens": "reasoning_output_tokens"}
    result: dict[str, int | None] = {}
    for field in TOKEN_FIELDS:
        value = usage.get(aliases.get(field, field))
        result[field] = value if type(value) is int and value >= 0 else None
    if provider == "codex" and result["input_tokens"] is not None and result["output_tokens"] is not None:
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    return result


def usage_summary(usage: dict[str, Any]) -> dict[str, Any]:
    calls = usage.get("calls", [])
    summary: dict[str, Any] = {"calls": len(calls), "failed_calls": sum(call.get("status") == "failed" for call in calls),
                               "reported_calls": sum(call.get("input_tokens") is not None and call.get("output_tokens") is not None for call in calls)}
    for key in TOKEN_FIELDS:
        values = [call[key] for call in calls if type(call.get(key)) is int]
        summary[key] = sum(values) if values else None
    return summary


def write_usage(job: VideoJob) -> None:
    if job.output_dir and job.ai_usage:
        path = Path(job.output_dir) / "ai-usage.json"
        try:
            path.write_text(json.dumps({**job.ai_usage, "summary": usage_summary(job.ai_usage)}, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            logging.getLogger("threadstudio").warning("Chưa ghi được báo cáo AI cho job #%s; số liệu vẫn ở metadata job.", job.job_id)
