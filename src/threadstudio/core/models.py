"""Domain models for batch jobs, scraped Threads content, layout geometry, and presets."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import json
import logging
import time
import uuid


class CommentMode(str, Enum):
    AUTHOR_ONLY = "author_only"
    TOP_LIKES_NO_AUTHOR = "top_likes_no_author"
    TOP_LIKES_WITH_AUTHOR = "top_likes_with_author"


class VoiceAssignMode(str, Enum):
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    SINGLE = "single"


class JobStage(str, Enum):
    QUEUED = "queued"
    SCRAPING = "scraping"
    NORMALIZING = "normalizing"
    AWAITING_REVIEW = "awaiting_review"
    SYNTHESIZING = "synthesizing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


STAGE_LABELS_VI: dict[str, str] = {
    JobStage.QUEUED.value: "Chờ xử lý",
    JobStage.SCRAPING.value: "Đang cào Threads",
    JobStage.NORMALIZING.value: "Chuẩn hóa từ viết tắt",
    JobStage.AWAITING_REVIEW.value: "Chờ duyệt nội dung",
    JobStage.SYNTHESIZING.value: "Đang tạo giọng & thẻ",
    JobStage.RENDERING.value: "Đang ghép MP4",
    JobStage.COMPLETED.value: "Hoàn tất",
    JobStage.FAILED.value: "Lỗi",
    JobStage.CANCELLED.value: "Đã dừng",
}


@dataclass
class LayoutConfig:
    """Normalized percentage coordinates on a portrait or landscape canvas."""

    aspect_ratio: str = "9:16"

    # Comment / Post Card
    card_x_pct: float = 50.0
    card_y_pct: float = 28.0
    card_scale_pct: float = 108.0
    card_radius_px: int = 0
    card_theme: str = "light"  # "light" | "dark"
    hide_username: bool = False

    # Secondary B-Roll / Meme Video
    sub_enabled: bool = True
    sub_x_pct: float = 50.0
    sub_y_pct: float = 64.0
    sub_w_pct: float = 86.0
    sub_h_pct: float = 26.0
    sub_radius_px: int = 0
    sub_fit: str = "cover"  # "cover" | "contain"

    @property
    def canvas_size(self) -> tuple[int, int]:
        return (1920, 1080) if self.aspect_ratio == "16:9" else (1080, 1920)

    @property
    def card_width_px(self) -> int:
        width, height = self.canvas_size
        return max(240, min(width - 24, int(round(880 * min(width, height) / 1080 * self.card_scale_pct / 100))))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LayoutConfig:
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class MediaConfig:
    """Folder paths and audio mixing levels."""

    bg_video_dir: str = ""
    bg_video_path: str = ""
    bg_random_start: bool = False
    bg_fit: str = "cover"
    sub_video_dir: str = ""
    bgm_dir: str = ""
    sfx_dir: str = ""
    bgm_enabled: bool = True
    bgm_volume_pct: int = 20
    sfx_enabled: bool = False
    sfx_volume_pct: int = 40
    meme_sound_dir: str = "assets/meme-sound"
    meme_sound_enabled: bool = False
    meme_sound_volume_pct: int = 40
    meme_sound_max_per_video: int = 3
    meme_sound_max_duration_sec: float = 6.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MediaConfig:
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class PresetProfile:
    """One-click workflow preset (e.g., Storytelling vs. Meme Comments)."""

    name: str
    comment_mode: str = CommentMode.TOP_LIKES_WITH_AUTHOR.value
    comment_sort: str = "likes"
    max_comments: int = 6
    voice_speed: float = 1.20
    voice_assign_mode: str = VoiceAssignMode.RANDOM.value
    selected_voices: list[str] = field(default_factory=list)
    media: MediaConfig = field(default_factory=MediaConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "comment_mode": self.comment_mode,
            "comment_sort": self.comment_sort,
            "max_comments": self.max_comments,
            "voice_speed": self.voice_speed,
            "voice_assign_mode": self.voice_assign_mode,
            "selected_voices": list(self.selected_voices),
            "media": self.media.to_dict(),
            "layout": self.layout.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresetProfile:
        return cls(
            name=data.get("name", "Mặc định"),
            comment_mode=data.get("comment_mode", CommentMode.TOP_LIKES_WITH_AUTHOR.value),
            comment_sort=data.get("comment_sort", "likes"),
            max_comments=int(data.get("max_comments", 6)),
            voice_speed=float(data.get("voice_speed", 1.20)),
            voice_assign_mode=data.get("voice_assign_mode", VoiceAssignMode.RANDOM.value),
            selected_voices=list(data.get("selected_voices", [])),
            media=MediaConfig.from_dict(data.get("media", {})),
            layout=LayoutConfig.from_dict(data.get("layout", {})),
        )


@dataclass
class SegmentItem:
    """One spoken & rendered card segment (index 0 = root post, 1..N = comments)."""

    seg_id: str
    is_root_post: bool
    username: str
    avatar_url: str = ""
    avatar_local: str = ""
    raw_text: str = ""
    spoken_text: str = ""
    image_urls: list[str] = field(default_factory=list)
    image_locals: list[str] = field(default_factory=list)
    likes: int | None = 0
    replies: int | None = 0
    reposts: int | None = 0
    quotes: int | None = None
    source_post_id: str = ""
    parent_post_id: str = ""
    timestamp: str = ""
    enabled: bool = True
    voice_id: str = ""
    card_png_path: str = ""
    audio_wav_path: str = ""
    audio_fingerprint: str = ""
    duration_sec: float = 0.0
    start_sec: float = 0.0
    end_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SegmentItem:
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class VideoJob:
    """Tracks one Threads-to-MP4 job across all pipeline stages."""

    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    source_url: str = ""
    manual_script: str = ""
    title_slug: str = "threads-video"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Per-job snapshot of settings so batch jobs stay isolated
    require_review: bool = True
    comment_mode: str = CommentMode.TOP_LIKES_WITH_AUTHOR.value
    comment_sort: str = "likes"
    max_comments: int = 6
    voice_speed: float = 1.20
    voice_assign_mode: str = VoiceAssignMode.RANDOM.value
    selected_voices: list[str] = field(default_factory=list)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    media: MediaConfig = field(default_factory=MediaConfig)

    # Runtime state
    ai_provider: str = ""
    ai_model: str = ""
    ai_usage: dict[str, Any] = field(default_factory=dict)
    checkpoint: dict[str, Any] = field(default_factory=dict)
    checkpoint_at: float = 0.0
    resume_on_startup: bool = False
    stage: str = JobStage.QUEUED.value
    progress_pct: float = 0.0
    status_detail: str = "Đang nằm trong hàng đợi"
    error_message: str = ""
    output_dir: str = ""
    output_mp4: str = ""
    total_duration_sec: float = 0.0
    segments: list[SegmentItem] = field(default_factory=list)
    comment_candidates: list[dict[str, Any]] = field(default_factory=list)
    comment_coverage: dict[str, Any] = field(default_factory=dict)
    meme_sound_plan: dict[str, dict[str, Any]] = field(default_factory=dict)

    def ensure_output_dir(self, base_output: Path) -> Path:
        if self.output_dir:
            out = Path(self.output_dir)
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            out = base_output / f"threads-{stamp}-{self.job_id}"
            self.output_dir = str(out)
        for sub in ("audio", "cards", "styled-cards", "clips", "video-phu", "media-cache"):
            (out / sub).mkdir(parents=True, exist_ok=True)
        return out

    def save_checkpoint(self) -> None:
        if self.output_dir:
            path = Path(self.output_dir) / "job-checkpoint.json"
            try:
                self.checkpoint_at = time.time()
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
                temporary.replace(path)
            except OSError:
                logging.getLogger("threadstudio").warning("Chưa ghi được checkpoint job #%s; PostgreSQL vẫn được thử lưu định kỳ.", self.job_id)

    @property
    def enabled_segments(self) -> list[SegmentItem]:
        return [s for s in self.segments if s.enabled and (s.spoken_text.strip() or s.raw_text.strip())]

