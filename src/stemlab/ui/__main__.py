from __future__ import annotations

import sys
import os
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication

from stemlab.ui import MainWindow
from stemlab.ui.branding import APP_NAME
from stemlab.ui.theme import APP_STYLESHEET, app_icon
from stemlab.ui.windows_chrome import configure_app_identity


def main() -> int:
    configure_app_identity()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    app.setStyleSheet(APP_STYLESHEET)
    repo_root = Path(__file__).resolve().parents[3]
    app.setWindowIcon(app_icon(repo_root))
    window = MainWindow()
    window.show()
    smoke_exit_ms = os.environ.get("STEMLAB_SMOKE_EXIT_MS")
    if smoke_exit_ms:
        QTimer.singleShot(int(smoke_exit_ms), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
