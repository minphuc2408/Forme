"""Dedicated sound library workspace; network and probing run outside the UI thread."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fluent_blue import (
    Button,
    Checkbox,
    Column,
    DataTable,
    FilePicker,
    FormField,
    NumberInput,
    Panel,
    ScrollArea,
    Stack,
    Text,
    TextArea,
    ThemeManager,
)
from fluent_blue.compatibility.qt import QAudioOutput, QMediaPlayer, QtCore, QUrl, QVBoxLayout, QWidget

from ..core.config import AppSettings
from ..core.meme_library import (
    load_sound_catalog,
    load_sound_catalog_data,
    resolve_sound_file,
    scan_sound_library,
    sound_library_root,
    update_sound,
)
from ..core.models import MediaConfig

Signal = getattr(QtCore, "pyqtSignal", None) or getattr(QtCore, "Signal")


class MemeSoundLibraryPage(ScrollArea):
    catalog_ready = Signal(object, str)
    task_failed = Signal(str)
    save_requested = Signal()

    def __init__(self, settings: AppSettings, executor: ThreadPoolExecutor) -> None:
        super().__init__()
        self._executor = executor
        self._sounds: dict[str, dict] = {}
        self._selected_id = ""
        self._loaded_folder = ""
        self._busy = False
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)

        container = QWidget()
        col = QVBoxLayout(container)
        col.setContentsMargins(0, 0, ThemeManager.spacing(2), 0)
        col.setSpacing(ThemeManager.spacing(3))
        self._scan = Button("Nhập / Quét lại kho", icon="folder-open", variant="primary")
        save = Button("Lưu cấu hình", icon="save", variant="outline")
        panel = Panel(title="Kho Meme Sound", actions=[self._scan, save], padding=3)
        self._folder = FilePicker(mode="directory", button_text="Chọn thư mục", placeholder="Nhập đường dẫn kho sound...")
        self._folder.input.setReadOnly(False)
        panel.add(FormField("Nhập kho bằng đường dẫn · Bao gồm thư mục con", self._folder))
        self._enabled = Checkbox("AI tự chọn sound sau lời bình luận đã duyệt")
        panel.add(self._enabled)
        options = Stack(direction="horizontal", spacing=3)
        self._volume = NumberInput(value=40, minimum=0, maximum=100, step=5, decimals=0)
        self._maximum = NumberInput(value=3, minimum=0, maximum=10, step=1, decimals=0)
        self._duration = NumberInput(value=6, minimum=0.1, maximum=15, step=0.5, decimals=1)
        for control in (self._volume, self._maximum, self._duration):
            control.setMaximumWidth(130)
        options.add(FormField("Âm lượng (%)", self._volume), 1)
        options.add(FormField("Tối đa sound / video", self._maximum), 1)
        options.add(FormField("Tối đa giây / sound", self._duration), 1)
        panel.add(options)
        hint = Text(
            "Dùng Codex / Antigravity và model đang chọn trong Cài đặt. Offline bỏ qua meme. "
            "Mô tả từ các file JSON được gom tự động cùng kho. AI đọc bài viết, bình luận đã duyệt "
            "và mô tả sound để chọn ngữ cảnh phù hợp. File thiếu mô tả chưa được đưa vào lựa chọn.",
            style="caption", color="text-secondary",
        )
        hint.setWordWrap(True)
        panel.add(hint)
        self._status = Text("Chưa nhập kho sound.", style="caption", color="text-secondary")
        self._status.setWordWrap(True)
        panel.add(self._status)
        col.addWidget(panel)

        library = Panel(title="Sound đã nhập · Tìm theo tên hoặc ngữ cảnh", padding=3)
        self._table = DataTable(
            columns=[Column("title", "Tên", width=150), Column("file", "File", width=160),
                     Column("duration_sec", "Giây", width=65), Column("state", "Trạng thái", width=130),
                     Column("description", "Ngữ cảnh", width=330)],
            rows=[], page_size=25, selection="single", searchable=True, column_menu=False, exportable=False,
            empty_title="Kho sound đang trống", empty_description="Tải sound vào thư mục rồi bấm Nhập / Quét lại kho.",
        )
        self._table.setMinimumHeight(220)
        library.add(self._table)
        actions = Stack(direction="horizontal", spacing=2)
        self._preview = Button("Nghe thử", icon="play", variant="secondary")
        stop = Button("Dừng", icon="stop", variant="ghost")
        self._item_enabled = Checkbox("Cho phép AI chọn sound này", checked=True)
        self._save_item = Button("Lưu chỉnh sửa", icon="save", variant="outline")
        actions.add(self._preview)
        actions.add(stop)
        actions.add(self._item_enabled, 1)
        actions.add(self._save_item)
        library.add(actions)
        self._description = TextArea(placeholder="Mô tả được ghép tự động; chỉ sửa ở đây nếu cần hiệu chỉnh.", rows=3)
        library.add(self._description)
        col.addWidget(library)
        col.addStretch(1)
        self.setWidget(container)
        self.set_media(settings.media)
        self.catalog_ready.connect(self._on_catalog_ready)
        self.task_failed.connect(self._on_failure)
        self._scan.clicked.connect(lambda: self._submit("scan"))
        save.clicked.connect(self.save_requested.emit)
        self._table.selection_changed.connect(self._on_selection)
        self._preview.clicked.connect(self._play_selected)
        stop.clicked.connect(self._player.stop)
        self._save_item.clicked.connect(lambda: self._submit("edit"))
        self._submit("load")

    def set_media(self, media: MediaConfig) -> None:
        self._folder.set_paths([str(sound_library_root(media.meme_sound_dir))])
        self._enabled.setChecked(media.meme_sound_enabled)
        self._volume.set_value(media.meme_sound_volume_pct)
        self._maximum.set_value(media.meme_sound_max_per_video)
        self._duration.set_value(media.meme_sound_max_duration_sec)
        if self._loaded_folder and self._loaded_folder != str(sound_library_root(media.meme_sound_dir)):
            self._submit("load")

    def collect_settings(self, media: MediaConfig) -> None:
        media.meme_sound_dir = str(sound_library_root(self._folder.input.text()))
        media.meme_sound_enabled = self._enabled.isChecked()
        media.meme_sound_volume_pct = int(self._volume.value())
        media.meme_sound_max_per_video = int(self._maximum.value())
        media.meme_sound_max_duration_sec = float(self._duration.value())

    def _submit(self, action: str) -> None:
        if self._busy:
            return
        folder = str(sound_library_root(self._folder.input.text()))
        if action == "edit" and (not self._selected_id or folder != self._loaded_folder):
            self._status.setText("Chọn sound trong kho hiện tại trước khi lưu.")
            return
        selected = self._selected_id
        enabled = self._item_enabled.isChecked()
        description = self._description.text()
        self._busy = True
        self._player.stop()
        for button in (self._scan, self._save_item):
            button.setEnabled(False)
        self._status.setText("Đang đọc danh mục sound...")

        def worker() -> None:
            try:
                if action == "load":
                    sounds = load_sound_catalog(folder)
                elif action == "edit":
                    sounds = update_sound(folder, selected, enabled=enabled, description=description)
                else:
                    root = sound_library_root(folder)
                    if root == sound_library_root():
                        root.mkdir(parents=True, exist_ok=True)
                    sounds = scan_sound_library(folder)
                data = load_sound_catalog_data(folder)
                self.catalog_ready.emit({"sounds": sounds, "folder": folder, "summary": data}, "")
            except Exception as exc:
                if action == "scan" and (sound_library_root(folder) / "catalog.json").is_file():
                    try:
                        sounds = load_sound_catalog(folder)
                        self.catalog_ready.emit({"sounds": sounds, "folder": folder, "summary": load_sound_catalog_data(folder)}, f"Chưa hoàn tất quét: {exc}. ")
                        return
                    except Exception:
                        pass
                self.task_failed.emit(str(exc))

        self._executor.submit(worker)

    def _on_catalog_ready(self, payload: dict, message: str) -> None:
        if payload["folder"] != str(sound_library_root(self._folder.input.text())):
            self._finish_task()
            self._submit("load")
            return
        self._loaded_folder = payload["folder"]
        self._sounds = {item["id"]: item for item in payload["sounds"]}
        self._selected_id = ""
        self._description.set_text("")
        rows = [{**item, "state": "Lỗi file" if item.get("error") else "Đã tắt" if not item.get("enabled", True)
                 else "Chưa có mô tả" if item.get("needs_review") else "Sẵn sàng"} for item in self._sounds.values()]
        self._table.set_rows(rows)
        pending = sum(bool(item.get("needs_review")) for item in self._sounds.values())
        summary = payload.get("summary", {})
        missing = summary.get("missing_files", [])
        duplicates = summary.get("duplicate_files", [])
        self._status.setText(f"{message}{len(rows)} sound · {pending} cần kiểm tra · {len(duplicates)} file trùng · {len(missing)} mô tả chưa có file.")
        self._status.setToolTip("\n".join(item["file"] for item in missing))
        self._finish_task()

    def _on_failure(self, message: str) -> None:
        self._status.setText(f"Chưa hoàn tất: {message}")
        self._finish_task()

    def _finish_task(self) -> None:
        self._busy = False
        for button in (self._scan, self._save_item):
            button.setEnabled(True)

    def _on_selection(self, rows: list[dict]) -> None:
        if not rows:
            return
        item = self._sounds.get(str(rows[0].get("id", "")))
        if item:
            self._selected_id = item["id"]
            self._description.set_text(item.get("description", ""))
            self._item_enabled.setChecked(item.get("enabled", True))

    def _play_selected(self) -> None:
        item = self._sounds.get(self._selected_id)
        if item is None:
            return
        try:
            path = resolve_sound_file(self._loaded_folder, item)
            self._audio.setVolume(float(self._volume.value()) / 100.0)
            self._player.setSource(QUrl.fromLocalFile(str(path)))
            self._player.play()
        except Exception as exc:
            self._status.setText(str(exc))


def build_meme_image_page() -> QWidget:
    page = QWidget()
    col = QVBoxLayout(page)
    panel = Panel(title="Kho Meme Image", padding=3)
    text = Text("Tính năng sẽ phát triển sau: quản lý kho ảnh meme và chọn ảnh theo ngữ cảnh bình luận.", color="text-secondary")
    text.setWordWrap(True)
    panel.add(text)
    col.addWidget(panel)
    col.addStretch(1)
    return page
