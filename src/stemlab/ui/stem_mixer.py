from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt


class StemRow(QWidget):
    export_requested = Signal(str, object)

    def __init__(self, role: str, path: Path, player, parent=None) -> None:
        super().__init__(parent)
        self.role, self.path, self.player = role, path, player
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(role.title())
        label.setMinimumWidth(80)
        self.mute_button = QPushButton("M")
        self.mute_button.setCheckable(True)
        self.solo_button = QPushButton("S")
        self.solo_button.setCheckable(True)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(100)
        self.export_button = QPushButton("Exportar")
        for button in (self.mute_button, self.solo_button):
            button.setFixedWidth(36)
        layout.addWidget(label)
        layout.addWidget(self.mute_button)
        layout.addWidget(self.solo_button)
        layout.addWidget(self.volume, 1)
        layout.addWidget(self.export_button)
        self.mute_button.toggled.connect(lambda value: self.player.set_mute(self.role, value))
        self.solo_button.toggled.connect(lambda value: self.player.set_solo(self.role, value))
        self.volume.valueChanged.connect(lambda value: self.player.set_volume(self.role, value / 100.0))
        self.export_button.clicked.connect(lambda: self.export_requested.emit(self.role, self.path))


class StemMixer(QWidget):
    export_requested = Signal(str, object)

    def __init__(self, player, parent=None) -> None:
        super().__init__(parent)
        self.player = player
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.rows: dict[str, StemRow] = {}

    def set_stems(self, stems: dict[str, Path]) -> None:
        self.clear()
        for role, path in stems.items():
            row = StemRow(role, path, self.player, self)
            row.export_requested.connect(self.export_requested)
            self.rows[role] = row
            self._layout.addWidget(row)

    def clear(self) -> None:
        for row in self.rows.values():
            row.deleteLater()
        self.rows.clear()
