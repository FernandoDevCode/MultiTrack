from __future__ import annotations

import sys
import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from stemlab.ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("StemLab")
    window = MainWindow()
    window.show()
    smoke_exit_ms = os.environ.get("STEMLAB_SMOKE_EXIT_MS")
    if smoke_exit_ms:
        QTimer.singleShot(int(smoke_exit_ms), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
