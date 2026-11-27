"""Stage-Pipelined Multi-Threaded Batch Orchestrator for Threads Studio Pro."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import hashlib
import json
import logging
from pathlib import Path
import threading

from fluent_blue.compatibility.qt import QObject, QtCore

from ..ai.text_normalizer import normalize_segments_batch
from ..ai.cli_metadata import capture_quota_after, capture_quota_before
from ..ai.usage import track_ai_usage, write_usage
from ..ai.meme_selector import apply_meme_timeline, select_meme_sounds
from ..render.card_renderer import render_cards_for_job
from ..render.ffmpeg_compositor import compose_final_video
from ..scrapers.threads_scraper import parse_manual_script, scrape_threads_url
from ..tts.router import TTSRouter
from .config import AppSettings
from .models import JobStage, VideoJob

Signal = getattr(QtCore, "pyqtSignal", None) or getattr(QtCore, "Signal")
logger = logging.getLogger("threadstudio")


class BatchPipelineManager(QObject):
    """Coordinates concurrent multi-stage video jobs without blocking the Qt main thread."""

    job_changed = Signal(str)           # job_id
    review_ready = Signal(str)          # job_id
    job_finished = Signal(str, str)     # job_id, mp4_path
    counts_changed = Signal()

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.jobs: dict[str, VideoJob] = {}
        self.job_order: list[str] = []
        self._cancelled: set[str] = set()
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()

        # Main task coordinator pool; stage semaphores prevent resource thrashing
        self._executor = ThreadPoolExecutor(max_workers=12, thread_name_prefix="ts-worker")
        self._rebuild_semaphores()

    def _rebuild_semaphores(self) -> None:
        self._scrape_sem = threading.Semaphore(max(1, self.settings.max_scrape_workers))
        self._ai_sem = threading.Semaphore(max(1, self.settings.max_ai_workers))
        self._tts_sem = threading.Semaphore(max(1, self.settings.max_tts_workers))
        self._render_sem = threading.Semaphore(max(1, self.settings.max_render_workers))

    def enqueue_jobs(self, jobs: list[VideoJob]) -> None:
        with self._lock:
            for job in jobs:
                self.jobs[job.job_id] = job
                self.job_order.append(job.job_id)
        self.counts_changed.emit()
        for job in jobs:
            self.job_changed.emit(job.job_id)
            self._submit(job.job_id, self._run_phase_ingest)

    def _submit(self, job_id: str, work) -> None:
        self._futures[job_id] = self._executor.submit(work, job_id)

    def is_running(self, job_id: str) -> bool:
        future = self._futures.get(job_id)
        return future is not None and not future.done()

    def can_resume(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        return bool(job and job.stage in {JobStage.CANCELLED.value, JobStage.FAILED.value}
                    and not self.is_running(job_id) and (job.segments or job.manual_script.strip() or job.source_url))

    def resume_job(self, job_id: str) -> bool:
        with self._lock:
            if not self.can_resume(job_id):
                return False
            job = self.jobs[job_id]
            self._cancelled.discard(job_id)
            job.resume_on_startup = False
            job.error_message = ""
            job.stage = JobStage.QUEUED.value
            job.status_detail = "Đang khôi phục tiến độ đã lưu..."
            self._submit(job_id, self._run_phase_resume)
        self.job_changed.emit(job_id)
        self.counts_changed.emit()
        return True

    def _restore_progress(self, job: VideoJob) -> None:
        if job.checkpoint or not job.segments:
            return
        job.checkpoint["scraped"] = True
        if job.progress_pct >= 45 and all(segment.spoken_text.strip() for segment in job.enabled_segments):
            job.checkpoint["normalized"] = True
        if job.output_dir:
            try:
                reviewed = json.loads((Path(job.output_dir) / "content-reviewed.json").read_text(encoding="utf-8"))
                keys = ("seg_id", "raw_text", "spoken_text", "voice_id", "enabled")
                current = [{key: getattr(segment, key) for key in keys} for segment in job.segments]
                if current == [{key: segment.get(key) for key in keys} for segment in reviewed]:
                    job.checkpoint.update(normalized=True, approved=True, legacy_audio=True)
            except (OSError, ValueError, TypeError, AttributeError):
                pass

    def _run_phase_resume(self, job_id: str) -> None:
        job = self.jobs[job_id]
        self._restore_progress(job)
        logger.info("[Job #%s] Tiếp tục từ tiến độ đã lưu; giữ nguyên nội dung đã duyệt và audio phù hợp.", job_id)
        self._run_phase_ingest(job_id)

    def approve_and_render(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if not job or job_id in self._cancelled or self.is_running(job_id):
            return
        if job.stage not in (JobStage.AWAITING_REVIEW.value, JobStage.FAILED.value):
            return
        job.stage = JobStage.SYNTHESIZING.value
        job.progress_pct = 50.0
        job.status_detail = "Đã duyệt — đang xếp hàng tạo giọng đọc..."
        job.error_message = ""
        job.checkpoint.update(scraped=True, normalized=True, approved=True)
        job.checkpoint.pop("composed", None)
        job.save_checkpoint()
        self.job_changed.emit(job_id)
        self.counts_changed.emit()
        self._submit(job_id, self._run_phase_render)

    def reselect_comments(self, job_id: str, comment_sort: str, max_comments: int) -> bool:
        job = self.jobs.get(job_id)
        if not job or job_id in self._cancelled or self.is_running(job_id) or not job.comment_candidates:
            return False
        if job.stage not in (JobStage.AWAITING_REVIEW.value, JobStage.FAILED.value):
            return False
        if comment_sort not in {"likes", "replies", "reposts", "quotes"}:
            return False
        job.comment_sort = comment_sort
        job.max_comments = max(1, min(25, max_comments))
        job.require_review = True
        job.checkpoint.clear()
        job.checkpoint["scraped"] = False
        job.error_message = ""
        job.stage = JobStage.QUEUED.value
        job.status_detail = "Đang chọn lại top bình luận từ dữ liệu đã tải..."
        job.save_checkpoint()
        self.job_changed.emit(job_id)
        self.counts_changed.emit()
        self._submit(job_id, self._run_phase_ingest)
        return True

    def approve_all_waiting(self) -> int:
        waiting = [
            jid for jid in self.job_order
            if self.jobs[jid].stage == JobStage.AWAITING_REVIEW.value
        ]
        for jid in waiting:
            self.approve_and_render(jid)
        return len(waiting)

    def cancel_job(self, job_id: str, *, resume_on_startup: bool = False) -> None:
        job = self.jobs.get(job_id)
        if job and job.stage not in (JobStage.COMPLETED.value, JobStage.FAILED.value, JobStage.CANCELLED.value):
            self._cancelled.add(job_id)
            job.resume_on_startup = resume_on_startup
            job.stage = JobStage.CANCELLED.value
            job.status_detail = "Tạm dừng · Tự tiếp tục khi mở lại backend" if resume_on_startup else "Đã dừng · Có thể tiếp tục tạo"
            self.job_changed.emit(job_id)
            self.counts_changed.emit()

    def pause_for_restart(self) -> None:
        for jid, job in list(self.jobs.items()):
            if job.stage in {"queued", "scraping", "normalizing", "synthesizing", "rendering"}:
                self.cancel_job(jid, resume_on_startup=True)

    def cancel_all_active(self) -> None:
        for jid, job in list(self.jobs.items()):
            if job.stage not in (JobStage.COMPLETED.value, JobStage.FAILED.value, JobStage.CANCELLED.value):
                self.cancel_job(jid)

    def active_count(self) -> int:
        active_stages = {
            JobStage.QUEUED.value,
            JobStage.SCRAPING.value,
            JobStage.NORMALIZING.value,
            JobStage.SYNTHESIZING.value,
            JobStage.RENDERING.value,
        }
        return sum(1 for j in self.jobs.values() if j.stage in active_stages)

    def review_count(self) -> int:
        return sum(1 for j in self.jobs.values() if j.stage == JobStage.AWAITING_REVIEW.value)

    # ---- Worker Phases ----

    def _run_phase_ingest(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if not job or job_id in self._cancelled:
            return

        try:
            out_dir = job.ensure_output_dir(self.settings.resolved_output_root())

            # Stage 1: Scrape or parse manual script
            if not job.checkpoint.get("scraped"):
                with self._scrape_sem:
                    if job_id in self._cancelled:
                        return
                    job.stage = JobStage.SCRAPING.value
                    job.progress_pct = 12.0
                    job.status_detail = "Đang lấy bài & bình luận..."
                    self.job_changed.emit(job_id)
                    self.counts_changed.emit()

                    if job.manual_script.strip():
                        logger.info("[Job #%s] Đang phân tích kịch bản nhập tay...", job_id)
                        slug, segments = parse_manual_script(job.manual_script)
                    else:
                        logger.info("[Job #%s] Đang cào Threads: %s", job_id, job.source_url)
                        slug, segments = scrape_threads_url(
                            job.source_url,
                            profile_dir=self.settings.user_data_dir() / "threads_edge_profile",
                            media_cache_dir=out_dir / "media-cache",
                            comment_mode=job.comment_mode,
                            max_comments=job.max_comments,
                            comment_sort=job.comment_sort,
                            candidates=job.comment_candidates,
                            coverage=job.comment_coverage,
                            cancelled=lambda: job_id in self._cancelled,
                        )

                    if job_id in self._cancelled:
                        return
                    job.title_slug = slug
                    job.segments = segments
                    if job.comment_candidates:
                        (out_dir / "comment-candidates.json").write_text(
                            json.dumps({"coverage": job.comment_coverage, "posts": job.comment_candidates}, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        logger.info("[Job #%s] Edge tải %d bình luận sau 10 lần cuộn; xếp hạng trong tập đã tải, không bảo đảm toàn bài.", job_id, len(job.comment_candidates) - 1)
                    (out_dir / "content.json").write_text(
                        json.dumps([s.to_dict() for s in segments], ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    job.checkpoint["scraped"] = True
                    job.save_checkpoint()
                    logger.info("[Job #%s] Thu thập xong %d đoạn (%s).", job_id, len(segments), slug)

            # Stage 2: Teencode & Vision OCR normalization + initial card preview render
            with self._ai_sem:
                if job_id in self._cancelled:
                    return
                if not job.checkpoint.get("normalized"):
                    job.stage = JobStage.NORMALIZING.value
                    job.progress_pct = 35.0
                    job.status_detail = "Đang bung từ viết tắt & dựng thẻ mẫu..."
                    self.job_changed.emit(job_id)

                    uses_vieneu = any(v.startswith("vieneu:") for v in job.selected_voices)
                    provider = job.ai_provider or self.settings.ai_provider
                    model = job.ai_model or (self.settings.codex_model if provider == "codex" else self.settings.antigravity_model)
                    job.ai_provider, job.ai_model = provider, model
                    capture_quota_before(job, provider)
                    with track_ai_usage(job, "Chuẩn hóa lời đọc"):
                        trans_map = normalize_segments_batch(
                            job.segments, ai_provider=provider, ai_model=model, include_emotion_cues=uses_vieneu,
                        )
                    (out_dir / "translation.json").write_text(
                        json.dumps(trans_map, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    job.checkpoint["normalized"] = True
                    job.save_checkpoint()

                router = self._make_tts_router()
                router.assign_voices(job.segments, job.selected_voices, job.voice_assign_mode)
                render_cards_for_job(job.segments, job.layout, out_dir / "cards")
                logger.info("[Job #%s] Đã chuẩn hóa lời đọc & tạo %d thẻ xem trước.", job_id, len(job.segments))

            if job_id in self._cancelled:
                return

            if job.require_review and not job.checkpoint.get("approved"):
                job.stage = JobStage.AWAITING_REVIEW.value
                job.progress_pct = 45.0
                job.status_detail = f"Chờ duyệt ({len(job.enabled_segments)} đoạn)"
                logger.info("[Job #%s] Chờ bạn duyệt nội dung trước khi xuất MP4.", job_id)
                self.job_changed.emit(job_id)
                self.counts_changed.emit()
                self.review_ready.emit(job_id)
            else:
                self._run_phase_render(job_id)

        except Exception as exc:
            if job_id in self._cancelled:
                return
            logger.error("[Job #%s] Lỗi khâu chuẩn bị: %s", job_id, exc)
            job.stage = JobStage.FAILED.value
            job.error_message = str(exc)
            job.status_detail = f"Lỗi: {exc}"
            capture_quota_after(job)
            self.job_changed.emit(job_id)
            self.counts_changed.emit()

        finally:
            if job_id in self._cancelled:
                job.stage = JobStage.CANCELLED.value
                job.status_detail = "Tạm dừng · Tự tiếp tục khi mở lại backend" if job.resume_on_startup else "Đã dừng · Có thể tiếp tục tạo"
            job.save_checkpoint()
            write_usage(job)

    def _run_phase_render(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if not job or job_id in self._cancelled:
            return

        try:
            out_dir = job.ensure_output_dir(self.settings.resolved_output_root())
            job.checkpoint["approved"] = True
            job.save_checkpoint()
            (out_dir / "content-reviewed.json").write_text(
                json.dumps([s.to_dict() for s in job.segments], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (out_dir / "translation-reviewed.json").write_text(
                json.dumps({s.seg_id: s.spoken_text for s in job.segments}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            # Use the final reviewed text, including edits/reordering, for reaction selection.
            meme_content = [{key: getattr(segment, key) for key in ("seg_id", "is_root_post", "username", "raw_text", "spoken_text", "parent_post_id", "enabled")} for segment in job.segments]
            meme_input = hashlib.sha256(json.dumps({"segments": meme_content, "media": job.media.to_dict()}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            if job.media.meme_sound_enabled:
                with self._ai_sem:
                    if job_id in self._cancelled:
                        return
                    job.status_detail = "Đang chọn meme sound theo nội dung đã duyệt..."
                    self.job_changed.emit(job_id)
                    if job.checkpoint.get("meme_input") != meme_input:
                        provider = job.ai_provider or self.settings.ai_provider
                        model = job.ai_model or (self.settings.codex_model if provider == "codex" else self.settings.antigravity_model)
                        capture_quota_before(job, provider)
                        with track_ai_usage(job, "Chọn meme sound sau duyệt"):
                            job.meme_sound_plan = select_meme_sounds(job.segments, job.media, provider=provider, model=model)
                        job.checkpoint["meme_input"] = meme_input
                        job.save_checkpoint()
            else:
                job.meme_sound_plan = {}

            # Stage 3: Final card render + multi-voice TTS synthesis
            with self._tts_sem:
                if job_id in self._cancelled:
                    return
                job.stage = JobStage.SYNTHESIZING.value
                job.progress_pct = 62.0
                job.status_detail = "Đang tạo giọng đọc AI đa luồng..."
                self.job_changed.emit(job_id)
                self.counts_changed.emit()

                router = self._make_tts_router()
                router.assign_voices(job.segments, job.selected_voices, job.voice_assign_mode)
                render_cards_for_job(job.segments, job.layout, out_dir / "styled-cards")

                total_dur = router.synthesize_segments_parallel(
                    job.segments,
                    out_dir / "audio",
                    speed=job.voice_speed,
                    max_workers=max(1, min(4, self.settings.max_tts_workers)),
                    reuse_existing=True,
                    reuse_legacy=bool(job.checkpoint.get("legacy_audio")),
                    cancelled=lambda: job_id in self._cancelled,
                    on_segment_done=job.save_checkpoint,
                )
                if job_id in self._cancelled:
                    return
                if job.meme_sound_plan:
                    total_dur = apply_meme_timeline(job.segments, job.meme_sound_plan)
                logger.info(
                    "[Job #%s] Hoàn tất TTS %d đoạn (tổng %.1fs).",
                    job_id,
                    len(job.enabled_segments),
                    total_dur,
                )

            # Stage 4: FFmpeg GPU/CPU Video Composition
            with self._render_sem:
                if job_id in self._cancelled:
                    return
                job.stage = JobStage.RENDERING.value
                job.progress_pct = 84.0
                width, height = job.layout.canvas_size
                job.status_detail = f"Đang ghép video {width}x{height} & trộn âm thanh..."
                self.job_changed.emit(job_id)

                if job.checkpoint.get("composed") and job.output_mp4 and Path(job.output_mp4).is_file():
                    final_mp4 = Path(job.output_mp4)
                else:
                    final_mp4 = compose_final_video(
                        job,
                        out_dir,
                        prefer_nvenc=self.settings.prefer_nvenc,
                    )
                    job.checkpoint["composed"] = True
                    job.save_checkpoint()

            if job_id in self._cancelled:
                return

            capture_quota_after(job)
            if job_id in self._cancelled:
                return
            job.stage = JobStage.COMPLETED.value
            job.progress_pct = 100.0
            job.status_detail = f"Hoàn tất ({job.total_duration_sec:.1f}s) → {final_mp4.name}"
            logger.info("[Job #%s] Xuất video thành công: %s", job_id, final_mp4)
            self.job_changed.emit(job_id)
            self.counts_changed.emit()
            self.job_finished.emit(job_id, str(final_mp4))

        except Exception as exc:
            if job_id in self._cancelled:
                return
            logger.error("[Job #%s] Lỗi khâu xuất video: %s", job_id, exc)
            job.stage = JobStage.FAILED.value
            job.error_message = str(exc)
            job.status_detail = f"Lỗi: {exc}"
            capture_quota_after(job)
            self.job_changed.emit(job_id)
            self.counts_changed.emit()

        finally:
            if job_id in self._cancelled:
                job.stage = JobStage.CANCELLED.value
                job.status_detail = "Tạm dừng · Tự tiếp tục khi mở lại backend" if job.resume_on_startup else "Đã dừng · Có thể tiếp tục tạo"
            job.save_checkpoint()
            write_usage(job)

    def _make_tts_router(self) -> TTSRouter:
        return TTSRouter(
            capcut_device_json=self.settings.capcut_device_json,
            vieneu_endpoint=self.settings.vieneu_endpoint,
            vieneu_clone_ref_audio=self.settings.vieneu_clone_ref_audio,
            vieneu_clone_ref_text=self.settings.vieneu_clone_ref_text,
        )

