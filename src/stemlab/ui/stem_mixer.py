from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QFrame,
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
        self.setObjectName("stemRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.role, self.path, self.player = role, path, player
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(6)
        color = {
            "vocals": "#af99ce", "drums": "#c5a077", "bass": "#86ad8c",
            "guitar": "#8aa9ce", "piano": "#7db6b1", "other": "#a0a0a0",
        }.get(role, "#a0a0a0")
        stripe = QFrame()
        stripe.setFixedSize(3, 24)
        stripe.setStyleSheet(f"background: {color}; border: none; border-radius: 1px;")
        layout.addWidget(stripe)
        label = QLabel(role.title())
        label.setObjectName("stemName")
        label.setMinimumWidth(52)
        self.mute_button = QPushButton("M")
        self.mute_button.setObjectName("muteButton")
        self.mute_button.setToolTip(f"Mute · Silenciar {role.title()}")
        self.mute_button.setAccessibleName(f"Silenciar {role.title()}")
        self.mute_button.setCheckable(True)
        self.solo_button = QPushButton("S")
        self.solo_button.setObjectName("soloButton")
        self.solo_button.setToolTip(f"Solo · Ouvir somente {role.title()} e outros solos ativos")
        self.solo_button.setAccessibleName(f"Solo {role.title()}")
        self.solo_button.setCheckable(True)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setMinimumWidth(50)
        self.volume.setAccessibleName(f"Volume de {role.title()}")
        self.volume.setRange(0, 100)
        self.volume.setValue(100)
        self.volume_value = QLabel("100%")
        self.volume_value.setObjectName("volumeValue")
        self.volume_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.volume_value.setFixedWidth(34)
        self.export_button = QPushButton("Exportar")
        self.export_button.setObjectName("stemExportButton")
        self.export_button.setFixedWidth(76)
        self.export_button.setToolTip(f"Exportar {role.title()} sem alterar o volume do arquivo")
        self.export_button.setAccessibleName(f"Exportar {role.title()}")
        for button in (self.mute_button, self.solo_button):
            button.setFixedSize(28, 28)
        layout.addWidget(label)
        layout.addWidget(self.mute_button)
        layout.addWidget(self.solo_button)
        layout.addWidget(self.volume, 1)
        layout.addWidget(self.volume_value)
        layout.addWidget(self.export_button)
        self.mute_button.toggled.connect(lambda value: self.player.set_mute(self.role, value))
        self.solo_button.toggled.connect(lambda value: self.player.set_solo(self.role, value))
        self.volume.valueChanged.connect(lambda value: self.player.set_volume(self.role, value / 100.0))
        self.volume.valueChanged.connect(lambda value: self.volume_value.setText(f"{value}%"))
        self.export_button.clicked.connect(lambda: self.export_requested.emit(self.role, self.path))


class StemMixer(QWidget):
    export_requested = Signal(str, object)

    def __init__(self, player, parent=None) -> None:
        super().__init__(parent)
        self.player = player
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
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
            self._layout.removeWidget(row)
            row.hide()
            row.deleteLater()
        self.rows.clear()
