"""Per-process/window Windows appearance; never changes system theme settings."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys

from PySide6.QtGui import QGuiApplication
from stemlab.ui.branding import WINDOWS_APP_ID


def configure_app_identity() -> None:
    if sys.platform != "win32":
        return
    try:
        shell = ctypes.WinDLL("shell32", use_last_error=True)
        set_identity = shell.SetCurrentProcessExplicitAppUserModelID
        set_identity.argtypes = [wintypes.LPCWSTR]
        set_identity.restype = wintypes.LONG
        set_identity(WINDOWS_APP_ID)
    except (OSError, AttributeError):
        pass


def apply_dark_title_bar(window) -> bool:
    if sys.platform != "win32" or QGuiApplication.platformName() != "windows":
        return False
    try:
        dwm = ctypes.WinDLL("dwmapi", use_last_error=True)
        set_attribute = dwm.DwmSetWindowAttribute
        set_attribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        set_attribute.restype = wintypes.LONG
        handle = wintypes.HWND(int(window.winId()))
        enabled = wintypes.BOOL(1)
        # Attribute 19 supports older Windows 10 builds; current builds use 20.
        dark_enabled = any(
            set_attribute(handle, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)) == 0
            for attribute in (20, 19)
        )
        # Windows 11 caption/text colors. Older Windows ignores these attributes.
        for attribute, color in ((35, 0x292929), (36, 0xEDEDED)):
            value = wintypes.DWORD(color)
            set_attribute(handle, attribute, ctypes.byref(value), ctypes.sizeof(value))
        return dark_enabled
    except (OSError, AttributeError):
        return False
