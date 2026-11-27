"""Application entry point for Threads Studio Pro."""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Force consistent PyQt6 binding before importing fluent_blue
os.environ.setdefault("FLUENT_BLUE_QT_BINDING", "PyQt6")

from .assets_gen import ensure_sample_assets
from .core.config import AppSettings


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Threads Studio Pro — web local")
    parser.add_argument("--desktop", action="store_true", help="Mở giao diện desktop cũ")
    parser.add_argument("--port", type=int, default=8000, help="Cổng web local (mặc định: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Không tự mở trình duyệt")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Cổng phải nằm trong khoảng 1–65535.")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ensure_sample_assets()
    settings = AppSettings.load()

    if not args.desktop:
        from .web_server import run_web_studio

        return run_web_studio(settings, port=args.port, open_browser=not args.no_browser)

    from fluent_blue import ThemeManager
    from fluent_blue.compatibility.qt import QApplication
    from .ui.main_window import ThreadsStudioWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Threads Studio Pro")
    ThemeManager.set_theme(settings.theme if settings.theme in ("dark", "light", "high-contrast") else "light")

    win = ThreadsStudioWindow(settings)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

