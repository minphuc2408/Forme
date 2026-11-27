"""Incremental local sound catalog built from imported audio and JSON descriptions."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unicodedata
from typing import Any

from ..render.ffmpeg_compositor import AUDIO_EXTS

_CATALOG_LOCK = threading.RLock()
EMOTION_GROUPS = {
    "Vui vẻ": "Hài hước, vui nhộn; dùng khi nội dung có sắc thái nhẹ nhàng.",
    "Bất ngờ": "Ngạc nhiên hoặc cú bẻ lái bất ngờ trong bình luận.",
    "Ngại ngùng": "Bối rối, ngượng ngùng hoặc tình huống khó xử.",
    "Mỉa mai": "Châm biếm, phản ứng mỉa mai; tránh hiểu nhầm lời nghiêm túc.",
    "Buồn": "Buồn hoặc thất vọng; không dùng để chế giễu nội dung đau buồn.",
    "Giận dữ": "Bực bội, phản bác hoặc phẫn nộ theo đúng ngữ cảnh.",
    "Đồng cảm": "An ủi, chia sẻ hoặc cảm động.",
}


def sound_library_root(folder: str = "") -> Path:
    path = Path(folder.strip().strip('"') or "assets/meme-sound").expanduser()
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / path
    return path.resolve()


def sound_name(value: str) -> str:
    value = re.sub(r"\s*\(\d+\)$", "", str(value or "")).lower().replace("đ", "d")
    value = unicodedata.normalize("NFKD", value)
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in value if not unicodedata.combining(c))).strip()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Không đọc được JSON kho meme: {path.name}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(value, handle, ensure_ascii=False, indent=2)
        except Exception:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_sound_catalog_data(folder: str) -> dict[str, Any]:
    data = _read_json(sound_library_root(folder) / "catalog.json", {"sounds": []})
    if not isinstance(data, dict) or not isinstance(data.get("sounds"), list):
        raise RuntimeError("catalog.json không đúng định dạng kho sound.")
    data.setdefault("emotion_groups", {name: {"description": description, "enabled": True} for name, description in EMOTION_GROUPS.items()})
    if not isinstance(data["emotion_groups"], dict) or any(not isinstance(group, dict) or not isinstance(group.get("description", ""), str) or type(group.get("enabled", True)) is not bool for group in data["emotion_groups"].values()):
        raise RuntimeError("Cấu hình nhóm cảm xúc trong catalog.json không hợp lệ.")
    return data


def load_sound_catalog(folder: str) -> list[dict[str, Any]]:
    return load_sound_catalog_data(folder)["sounds"]


def _load_sound_sources(root: Path) -> list[dict[str, Any]]:
    sources = []
    for path in sorted(root.rglob("*.json")):
        relative = path.relative_to(root)
        if path.name == "catalog.json" or "imports" in relative.parts or not path.resolve().is_relative_to(root):
            continue
        data = _read_json(path, [])
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise RuntimeError(f"{relative} phải chứa danh sách mô tả sound.")
        for source in data:
            if any(not isinstance(source.get(key, ""), str) for key in ("title", "description", "filename", "path")):
                raise RuntimeError(f"Mô tả/tên/đường dẫn trong {relative} phải là chuỗi.")
            filename = source.get("filename") or Path(source.get("path", "")).name
            if not filename:
                raise RuntimeError(f"Bản ghi trong {relative} thiếu filename/path.")
            candidate = (path.parent / (source.get("path") or filename)).resolve()
            sources.append({**source, "filename": filename, "metadata_file": relative.as_posix(),
                            "relative_file": candidate.relative_to(root).as_posix() if candidate.is_relative_to(root) else ""})
    return sources


def _sound_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
    )
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    if result.returncode or not data.get("streams") or not math.isfinite(duration) or duration <= 0:
        raise ValueError("File không có âm thanh/thời lượng hợp lệ.")
    return round(duration, 3)


def scan_sound_library(folder: str) -> list[dict[str, Any]]:
    root = sound_library_root(folder)
    if not root.is_dir():
        raise RuntimeError(f"Thư mục kho sound chưa tồn tại: {root}")
    with _CATALOG_LOCK:
        data = load_sound_catalog_data(str(root))
        old = {item["file"]: item for item in data["sounds"]}
        old_by_id = {item["id"]: item for item in old.values()}
        sources = _load_sound_sources(root)
        by_path: dict[str, list[int]] = {}
        by_filename: dict[str, list[int]] = {}
        aliases: dict[str, list[int]] = {}
        for index, source in enumerate(sources):
            by_path.setdefault(source["relative_file"].casefold(), []).append(index)
            by_filename.setdefault(source["filename"].casefold(), []).append(index)
            for name in (source.get("id", ""), source.get("title", ""), Path(source["filename"]).stem):
                if sound_name(name):
                    aliases.setdefault(sound_name(name), []).append(index)
        matched: set[int] = set()
        duplicates: list[dict[str, str]] = []
        sounds: list[dict[str, Any]] = []
        seen: dict[str, dict[str, Any]] = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTS or not path.resolve().is_relative_to(root):
                continue
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
            previous = old.get(relative, {})
            if previous.get("size") == stat.st_size and previous.get("mtime_ns") == stat.st_mtime_ns and not previous.get("error"):
                item = dict(previous)
            else:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                sound_id = digest.hexdigest()[:24]
                saved = old_by_id.get(sound_id) or seen.get(sound_id, {})
                item = {"id": sound_id, "file": relative, "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns, "enabled": saved.get("enabled", True),
                        "emotion_group": saved.get("emotion_group", "")}
                if saved.get("description_origin") == "manual":
                    item.update(description=saved.get("description", ""), description_origin="manual")
                try:
                    item["duration_sec"] = saved["duration_sec"] if saved.get("duration_sec", 0) > 0 and not saved.get("error") else _sound_duration(path)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    item.update(duration_sec=0.0, error="Không đọc được âm thanh; kiểm tra file và FFprobe.")
            candidates = by_path.get(relative.casefold()) or by_filename.get(path.name.casefold()) or aliases.get(sound_name(path.stem), [])
            variants = {(sources[i].get("title", ""), sources[i].get("description", "")) for i in candidates}
            source = sources[candidates[0]] if candidates and len(variants) == 1 else None
            if source:
                matched.update(candidates)
            item["title"] = (source.get("title") or path.stem) if source else path.stem
            item["aliases"] = []
            if item.get("description_origin") != "manual":
                item["description"] = source.get("description", "").strip() if source else ""
                item["description_origin"] = "json" if source else "missing"
            item["metadata_file"] = source["metadata_file"] if source else ""
            if source:
                item["source_url"] = source.get("source_url", "")
                item["audio_url"] = source.get("audio_url", "")
            item["needs_review"] = not bool(item.get("description")) or bool(item.get("error"))
            if item["id"] in seen:
                canonical = seen[item["id"]]
                duplicates.append({"file": relative, "canonical_file": canonical["file"]})
                if item["title"] != canonical["title"]:
                    canonical["aliases"].append(item["title"])
                if canonical.get("description_origin") != "manual" and item["description"] and item["description"] not in canonical["description"]:
                    canonical["description"] = "\n".join(filter(None, (canonical["description"], item["description"])))
                    canonical["needs_review"] = bool(canonical.get("error"))
            else:
                sounds.append(item)
                seen[item["id"]] = item
        missing = [{"id": source.get("id", ""), "file": source["filename"], "metadata_file": source["metadata_file"]}
                   for index, source in enumerate(sources) if index not in matched]
        _write_json(root / "catalog.json", {**data, "version": 1, "sounds": sounds, "duplicate_files": duplicates, "missing_files": missing})
        return sounds


def update_sound(folder: str, sound_id: str, *, enabled: bool, description: str, emotion_group: str | None = None) -> list[dict[str, Any]]:
    with _CATALOG_LOCK:
        data = load_sound_catalog_data(folder)
        sounds = data["sounds"]
        item = next((item for item in sounds if item["id"] == sound_id), None)
        if item is None:
            raise RuntimeError("Sound đã thay đổi; hãy quét lại kho.")
        if emotion_group is not None:
            if not isinstance(emotion_group, str) or (emotion_group and emotion_group not in data["emotion_groups"]):
                raise ValueError("Nhóm cảm xúc không hợp lệ.")
            item["emotion_group"] = emotion_group
        item.update(enabled=enabled, description=description.strip(), description_origin="manual")
        item["needs_review"] = not bool(item["description"]) or bool(item.get("error"))
        _write_json(sound_library_root(folder) / "catalog.json", data)
        return sounds


def update_emotion_group(folder: str, name: str, *, enabled: bool, description: str) -> None:
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 60 or name.strip() == "Chưa phân nhóm":
        raise ValueError("Tên nhóm cảm xúc phải từ 1 đến 60 ký tự và khác Chưa phân nhóm.")
    if type(enabled) is not bool or not isinstance(description, str) or len(description) > 4000:
        raise ValueError("Cấu hình nhóm cảm xúc không hợp lệ.")
    with _CATALOG_LOCK:
        data = load_sound_catalog_data(folder)
        data["emotion_groups"][name.strip()] = {"enabled": enabled, "description": description.strip()}
        _write_json(sound_library_root(folder) / "catalog.json", data)


def resolve_sound_file(folder: str, item: dict[str, Any]) -> Path:
    root = sound_library_root(folder)
    path = (root / item["file"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() not in AUDIO_EXTS:
        raise RuntimeError("File sound không còn tồn tại hoặc nằm ngoài kho đã chọn.")
    return path
