from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QIcon


_ICON_ROOT = Path(__file__).resolve().parents[3] / "resources" / "icons"
APP_STYLESHEET = r"""
QWidget {
    color: #dedede;
    font-family: "Segoe UI";
    font-size: 10pt;
    selection-background-color: #365e9c;
    selection-color: #ffffff;
}
QMainWindow, QWidget#centralPanel { background: #1b1b1b; }
QFrame#appBar { background: #292929; border-bottom: 1px solid #101010; }
QLabel#brandMark {
    color: #a5bfff; background: #1c2943; border: 1px solid #607cae;
    border-radius: 3px; font-size: 14pt; font-weight: 600;
}
QLabel#appTitle { color: #f2f2f2; font-size: 12pt; font-weight: 600; }
QLabel#workspaceTitle { color: #a8a8a8; font-size: 9pt; }
QFrame#settingsPanel, QFrame#workspacePanel {
    background: #252525; border: 1px solid #363636; border-radius: 4px;
}
QWidget#settingsContent { background: #252525; }
QWidget#workspaceContent { background: #202020; }
QLabel#panelTitle { color: #ededed; font-size: 10pt; font-weight: 600; }
QFrame#sourcePanel { background: #292929; border-bottom: 1px solid #393939; }
QLabel#filePathLabel { color: #ededed; font-size: 11pt; font-weight: 600; }
QLabel#eyebrowLabel { color: #969696; font-size: 8pt; font-weight: 600; }
QLabel#fieldLabel { color: #c5c5c5; font-size: 9pt; }
QLabel#helperText, QLabel#hintLabel { color: #aaa; font-size: 9pt; }
QLabel#hintLabel { padding: 9px 0; border-top: 1px solid #3b3b3b; }
QLabel#emptySymbol { color: #696969; font-size: 40pt; }
QLabel#emptyTitle { color: #ddd; font-size: 16pt; font-weight: 600; }
QLabel#stepLabel { color: #999; font-size: 9pt; }
QFrame#actionPanel { background: #292929; border-top: 1px solid #3a3a3a; }
QFrame#statusBar { background: #292929; border-top: 1px solid #141414; }
QLabel#statusLabel { color: #cecece; font-size: 9pt; }
QLabel#statusLabel[tone="error"] { color: #efaaaa; }
QLabel#localLabel { color: #999; font-size: 8pt; }
QGroupBox { background: transparent; border: none; padding: 0; margin: 0; }
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    color: #ddd; padding: 0; font-weight: 600;
}
QPushButton {
    background: #393939; color: #e7e7e7; border: 1px solid #535353;
    border-radius: 4px; padding: 6px 11px; min-height: 18px;
}
QPushButton:hover { background: #474747; border-color: #777; }
QPushButton:pressed { background: #222; border-color: #aaa; }
QPushButton:focus { border: 1px solid #98bbff; }
QPushButton:disabled { color: #777; background: #2c2c2c; border-color: #414141; }
QPushButton#primaryButton {
    background: #3875dd; color: #fff; border-color: #4485f5; font-weight: 600;
}
QPushButton#primaryButton:hover { background: #4888ef; border-color: #81adff; }
QPushButton#primaryButton:pressed { background: #2558ad; }
QPushButton#primaryButton:focus { border: 1px solid #d2e2ff; }
QPushButton#primaryButton:disabled { background: #313c4e; color: #7a8ba6; border-color: #3b4a60; }
QComboBox {
    color: #e6e6e6; background: #1d1d1d; border: 1px solid #505050;
    border-radius: 3px; padding: 6px 27px 6px 9px; min-height: 18px;
}
QComboBox:hover { border-color: #818181; }
QComboBox:focus { border-color: #88adf4; }
QComboBox:disabled { color: #777; background: #242424; border-color: #3c3c3c; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow { image: url("@icons@/ui-chevron.svg"); width: 14px; height: 14px; }
QComboBox QAbstractItemView {
    color: #eee; background: #303030; border: 1px solid #555;
    selection-background-color: #3b609c; selection-color: #fff; outline: none;
    padding: 4px;
}
QCheckBox, QRadioButton { color: #d5d5d5; spacing: 7px; padding: 2px 0; }
QCheckBox:disabled, QRadioButton:disabled { color: #777; }
QCheckBox:focus, QRadioButton:focus { color: #b4ceff; }
QCheckBox::indicator {
    width: 15px; height: 15px; border: 1px solid #777;
    border-radius: 2px; background: #202020;
}
QCheckBox::indicator:hover { border-color: #b8b8b8; }
QCheckBox::indicator:checked {
    background: #477aca; border-color: #6d9be5; image: url("@icons@/ui-check.svg");
}
QCheckBox::indicator:disabled { border-color: #555; background-color: #353535; }
QRadioButton::indicator {
    width: 14px; height: 14px; border: 1px solid #888;
    border-radius: 8px; background: #202020;
}
QRadioButton::indicator:checked { background: #84afff; border: 4px solid #3b4b63; }
QRadioButton::indicator:hover { border-color: #b8cbed; }
QProgressBar { background: #171717; border: none; border-radius: 2px; min-height: 4px; max-height: 4px; }
QProgressBar::chunk { background: #5e94ec; border-radius: 2px; }
QFrame#transportPanel { background: #2a2a2a; border: 1px solid #393939; border-radius: 4px; }
QLabel#timeLabel, QLabel#volumeValue { color: #bbb; font-family: "Consolas"; font-size: 9pt; }
QWidget#stemRow { background: #2a2a2a; border: 1px solid #373737; border-radius: 3px; }
QWidget#stemRow:hover { background: #2f2f2f; border-color: #505050; }
QLabel#stemName { color: #e4e4e4; font-weight: 600; }
QPushButton#muteButton, QPushButton#soloButton { padding: 0; font-size: 9pt; font-weight: 600; }
QPushButton#stemExportButton { padding: 6px 8px; }
QPushButton#muteButton:checked { background: #675032; color: #ffdda0; border-color: #b48a49; }
QPushButton#soloButton:checked { background: #304f7e; color: #c9e0ff; border-color: #6b97d7; }
QSlider::groove:horizontal { height: 3px; background: #171717; border-radius: 1px; }
QSlider::sub-page:horizontal { background: #819dc5; border-radius: 1px; }
QSlider::handle:horizontal {
    background: #d7d7d7; border: 1px solid #202020; border-radius: 4px;
    width: 8px; margin: -5px 0;
}
QSlider::handle:horizontal:hover { background: #b1cdff; border-color: #819dc5; }
QSlider::handle:horizontal:pressed { background: #8fb7ff; }
QSlider::handle:horizontal:focus { border-color: #9bbfff; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #242424; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #535353; border-radius: 4px; min-height: 32px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #777; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSplitter::handle { background: #1b1b1b; }
QSplitter::handle:hover { background: #4b6488; }
QToolTip { color: #eee; background: #3a3a3a; border: 1px solid #666; padding: 6px; }
""".replace("@icons@", _ICON_ROOT.as_posix())


@lru_cache(maxsize=8)
def control_icon(name: str) -> QIcon:
    return QIcon(str(_ICON_ROOT / f"ui-{name}.svg"))


def icon_path(repo_root: Path | None = None) -> Path | None:
    source_root = Path(__file__).resolve().parents[3]
    roots = [repo_root.resolve(), source_root] if repo_root is not None else [source_root]
    candidates = [
        root / "resources" / "icons" / name
        for root in roots
        for name in ("multitrack.ico", "multitrack.png")
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def app_icon(repo_root: Path | None = None) -> QIcon:
    path = icon_path(repo_root)
    return QIcon(str(path)) if path is not None else QIcon()
