"""PostgreSQL metadata storage; media files always remain on the local filesystem."""
from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .config import AppSettings, project_root
from .models import LayoutConfig, MediaConfig, SegmentItem, VideoJob


class StudioDatabase:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = {key: config[key] for key in ("host", "port", "dbname", "user", "password") if key in config}
        self.schema = config.get("schema", "thread")
        if not isinstance(self.schema, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.schema):
            raise ValueError("Tên schema PostgreSQL không hợp lệ.")
        self.connected = False

    @classmethod
    def load(cls) -> StudioDatabase | None:
        path = project_root() / "user_data" / "database.json"
        if not path.is_file():
            return None
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def connect(self) -> psycopg.Connection:
        try:
            connection = psycopg.connect(**self.config, connect_timeout=3, options="-c statement_timeout=10000 -c lock_timeout=3000", row_factory=dict_row)
        except psycopg.Error:
            self.connected = False
            raise
        self.connected = True
        return connection

    def table(self, name: str) -> sql.Identifier:
        return sql.Identifier(self.schema, name)

    def status(self) -> dict[str, Any]:
        return {"enabled": True, "connected": self.connected, "schema": self.schema}

    def initialize(self) -> None:
        with self.connect() as connection:
            if not connection.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (self.schema,)).fetchone():
                raise RuntimeError(f"Không tìm thấy schema PostgreSQL {self.schema}.")
            connection.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id smallint PRIMARY KEY CHECK (id = 1),
                    payload jsonb NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
            """).format(self.table("settings")))
            connection.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    job_id text PRIMARY KEY,
                    source_url text NOT NULL DEFAULT '',
                    title_slug text NOT NULL,
                    stage text NOT NULL,
                    video_path text NOT NULL DEFAULT '',
                    snapshot jsonb NOT NULL,
                    created_at timestamp NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
            """).format(self.table("video_jobs")))
            connection.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    job_id text NOT NULL REFERENCES {} (job_id),
                    seg_id text NOT NULL,
                    position integer NOT NULL,
                    raw_text text NOT NULL DEFAULT '',
                    spoken_text text NOT NULL DEFAULT '',
                    voice_id text NOT NULL DEFAULT '',
                    enabled boolean NOT NULL DEFAULT true,
                    snapshot jsonb NOT NULL,
                    PRIMARY KEY (job_id, seg_id)
                )
            """).format(self.table("segments"), self.table("video_jobs")))
        self.connected = True

    def load_settings(self) -> dict[str, Any] | None:
        with self.connect() as connection:
            return connection.execute(sql.SQL("SELECT payload, updated_at FROM {} WHERE id = 1").format(self.table("settings"))).fetchone()

    def save_settings(self, payload: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(sql.SQL("""
                INSERT INTO {} (id, payload) VALUES (1, %s)
                ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
            """).format(self.table("settings")), (Jsonb(payload),))
        self.connected = True

    def save_jobs(self, snapshots: list[dict[str, Any]], *, import_only: bool = False) -> int:
        inserted = 0
        with self.connect() as connection:
            for job in snapshots:
                snapshot = {key: value for key, value in job.items() if key != "segments"}
                snapshot["segment_order"] = [segment["seg_id"] for segment in job["segments"]]
                conflict = sql.SQL("DO NOTHING") if import_only else sql.SQL("""DO UPDATE SET
                    source_url = EXCLUDED.source_url, title_slug = EXCLUDED.title_slug, stage = EXCLUDED.stage,
                    video_path = EXCLUDED.video_path, snapshot = EXCLUDED.snapshot, updated_at = now()""")
                row = connection.execute(sql.SQL("""
                    INSERT INTO {} (job_id, source_url, title_slug, stage, video_path, snapshot, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (job_id) {} RETURNING job_id
                """).format(self.table("video_jobs"), conflict),
                    (job["job_id"], job["source_url"], job["title_slug"], job["stage"], job["output_mp4"], Jsonb(snapshot), job["created_at"])).fetchone()
                if row is None:
                    continue
                inserted += 1
                for position, segment in enumerate(job["segments"]):
                    connection.execute(sql.SQL("""
                        INSERT INTO {} (job_id, seg_id, position, raw_text, spoken_text, voice_id, enabled, snapshot)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (job_id, seg_id) DO UPDATE SET position = EXCLUDED.position,
                        raw_text = EXCLUDED.raw_text, spoken_text = EXCLUDED.spoken_text,
                        voice_id = EXCLUDED.voice_id, enabled = EXCLUDED.enabled, snapshot = EXCLUDED.snapshot
                    """).format(self.table("segments")),
                        (job["job_id"], segment["seg_id"], position, segment["raw_text"], segment["spoken_text"],
                         segment["voice_id"], segment["enabled"], Jsonb(segment)))
        self.connected = True
        return inserted

    def load_jobs(self) -> list[VideoJob]:
        with self.connect() as connection:
            rows = connection.execute(sql.SQL("SELECT snapshot FROM {} ORDER BY created_at, job_id").format(self.table("video_jobs"))).fetchall()
            segment_rows = connection.execute(sql.SQL("SELECT job_id, seg_id, snapshot FROM {}").format(self.table("segments"))).fetchall()
        segments = {(row["job_id"], row["seg_id"]): row["snapshot"] for row in segment_rows}
        jobs = []
        known = {item.name for item in fields(VideoJob)}
        for row in rows:
            data = row["snapshot"]
            order = data.pop("segment_order", [])
            local_segments = None
            if data.get("output_dir"):
                try:
                    local = json.loads((Path(data["output_dir"]) / "job-checkpoint.json").read_text(encoding="utf-8"))
                    if (local.get("job_id") == data["job_id"] and isinstance(local.get("segments"), list)
                            and local.get("checkpoint_at", 0) > data.get("checkpoint_at", 0)):
                        local_segments = local["segments"]
                        data = local
                except (OSError, ValueError, TypeError, AttributeError):
                    pass
            data = {key: value for key, value in data.items() if key in known}
            data["layout"] = LayoutConfig.from_dict(data.get("layout", {}))
            data["media"] = MediaConfig.from_dict(data.get("media", {}))
            data["segments"] = [SegmentItem.from_dict(item) for item in local_segments] if local_segments is not None else [SegmentItem.from_dict(segments[(data["job_id"], seg_id)]) for seg_id in order]
            job = VideoJob(**data)
            if job.stage in {"queued", "scraping", "normalizing", "synthesizing", "rendering"}:
                job.stage = "cancelled"
                job.resume_on_startup = True
                job.error_message = ""
                job.status_detail = "Phiên trước bị gián đoạn · Sẽ tự tiếp tục từ tiến độ đã lưu"
            jobs.append(job)
        self.connected = True
        return jobs

    def import_outputs(self, settings: AppSettings) -> tuple[int, int]:
        """Idempotently import recognized job folders without reading any video bytes."""
        root = Path(settings.output_root) if settings.output_root else project_root() / "output"
        if not root.is_dir():
            return 0, 0
        with self.connect() as connection:
            existing = {row["job_id"] for row in connection.execute(sql.SQL("SELECT job_id FROM {}").format(self.table("video_jobs")))}
        imported, skipped = 0, 0
        for folder in sorted(root.iterdir()):
            match = re.fullmatch(r"threads-(\d{8})-(\d{6})-([0-9a-f]{8})", folder.name)
            if not match or not folder.is_dir() or match[3] in existing:
                continue
            source = folder / "content-reviewed.json"
            if not source.is_file():
                source = folder / "content.json"
            if not source.is_file():
                continue
            try:
                segments = [SegmentItem.from_dict(item) for item in json.loads(source.read_text(encoding="utf-8"))]
                if any(not all(isinstance(getattr(segment, key), str) for key in ("raw_text", "spoken_text", "voice_id")) for segment in segments):
                    raise ValueError("Metadata đoạn phải chứa nội dung văn bản.")
                for filename in ("translation-reviewed.json", "translation.json"):
                    path = folder / filename
                    if path.is_file():
                        mapping = json.loads(path.read_text(encoding="utf-8"))
                        for segment in segments:
                            segment.spoken_text = str(mapping.get(segment.seg_id, segment.spoken_text))
                        break
                layout_path = folder / "v2-layout.json"
                layout = LayoutConfig.from_dict(json.loads(layout_path.read_text(encoding="utf-8"))) if layout_path.is_file() else LayoutConfig.from_dict(settings.layout.to_dict())
                timeline_path = folder / "timeline.json"
                if timeline_path.is_file():
                    timeline = {item["seg_id"]: item for item in json.loads(timeline_path.read_text(encoding="utf-8"))}
                    for segment in segments:
                        for key in ("audio_wav_path", "card_png_path", "start_sec", "end_sec", "duration_sec", "voice_id"):
                            if key in timeline.get(segment.seg_id, {}):
                                setattr(segment, key, timeline[segment.seg_id][key])
                videos = sorted(path for path in folder.glob("*.mp4") if path.is_file())
                video = videos[0] if videos else None
                created_at = datetime.strptime(match[1] + match[2], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                job = VideoJob(job_id=match[3], title_slug=video.stem if video else folder.name,
                               created_at=created_at,
                               stage="completed" if video else "awaiting_review", progress_pct=100 if video else 45,
                               status_detail="Đã nhập từ output local" if video else "Đã nhập kịch bản local · Chờ duyệt",
                               output_dir=str(folder.resolve()), output_mp4=str(video.resolve()) if video else "",
                               segments=segments, layout=layout, media=MediaConfig.from_dict(settings.media.to_dict()),
                               selected_voices=list(settings.selected_voices),
                               total_duration_sec=max((segment.end_sec for segment in segments), default=0))
                media_path = folder / "selected-media.json"
                if media_path.is_file():
                    media = json.loads(media_path.read_text(encoding="utf-8"))
                    job.media.bg_video_path = str(media.get("background", ""))
                    job.media.bg_fit = str(media.get("background_fit", "cover"))
                usage_path = folder / "ai-usage.json"
                if usage_path.is_file():
                    usage = json.loads(usage_path.read_text(encoding="utf-8"))
                    if isinstance(usage, dict):
                        job.ai_usage = {key: value for key, value in usage.items() if key != "summary"}
                candidate_path = folder / "comment-candidates.json"
                if candidate_path.is_file():
                    candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
                    job.comment_candidates = candidates.get("posts", [])
                    job.comment_coverage = candidates.get("coverage", {})
                imported += self.save_jobs([asdict(job)], import_only=True)
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                skipped += 1
        return imported, skipped
