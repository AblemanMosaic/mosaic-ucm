from __future__ import annotations

import copy
import ctypes
import math
import sys
import traceback
import uuid
from collections import deque
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from mosaic_ui_std.theme import validate_tokens

from .model import UIRefusal


if sys.platform != "win32":
    raise RuntimeError("mosaic_ui.win32 requires Windows")

from .win32_vector import VectorPainter  # noqa: E402  (GDI+ binding is Windows-only)


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
ole32 = ctypes.WinDLL("ole32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
uxtheme = ctypes.WinDLL("uxtheme", use_last_error=True)
msftedit = ctypes.WinDLL("Msftedit", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)
SUBCLASSPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM, WPARAM, WPARAM)
BFFCALLBACK = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.UINT, LPARAM, LPARAM)

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000
WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_EX_COMPOSITED = 0x02000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_RIGHT = 0x00001000
WS_EX_RTLREADING = 0x00002000
WS_TABSTOP = 0x00010000
WS_BORDER = 0x00800000
WS_VSCROLL = 0x00200000
ES_AUTOHSCROLL = 0x0080
ES_MULTILINE = 0x0004
ES_AUTOVSCROLL = 0x0040
ES_READONLY = 0x0800
EM_SETBKGNDCOLOR = 0x0400 + 67
EM_SETCHARFORMAT = 0x0400 + 68
EM_SETSEL = 0x00B1
SCF_SELECTION = 0x0001
CFM_BOLD = 0x00000001
CFM_ITALIC = 0x00000002
CFM_UNDERLINE = 0x00000004
CFM_OFFSET = 0x10000000
CFM_FACE = 0x20000000
CFM_COLOR = 0x40000000
CFE_BOLD = 0x00000001
CFE_ITALIC = 0x00000002
CFE_UNDERLINE = 0x00000004
BS_OWNERDRAW = 0x0000000B
CBS_DROPDOWN = 0x0002
CBS_DROPDOWNLIST = 0x0003
CBS_HASSTRINGS = 0x0200
CBS_OWNERDRAWFIXED = 0x0010
SS_LEFT = 0
SS_CENTER = 1
SS_OWNERDRAW = 0x000D
SW_SHOW = 5
SW_HIDE = 0
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
WM_DESTROY = 0x0002
WM_SIZE = 0x0005
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_TIMER = 0x0113
WM_CTLCOLORMSGBOX = 0x0132
WM_CTLCOLOREDIT = 0x0133
WM_CTLCOLORLISTBOX = 0x0134
WM_CTLCOLORBTN = 0x0135
WM_CTLCOLORDLG = 0x0136
WM_CTLCOLORSCROLLBAR = 0x0137
WM_CTLCOLORSTATIC = 0x0138
WM_DRAWITEM = 0x002B
WM_MOUSEMOVE = 0x0200
WM_DPICHANGED = 0x02E0
BASE_DPI = 96
WM_MOUSELEAVE = 0x02A3
TME_LEAVE = 0x00000002
WM_SETFONT = 0x0030
WM_GETTEXTLENGTH = 0x000E
WM_GETTEXT = 0x000D
WM_SETTEXT = 0x000C
WM_SETFOCUS = 0x0007
WM_KEYDOWN = 0x0100
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
BN_CLICKED = 0
CBN_SELCHANGE = 1
CBN_EDITCHANGE = 5
LBN_SELCHANGE = 1
EN_KILLFOCUS = 0x0200
CB_ADDSTRING = 0x0143
CB_GETCURSEL = 0x0147
CB_SETCURSEL = 0x014E
LB_ADDSTRING = 0x0180
LB_RESETCONTENT = 0x0184
LB_SETCURSEL = 0x0186
LB_GETCURSEL = 0x0188
LB_GETTEXT = 0x0189
LB_GETTEXTLEN = 0x018A
LBS_NOTIFY = 0x0001
LBS_OWNERDRAWFIXED = 0x0010
LBS_HASSTRINGS = 0x0040
LBS_NOINTEGRALHEIGHT = 0x0100
PBM_SETRANGE32 = 0x0406
PBM_SETPOS = 0x0402
PBM_SETBARCOLOR = 0x0409
PBM_SETBKCOLOR = 0x2001
DT_CENTER = 0x00000001
DT_LEFT = 0x00000000
DT_RIGHT = 0x00000002
DT_VCENTER = 0x00000004
DT_SINGLELINE = 0x00000020
DT_NOPREFIX = 0x00000800
DT_END_ELLIPSIS = 0x00008000
TRANSPARENT = 1
ODS_SELECTED = 0x0001
ODS_DISABLED = 0x0004
ODT_LISTBOX = 2
ODT_COMBOBOX = 3
ODT_STATIC = 5
IDC_ARROW = 32512
COLOR_WINDOW = 5
BIF_RETURNONLYFSDIRS = 0x0001
BIF_NEWDIALOGSTYLE = 0x0040
BIF_USENEWUI = BIF_NEWDIALOGSTYLE | 0x0010
MAX_PATH = 260
CW_USEDEFAULT = -2147483648
CLSCTX_INPROC_SERVER = 0x00000001
FOS_PICKFOLDERS = 0x00000020
FOS_FORCEFILESYSTEM = 0x00000040
FOS_PATHMUSTEXIST = 0x00000800
FOS_FILEMUSTEXIST = 0x00001000
SIGDN_FILESYSPATH = 0x80058000
ERROR_CANCELLED_HRESULT = -2147023673
BFFM_INITIALIZED = 1
BFFM_SETSELECTIONW = 0x0400 + 103


def rgb(value: str) -> int:
    value = value.lstrip("#")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return red | (green << 8) | (blue << 16)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT), ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND), ("message", wintypes.UINT), ("wParam", WPARAM),
        ("lParam", LPARAM), ("time", wintypes.DWORD), ("pt", wintypes.POINT),
        ("lPrivate", wintypes.DWORD),
    ]


class CHARFORMATW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT), ("dwMask", wintypes.DWORD),
        ("dwEffects", wintypes.DWORD), ("yHeight", ctypes.c_long),
        ("yOffset", ctypes.c_long), ("crTextColor", wintypes.DWORD),
        ("bCharSet", ctypes.c_ubyte), ("bPitchAndFamily", ctypes.c_ubyte),
        ("szFaceName", ctypes.c_wchar * 32),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC), ("fErase", wintypes.BOOL), ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL), ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


class DRAWITEMSTRUCT(ctypes.Structure):
    _fields_ = [
        ("CtlType", wintypes.UINT), ("CtlID", wintypes.UINT), ("itemID", wintypes.UINT),
        ("itemAction", wintypes.UINT), ("itemState", wintypes.UINT),
        ("hwndItem", wintypes.HWND), ("hDC", wintypes.HDC),
        ("rcItem", wintypes.RECT), ("itemData", ctypes.c_size_t),
    ]


class INITCOMMONCONTROLSEX(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("dwICC", wintypes.DWORD)]


class MINMAXINFO(ctypes.Structure):
    _fields_ = [("reserved", wintypes.POINT), ("maximum", wintypes.POINT),
                ("position", wintypes.POINT), ("minimum_track", wintypes.POINT),
                ("maximum_track", wintypes.POINT)]


class BROWSEINFOW(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND), ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", wintypes.LPWSTR), ("lpszTitle", wintypes.LPCWSTR),
        ("ulFlags", wintypes.UINT), ("lpfn", ctypes.c_void_p),
        ("lParam", LPARAM), ("iImage", ctypes.c_int),
    ]


class GUID(ctypes.Structure):
    _fields_ = [("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
                ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, value: str) -> "GUID":
        raw = uuid.UUID(value).bytes_le
        return cls(int.from_bytes(raw[0:4], "little"), int.from_bytes(raw[4:6], "little"),
                   int.from_bytes(raw[6:8], "little"), (ctypes.c_ubyte * 8)(*raw[8:]))


class TOOLINFOW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("uFlags", wintypes.UINT),
                ("hwnd", wintypes.HWND), ("uId", WPARAM), ("rect", wintypes.RECT),
                ("hinst", wintypes.HINSTANCE), ("lpszText", wintypes.LPWSTR),
                ("lParam", LPARAM), ("lpReserved", ctypes.c_void_p)]


class LVCOLUMNW(ctypes.Structure):
    _fields_ = [("mask", wintypes.UINT), ("fmt", ctypes.c_int), ("cx", ctypes.c_int),
                ("pszText", wintypes.LPWSTR), ("cchTextMax", ctypes.c_int),
                ("iSubItem", ctypes.c_int), ("iImage", ctypes.c_int), ("iOrder", ctypes.c_int)]


class LVITEMW(ctypes.Structure):
    _fields_ = [("mask", wintypes.UINT), ("iItem", ctypes.c_int), ("iSubItem", ctypes.c_int),
                ("state", wintypes.UINT), ("stateMask", wintypes.UINT),
                ("pszText", wintypes.LPWSTR), ("cchTextMax", ctypes.c_int),
                ("iImage", ctypes.c_int), ("lParam", LPARAM), ("iIndent", ctypes.c_int)]


class TRACKMOUSEEVENT(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("hwndTrack", wintypes.HWND), ("dwHoverTime", wintypes.DWORD)]


class NMHDR(ctypes.Structure):
    _fields_ = [("hwndFrom", wintypes.HWND), ("idFrom", WPARAM), ("code", wintypes.UINT)]


class NMLVDISPINFOW(ctypes.Structure):
    _fields_ = [("hdr", NMHDR), ("item", LVITEMW)]


class LVFINDINFOW(ctypes.Structure):
    _fields_ = [("flags", wintypes.UINT), ("psz", wintypes.LPCWSTR),
                ("lParam", LPARAM), ("pt", wintypes.POINT), ("vkDirection", wintypes.UINT)]


class NMLVFINDITEMW(ctypes.Structure):
    _fields_ = [("hdr", NMHDR), ("iStart", ctypes.c_int), ("lvfi", LVFINDINFOW)]


class NMLISTVIEW(ctypes.Structure):
    _fields_ = [
        ("hdr", NMHDR), ("iItem", ctypes.c_int), ("iSubItem", ctypes.c_int),
        ("uNewState", wintypes.UINT), ("uOldState", wintypes.UINT),
        ("uChanged", wintypes.UINT), ("ptAction", wintypes.POINT), ("lParam", LPARAM),
    ]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.SendMessageW.restype = LRESULT
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype = wintypes.HANDLE
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
user32.EnableWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT), wintypes.BOOL]
user32.TrackMouseEvent.argtypes = [ctypes.POINTER(TRACKMOUSEEVENT)]
try:  # Windows 10 1607+; older hosts keep the pre-r009 96-DPI realization.
    user32.GetDpiForWindow.argtypes = [wintypes.HWND]
    user32.GetDpiForWindow.restype = wintypes.UINT
    _get_dpi_for_window = user32.GetDpiForWindow
except AttributeError:
    _get_dpi_for_window = None


def to_physical(value: float, scale: float) -> int:
    """Round one DIP coordinate to device pixels (half-up, deterministic)."""
    return int(math.floor(value * scale + 0.5))


def compact_identifier(value: str) -> str:
    """Display form for long hex identifiers (first 12 ... last 8). The full value stays in window text."""
    text = str(value)
    if len(text) >= 24 and all(ch in "0123456789abcdefABCDEF" for ch in text):
        return text[:12] + "\u2026" + text[-8:]
    return text


def scale_rect(rect: tuple[int, int, int, int], scale: float) -> tuple[int, int, int, int]:
    """Scale a DIP (x, y, width, height) rect by rounding its edges, so neighbours never gap or overlap."""
    x, y, width, height = rect
    left, top = to_physical(x, scale), to_physical(y, scale)
    return left, top, to_physical(x + width, scale) - left, to_physical(y + height, scale) - top
user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = wintypes.HDC
user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
user32.FrameRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.RECT), wintypes.UINT]
user32.SetTimer.argtypes = [wintypes.HWND, WPARAM, wintypes.UINT, ctypes.c_void_p]
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.IsDialogMessageW.argtypes = [wintypes.HWND, ctypes.POINTER(MSG)]
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.UpdateWindow.argtypes = [wintypes.HWND]
user32.RedrawWindow.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT), wintypes.HRGN, wintypes.UINT]
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.CreateFontW.restype = wintypes.HFONT
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetBkColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
gdi32.CreatePen.restype = wintypes.HANDLE
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.RoundRect.argtypes = [wintypes.HDC] + [ctypes.c_int] * 6
user32.DrawFocusRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, WPARAM, wintypes.LPCWSTR]
user32.TrackPopupMenuEx.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
user32.TrackPopupMenuEx.restype = wintypes.UINT
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalFree.argtypes = [wintypes.HANDLE]
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.DestroyIcon.argtypes = [wintypes.HICON]
user32.GetFocus.restype = wintypes.HWND
user32.GetNextDlgTabItem.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.BOOL]
user32.GetNextDlgTabItem.restype = wintypes.HWND
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.IsWindowEnabled.argtypes = [wintypes.HWND]
user32.BeginDeferWindowPos.argtypes = [ctypes.c_int]
user32.BeginDeferWindowPos.restype = wintypes.HANDLE
user32.DeferWindowPos.argtypes = [wintypes.HANDLE, wintypes.HWND, wintypes.HWND,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.DeferWindowPos.restype = wintypes.HANDLE
user32.EndDeferWindowPos.argtypes = [wintypes.HANDLE]
gdi32.GetStockObject.argtypes = [ctypes.c_int]
gdi32.GetStockObject.restype = wintypes.HGDIOBJ
shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SUBCLASSPROC, WPARAM, WPARAM]
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
comctl32.DefSubclassProc.restype = LRESULT
uxtheme.SetWindowTheme.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BROWSEINFOW)]
shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
ole32.CoInitializeEx.restype = ctypes.c_long
ole32.CoUninitialize.argtypes = []
ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
                                   ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
ole32.CoCreateInstance.restype = ctypes.c_long
shell32.SHCreateItemFromParsingName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p,
                                                ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
shell32.SHCreateItemFromParsingName.restype = ctypes.c_long
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateFontW.argtypes = [ctypes.c_int] * 5 + [wintypes.DWORD] * 8 + [wintypes.LPCWSTR]
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]


@dataclass
class Control:
    key: str
    hwnd: int
    kind: str
    command_id: int | None = None


_windows: dict[int, "NativeWindow"] = {}
_window_class_registered = False


@WNDPROC
def _window_proc(hwnd: int, message: int, wparam: int, lparam: int) -> int:
    window = _windows.get(int(hwnd))
    if window is not None:
        try:
            return window._dispatch(message, wparam, lparam)
        except Exception:
            window.record_callback_failure()
            return 0
    return user32.DefWindowProcW(hwnd, message, wparam, lparam)


class NativeWindow:
    """Small, stdlib-only Win32 component realization with semantic control keys."""

    def create_role_font(self, role: str, scale: float = 1.0) -> int:
        """Create the HFONT for a typography role token at a DPI scale; the caller owns deletion."""
        spec = self.TYPOGRAPHY[role]
        return gdi32.CreateFontW(-max(1, to_physical(spec["size"], scale)), 0, 0, 0, int(spec["weight"]), 0, 0, 0,
                                 1, 0, 0, 5, 0, spec["family"])

    def __init__(self, title: str, *, tokens: dict, width: int = 1240, height: int = 820,
                 owner: "NativeWindow | None" = None, error_status: tuple[str, str] | None = None,
                 rtl: bool = False, presentation: str = "window") -> None:
        # Theme tokens are injected (closed schema, validated) rather than read from a generated payload.
        validate_tokens(tokens)
        if presentation not in {"window", "splash"}:
            raise UIRefusal("NATIVE_PRESENTATION_REFUSED", presentation)
        if presentation == "splash" and owner is not None:
            raise UIRefusal("NATIVE_PRESENTATION_REFUSED", "SPLASH_OWNER")
        self.TOKENS = copy.deepcopy(tokens)
        self.COLORS = {key: rgb(value) for key, value in self.TOKENS["colors"].items()}
        self.COLORS["raised"] = self.COLORS["surface_raised"]
        self.COLORS["quiet"] = self.COLORS["text_quiet"]
        self.TYPOGRAPHY = self.TOKENS["typography"]["roles"]
        # (control key, text) written when a UI callback fails; None disables the status write.
        self.error_status = error_status
        self.title = title
        self.owner = owner
        self.rtl = bool(rtl)
        self.presentation = presentation
        self._icons: list[int] = []
        self._images: dict[str, object] = {}
        self._tooltip_buffers: list[object] = []
        self._modal = False
        self.callback_errors = deque(maxlen=20)
        self.keyboard_navigation = False
        self._rects: dict[str, tuple[int, int, int, int]] = {}
        self._progress_values: dict[str, int] = {}
        self._table_rows: dict[int, tuple] = {}
        self._table_callbacks: dict[int, Callable[[str], None]] = {}
        self._table_sync: set[int] = set()
        self._table_text_buffers = deque(maxlen=32)
        self.controls: dict[str, Control] = {}
        self.button_styles: dict[str, str] = {}
        self.selected_buttons: set[str] = set()
        self.hovered: str | None = None
        self._components: dict[str, dict] = {}
        self._choice_pointer_pending: set[str] = set()
        self.label_styles: dict[int, str] = {}
        self.control_backgrounds: dict[int, str] = {}
        self._subclasses: list[SUBCLASSPROC] = []
        self.handlers: dict[int, tuple[set[int] | None, Callable[[], None]]] = {}
        self._focus_handlers: dict[str, Callable[[], None]] = {}
        self._accessible_keys: set[str] = set()
        self._accessibility_values: dict[str, tuple[str, str, str, str]] = {}
        self.context_menus = {}
        self.timer_handler: Callable[[], None] | None = None
        self.layout_handler: Callable[[int, int], None] | None = None
        self.close_handler: Callable[[], bool | None] | None = None
        self.minimum_client_size = (920, 700)
        self._next_id = 1000
        self._class_name = f"MosaicNativeUI_{ctypes.cast(_window_proc, ctypes.c_void_p).value:x}"
        self._instance = kernel32.GetModuleHandleW(None)
        self._brushes = {name: gdi32.CreateSolidBrush(color) for name, color in self.COLORS.items()}
        self.dpi, self.scale = BASE_DPI, 1.0
        self._fonts: dict[str, int] = {}
        self._font_roles: dict[str, str] = {}
        self._initialize_runtime()
        self._vector: VectorPainter | None = None
        try:
            self._vector = VectorPainter()
        except OSError:
            self.record_callback_failure()  # Visible; buttons keep the GDI RoundRect renderer.
        self._register_class()
        self.window_style = (WS_POPUP if presentation == "splash"
                             else WS_OVERLAPPEDWINDOW if owner is None else 0x00C80000) | WS_CLIPCHILDREN
        extended_style = WS_EX_COMPOSITED | (WS_EX_RTLREADING if self.rtl else 0)
        if presentation == "splash":
            extended_style |= WS_EX_TOOLWINDOW
        self.hwnd = user32.CreateWindowExW(
            extended_style, self._class_name, title,
            self.window_style, CW_USEDEFAULT, CW_USEDEFAULT,
            width, height, owner.hwnd if owner else None, None, self._instance, None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        _windows[int(self.hwnd)] = self
        self.dpi = self._query_dpi()
        self.scale = self.dpi / BASE_DPI
        self._build_fonts()
        if presentation == "splash":
            physical_width, physical_height = self.px(width), self.px(height)
            screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            user32.SetWindowPos(
                self.hwnd, None, max(0, (screen_width - physical_width) // 2),
                max(0, (screen_height - physical_height) // 2), physical_width, physical_height,
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        elif self.scale != 1.0:  # Created in DIPs; realize the outer size in device pixels.
            user32.SetWindowPos(self.hwnd, None, 0, 0, self.px(width), self.px(height),
                                0x0002 | SWP_NOZORDER | SWP_NOACTIVATE)
        dark = ctypes.c_int(1)
        try:
            dwmapi.DwmSetWindowAttribute(self.hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
            if presentation == "splash":
                rounded = ctypes.c_int(2)
                dwmapi.DwmSetWindowAttribute(self.hwnd, 33, ctypes.byref(rounded), ctypes.sizeof(rounded))
        except OSError:
            pass

    def _initialize_runtime(self) -> None:
        try:
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except OSError:
            pass
        controls = INITCOMMONCONTROLSEX(ctypes.sizeof(INITCOMMONCONTROLSEX), 0x00004021)
        comctl32.InitCommonControlsEx(ctypes.byref(controls))
        self._com_initialized = ole32.CoInitializeEx(None, 2) >= 0

    def _query_dpi(self) -> int:
        if _get_dpi_for_window is None:
            return BASE_DPI
        return int(_get_dpi_for_window(self.hwnd)) or BASE_DPI

    def px(self, value: float) -> int:
        """One DIP length in this window's device pixels."""
        return to_physical(value, self.scale)

    def physical_rect(self, key: str) -> tuple[int, int, int, int]:
        return scale_rect(self._rects[key], self.scale)

    def set_client_size(self, width: int, height: int) -> None:
        """Resize a top-level window so its client area matches the DIP contract."""
        if self.owner is not None or self.presentation != "window":
            raise UIRefusal("NATIVE_CLIENT_SIZE_REFUSED", self.presentation)
        rect = wintypes.RECT(0, 0, self.px(width), self.px(height))
        if not user32.AdjustWindowRect(ctypes.byref(rect), self.window_style, False):
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.SetWindowPos(
            self.hwnd, None, 0, 0, rect.right - rect.left, rect.bottom - rect.top,
            0x0002 | SWP_NOZORDER | SWP_NOACTIVATE,
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def set_minimum_client_size(self, width: int, height: int) -> None:
        """Set the top-level resize floor in client-area DIPs."""
        if self.owner is not None or self.presentation != "window" or width < 1 or height < 1:
            raise UIRefusal("NATIVE_MINIMUM_CLIENT_SIZE_REFUSED", f"{width}x{height}")
        self.minimum_client_size = (int(width), int(height))

    def _build_fonts(self) -> dict[str, int]:
        """(Re)create every typography role at the current scale; returns the fonts being replaced."""
        replaced = self._fonts
        self._fonts = {role: self.create_role_font(role, self.scale) for role in self.TYPOGRAPHY}
        self._font, self._font_bold = self._fonts["body"], self._fonts["heading"]
        self._font_title, self._font_metric = self._fonts["title"], self._fonts["metric"]
        return replaced

    def set_font_role(self, key: str, role: str) -> None:
        """Bind a control to a typography role; the window owns the font and rescales it."""
        self._font_roles[key] = role
        user32.SendMessageW(self.controls[key].hwnd, WM_SETFONT, self._fonts[role], 1)

    def relayout(self) -> None:
        """Run the layout handler for the current client area, converted to DIPs."""
        rect = wintypes.RECT()
        if self.layout_handler and user32.GetClientRect(self.hwnd, ctypes.byref(rect)):
            self.layout_handler(int(rect.right / self.scale), int(rect.bottom / self.scale))

    def _apply_dpi(self, dpi: int) -> None:
        if dpi == self.dpi:
            return
        self.dpi, self.scale = dpi, dpi / BASE_DPI
        replaced = self._build_fonts()
        for key, control in self.controls.items():
            user32.SendMessageW(control.hwnd, WM_SETFONT, self._fonts[self._font_roles.get(key, "body")], 0)
            if control.kind == "combo":
                user32.SendMessageW(control.hwnd, 0x0153, WPARAM(-1).value, self.px(26))
            x, y, width, height = self.physical_rect(key)
            user32.SetWindowPos(control.hwnd, None, x, y, max(1, width), max(1, height), SWP_NOZORDER | SWP_NOACTIVATE)
            if control.kind in {"table", "data_grid"}:
                for index, fraction in enumerate((0.32, 0.20, 0.45)):
                    user32.SendMessageW(control.hwnd, 0x101E, index, int(width * fraction))
        for font in replaced.values():
            gdi32.DeleteObject(font)
        user32.InvalidateRect(self.hwnd, None, True)

    def set_review_dpi(self, dpi: int, design_size: tuple[int, int]) -> None:
        """Exercise deterministic DIP scaling for review captures.

        This drives the same font/control scaling path as WM_DPICHANGED. It is a review
        projection, not evidence that a physical monitor delivered the requested DPI.
        """
        if not isinstance(dpi, int) or dpi < 96 or dpi > 384:
            raise ValueError("review DPI must be an integer from 96 through 384")
        self._apply_dpi(dpi)
        width, height = design_size
        user32.SetWindowPos(self.hwnd, None, 0, 0, self.px(width), self.px(height),
                            0x0002 | SWP_NOZORDER | SWP_NOACTIVATE)

    def record_callback_failure(self) -> None:
        self.callback_errors.append(traceback.format_exc(limit=8))
        if self.error_status is not None and self.error_status[0] in self.controls:
            user32.SetWindowTextW(self.controls[self.error_status[0]].hwnd, self.error_status[1])

    def _guard_subclass(self, callback):
        @SUBCLASSPROC
        def guarded(hwnd, message, wparam, lparam, subclass_id, reference):
            try:
                return callback(hwnd, message, wparam, lparam, subclass_id, reference)
            except Exception:
                self.record_callback_failure()
                return 0
        return guarded

    def _register_class(self) -> None:
        global _window_class_registered
        if _window_class_registered:
            return
        klass = WNDCLASSEXW()
        klass.cbSize = ctypes.sizeof(klass)
        klass.style = 0
        klass.lpfnWndProc = _window_proc
        klass.hInstance = self._instance
        klass.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(IDC_ARROW))
        # One process-lifetime class. Per-window brushes are owned by WM_PAINT,
        # never by a class that outlives the window being destroyed.
        klass.hbrBackground = None
        klass.lpszClassName = self._class_name
        if not user32.RegisterClassExW(ctypes.byref(klass)):
            raise ctypes.WinError(ctypes.get_last_error())
        _window_class_registered = True

    def _new_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def _control(self, key: str, kind: str, class_name: str, text: str, style: int,
                 rect: tuple[int, int, int, int], command: Callable[[], None] | None = None,
                 command_notifications: set[int] | None = None, *, subclass: bool = True) -> Control:
        command_id = self._new_id()
        x, y, width, height = scale_rect(rect, self.scale)
        hwnd = user32.CreateWindowExW(
            (WS_EX_RIGHT | WS_EX_RTLREADING) if self.rtl else 0,
            class_name, text, WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS | style, x, y, width, height,
            self.hwnd, ctypes.c_void_p(command_id), self._instance, None,
        )
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        user32.SendMessageW(hwnd, WM_SETFONT, self._font, 1)
        self._font_roles[key] = "body"
        try:
            uxtheme.SetWindowTheme(hwnd, "DarkMode_Explorer", None)
        except OSError:
            pass
        control = Control(key, int(hwnd), kind, command_id)
        self.controls[key] = control
        self._rects[key] = rect
        if not subclass:
            if command is not None:
                self.handlers[command_id] = (command_notifications, command)
            return control
        @self._guard_subclass
        def input_dispatch(handle, message, wparam, lparam, subclass_id, reference):
            self.track_input(message, wparam)
            if message == WM_SETFOCUS and key in self._focus_handlers:
                self._focus_handlers[key]()
            if kind == "button" and message in (WM_MOUSEMOVE, WM_MOUSELEAVE):
                self._track_hover(key, handle, message)
            choice_kinds = {
                "segmented", "tab_bar", "workspace_tabs", "stepper", "dialog", "menu",
                "navigation", "radio_group",
            }
            if kind in choice_kinds and message == WM_LBUTTONDOWN:
                data = self._components.get(key, {})
                options = data.get("options", data.get("steps", data.get("decisions", ())))
                if options:
                    client = wintypes.RECT()
                    user32.GetClientRect(handle, ctypes.byref(client))
                    x = int(lparam) & 0xFFFF
                    index = min(len(options) - 1, max(0, x * len(options) // max(1, client.right)))
                    if kind == "stepper":
                        data["index"] = index
                    else:
                        data["selected"] = options[index]
                    self._choice_pointer_pending.add(key)
                    user32.InvalidateRect(handle, None, False)
            if kind in choice_kinds and message == WM_KEYDOWN and wparam in {37, 38, 39, 40}:
                data = self._components.get(key, {})
                options = data.get("options", data.get("steps", data.get("decisions", ())))
                if options:
                    current = data.get("index", 0) if kind == "stepper" else options.index(data.get("selected", options[0]))
                    delta = -1 if wparam in {37, 38} else 1
                    index = min(len(options) - 1, max(0, current + delta))
                    if kind == "stepper":
                        data["index"] = index
                    else:
                        data["selected"] = options[index]
                    user32.InvalidateRect(handle, None, False)
                    handler = self.handlers.get(command_id)
                    if handler:
                        self._choice_pointer_pending.add(key)
                        handler[1]()
                    return 0
            return comctl32.DefSubclassProc(handle, message, wparam, lparam)
        if not comctl32.SetWindowSubclass(hwnd, input_dispatch, 2, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        self._subclasses.append(input_dispatch)
        if command is not None:
            self.handlers[command_id] = (command_notifications, command)
        return control

    def bind_focus(self, key: str, command: Callable[[], None]) -> None:
        self._focus_handlers[key] = command

    def set_focusable(self, key: str, focusable: bool) -> None:
        hwnd = self.controls[key].hwnd
        style = int(user32.GetWindowLongW(hwnd, -16))
        updated = style | WS_TABSTOP if focusable else style & ~WS_TABSTOP
        if updated != style:
            ctypes.set_last_error(0)
            previous = user32.SetWindowLongW(hwnd, -16, updated)
            if not previous and ctypes.get_last_error():
                raise ctypes.WinError(ctypes.get_last_error())

    def focus(self, key: str) -> None:
        if user32.GetFocus() != self.controls[key].hwnd:
            user32.SetFocus(self.controls[key].hwnd)

    def tab_order(self) -> list[str]:
        by_hwnd = {control.hwnd: key for key, control in self.controls.items()}
        order: list[str] = []
        current = None
        for _ in range(len(self.controls) + 1):
            current = user32.GetNextDlgTabItem(self.hwnd, current, False)
            key = by_hwnd.get(int(current or 0))
            if key is None or key in order:
                break
            order.append(key)
        return order

    def set_accessibility(self, key: str, *, name: str, description: str = "",
                          value: str = "", default_action: str = "") -> None:
        from .win32_accessibility import annotate

        current = (str(name), str(description), str(value), str(default_action))
        if self._accessibility_values.get(key) == current:
            return
        annotate(self.controls[key].hwnd, name=current[0], description=current[1],
                 value=current[2], default_action=current[3])
        self._accessible_keys.add(key)
        self._accessibility_values[key] = current

    def _clear_accessibility(self) -> None:
        if not self._accessible_keys:
            return
        from .win32_accessibility import clear

        for key in list(self._accessible_keys):
            control = self.controls.get(key)
            if control and user32.IsWindow(control.hwnd):
                clear(control.hwnd)
        self._accessible_keys.clear()
        self._accessibility_values.clear()

    def _track_hover(self, key: str, hwnd: int, message: int) -> None:
        """Realize the HOVER state for owner-drawn buttons; repaint only on hover transitions."""
        if message == WM_MOUSEMOVE and self.hovered != key:
            previous, self.hovered = self.hovered, key
            if previous in self.controls:
                user32.InvalidateRect(self.controls[previous].hwnd, None, False)
            event = TRACKMOUSEEVENT(ctypes.sizeof(TRACKMOUSEEVENT), TME_LEAVE, hwnd, 0)
            if not user32.TrackMouseEvent(ctypes.byref(event)):
                self.hovered = None  # Never leave a hover that no WM_MOUSELEAVE can clear.
                raise ctypes.WinError(ctypes.get_last_error())
            user32.InvalidateRect(hwnd, None, False)
        elif message == WM_MOUSELEAVE and self.hovered == key:
            self.hovered = None
            user32.InvalidateRect(hwnd, None, False)

    def set_keyboard_cues(self, visible: bool) -> None:
        if self.keyboard_navigation == visible:
            return
        self.keyboard_navigation = visible
        user32.SendMessageW(self.hwnd, 0x0127, (2 if visible else 1) | (1 << 16), 0)
        focused = user32.GetFocus()
        if focused:
            user32.InvalidateRect(focused, None, False)

    def track_input(self, message: int, key: int) -> None:
        if message in {0x0201, 0x0204, 0x0207}:  # Mouse button down.
            self.set_keyboard_cues(False)
        elif message == 0x0100 and key in {9, 13, 32, 37, 38, 39, 40}:
            self.set_keyboard_cues(True)

    def label(self, key: str, text: str, rect: tuple[int, int, int, int], *, style: str = "body") -> Control:
        control = self._control(key, "label", "STATIC", text, SS_LEFT | 0x0080, rect)
        self.label_styles[control.hwnd] = style
        self.set_font_role(key, style if style in {"title", "heading", "metric"} else "body")
        return control

    def set_control_background(self, key: str, role: str) -> None:
        """Bind a native text control to a declared opaque background token."""
        if role not in self._brushes:
            raise UIRefusal("NATIVE_CONTROL_BACKGROUND_REFUSED", role)
        control = self.controls[key]
        self.control_backgrounds[control.hwnd] = role
        user32.InvalidateRect(control.hwnd, None, True)

    def set_edit_placeholder(self, key: str, text: str) -> None:
        """Set the native cue banner for a single-line edit control."""
        control = self.controls[key]
        if control.kind != "edit":
            raise UIRefusal("NATIVE_EDIT_PLACEHOLDER_REFUSED", key)
        buffer = ctypes.c_wchar_p(str(text))
        user32.SendMessageW(control.hwnd, 0x1501, 1, ctypes.cast(buffer, ctypes.c_void_p).value)

    def edit(self, key: str, text: str, rect: tuple[int, int, int, int], *, multiline: bool = False,
             readonly: bool = False, command: Callable[[str], None] | None = None) -> Control:
        style = WS_TABSTOP | WS_BORDER | (ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL if multiline else ES_AUTOHSCROLL)
        if readonly:
            style |= ES_READONLY
        def commit() -> None:
            if command:
                command(self.text(key))
        return self._control(key, "edit", "EDIT", text, style, rect, commit if command else None,
                             {EN_KILLFOCUS} if command else None)

    def rich_document(self, key: str, text: str, rect: tuple[int, int, int, int]) -> Control:
        """Create a read-only native document surface using the OS RichEdit control."""
        style = WS_TABSTOP | WS_BORDER | ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL | ES_READONLY
        # RichEdit's synchronous messages are kept off the common-control subclass
        # thunk; the semantic realizer owns focus and accessibility explicitly.
        control = self._control(
            key, "rich_document", "RICHEDIT50W", text, style, rect, subclass=False,
        )
        user32.SendMessageW(control.hwnd, EM_SETBKGNDCOLOR, 0, self.COLORS["field"])
        return control

    def set_rich_document(self, key: str, text: str, spans) -> None:
        """Apply bounded character spans to a RichEdit without executing markup."""
        control = self.controls[key]
        if control.kind != "rich_document":
            raise UIRefusal("NATIVE_RICH_DOCUMENT_TARGET_REFUSED", key)
        value = str(text)
        user32.SetWindowTextW(control.hwnd, value)

        def units(offset: int) -> int:
            return len(value[:max(0, offset)].encode("utf-16-le")) // 2

        def apply(start: int, end: int, *, mask: int, effects: int = 0,
                  color: int = 0, face: str = "", offset: int = 0) -> None:
            user32.SendMessageW(control.hwnd, EM_SETSEL, units(start), units(end))
            formatting = CHARFORMATW()
            formatting.cbSize = ctypes.sizeof(CHARFORMATW)
            formatting.dwMask = mask
            formatting.dwEffects = effects
            formatting.crTextColor = color
            formatting.yOffset = offset
            if face:
                formatting.szFaceName = face[:31]
            user32.SendMessageW(
                control.hwnd, EM_SETCHARFORMAT, SCF_SELECTION, ctypes.addressof(formatting),
            )

        apply(0, len(value), mask=CFM_COLOR | CFM_FACE,
              color=self.COLORS["text"], face="Segoe UI")
        for span in spans or ():
            mask = effects = 0
            if getattr(span, "bold", False):
                mask |= CFM_BOLD
                effects |= CFE_BOLD
            if getattr(span, "italic", False):
                mask |= CFM_ITALIC
                effects |= CFE_ITALIC
            if getattr(span, "underline", False):
                mask |= CFM_UNDERLINE
                effects |= CFE_UNDERLINE
            color = self.COLORS["accent"] if getattr(span, "link", False) else 0
            if getattr(span, "link", False):
                mask |= CFM_COLOR
            face = "Cascadia Mono" if getattr(span, "code", False) else ""
            if face:
                mask |= CFM_FACE
            vertical = 60 if getattr(span, "superscript", False) else \
                -40 if getattr(span, "subscript", False) else 0
            if vertical:
                mask |= CFM_OFFSET
            if mask:
                apply(int(span.start), int(span.end), mask=mask, effects=effects,
                      color=color, face=face, offset=vertical)
        user32.SendMessageW(control.hwnd, EM_SETSEL, 0, 0)

    def button(self, key: str, text: str, rect: tuple[int, int, int, int], command: Callable[[], None]) -> Control:
        return self._control(key, "button", "BUTTON", text, WS_TABSTOP | BS_OWNERDRAW, rect, command, {BN_CLICKED})

    def popup_menu(self, key: str, label: str, options, rect,
                   command: Callable[[str], None]) -> Control:
        """Create a button that opens an actual bounded Win32 popup menu."""
        values = tuple(str(value) for value in options)
        if not values:
            raise ValueError("popup menu requires at least one option")

        def activate() -> None:
            bounds = wintypes.RECT()
            user32.GetWindowRect(self.controls[key].hwnd, ctypes.byref(bounds))
            menu = user32.CreatePopupMenu()
            if not menu:
                raise ctypes.WinError()
            try:
                for index, value in enumerate(values, 1):
                    user32.AppendMenuW(menu, 0, index, value)
                choice = user32.TrackPopupMenuEx(menu, 0x0102, bounds.left, bounds.bottom, self.hwnd, None)
            finally:
                user32.DestroyMenu(menu)
            if 1 <= choice <= len(values):
                command(values[choice - 1])

        return self.button(key, label, rect, activate)

    def tooltip_anchor(self, key: str, label: str, tooltip_text: str, rect,
                       command: Callable[[], None]) -> Control:
        """Create a focusable command with a native hover/focus tooltip."""
        control = self.button(key, label, rect, command)
        tooltip = user32.CreateWindowExW(0, "tooltips_class32", None, 0x80000001,
                                        0, 0, 0, 0, self.hwnd, None, self._instance, None)
        if not tooltip:
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_unicode_buffer(str(tooltip_text))
        self._tooltip_buffers.append(buffer)
        info = TOOLINFOW(cbSize=ctypes.sizeof(TOOLINFOW), uFlags=0x0011, hwnd=self.hwnd,
                         uId=control.hwnd, lpszText=ctypes.cast(buffer, wintypes.LPWSTR))
        user32.SendMessageW(tooltip, 0x0432, 0, ctypes.addressof(info))
        return control

    def checkbox(self, key: str, text: str, rect, *, checked=False,
                 command: Callable[[bool], None] | None = None) -> Control:
        def activate() -> None:
            if command:
                command(self.checked(key))

        control = self._control(key, "checkbox", "BUTTON", text, WS_TABSTOP | 3, rect,
                                activate if command else None, {BN_CLICKED} if command else None)
        user32.SendMessageW(control.hwnd, 0x00F1, int(checked), 0)
        return control

    def checked(self, key: str) -> bool:
        return user32.SendMessageW(self.controls[key].hwnd, 0x00F0, 0, 0) == 1

    def set_checked(self, key: str, checked: bool) -> None:
        if self.checked(key) != bool(checked):
            user32.SendMessageW(self.controls[key].hwnd, 0x00F1, int(bool(checked)), 0)

    def copy_text(self, text: str) -> None:
        data = text.encode("utf-16-le") + b"\0\0"
        handle = kernel32.GlobalAlloc(2, len(data))
        if not handle:
            raise ctypes.WinError()
        try:
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                raise ctypes.WinError()
            ctypes.memmove(pointer, data, len(data))
            kernel32.GlobalUnlock(handle)
            if not user32.OpenClipboard(self.hwnd):
                raise OSError("Clipboard is busy; try again")
            try:
                if not user32.EmptyClipboard() or not user32.SetClipboardData(13, handle):
                    raise ctypes.WinError()
                handle = None  # Clipboard now owns the allocation.
            finally:
                user32.CloseClipboard()
        finally:
            if handle:
                kernel32.GlobalFree(handle)

    def show_modeless(self) -> None:
        if self.owner is None:
            raise ValueError("A details window requires an owner")
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.UpdateWindow(self.hwnd)

    def image(self, key: str, image, rect: tuple[int, int, int, int], *, name: str,
              command: Callable[[], None] | None = None) -> Control:
        self._images[key] = image
        control = self._control(key, "image", "BUTTON", name,
                                BS_OWNERDRAW | (WS_TABSTOP if command else 0), rect, command)
        if command:
            tooltip = user32.CreateWindowExW(0, "tooltips_class32", None, 0x80000001,
                                            0, 0, 0, 0, self.hwnd, None, self._instance, None)
            if not tooltip:
                raise ctypes.WinError(ctypes.get_last_error())
            buffer = ctypes.create_unicode_buffer(name)
            self._tooltip_buffers.append(buffer)
            info = TOOLINFOW(cbSize=ctypes.sizeof(TOOLINFOW), uFlags=0x0011, hwnd=self.hwnd,
                             uId=control.hwnd, lpszText=ctypes.cast(buffer, wintypes.LPWSTR))
            user32.SendMessageW(tooltip, 0x0432, 0, ctypes.addressof(info))
        return control

    def set_icon(self, image) -> None:
        for kind, metric in ((0, 49), (1, 11)):
            icon = image.icon(max(16, user32.GetSystemMetrics(metric)))
            user32.SendMessageW(self.hwnd, 0x0080, kind, icon)  # WM_SETICON
            self._icons.append(icon)

    def show_modal(self, focus_key: str) -> None:
        if self.owner is None:
            raise ValueError("A modal requires an owner")
        parent = wintypes.RECT()
        bounds = wintypes.RECT()
        user32.GetWindowRect(self.owner.hwnd, ctypes.byref(parent))
        user32.GetWindowRect(self.hwnd, ctypes.byref(bounds))
        width, height = bounds.right - bounds.left, bounds.bottom - bounds.top
        user32.SetWindowPos(self.hwnd, None, max(0, (parent.left + parent.right - width) // 2),
                           max(0, (parent.top + parent.bottom - height) // 2),
                           width, height, SWP_NOZORDER | SWP_NOACTIVATE)
        self._owner_focus = user32.GetFocus()
        self._owner_keyboard_navigation = self.owner.keyboard_navigation
        self.set_keyboard_cues(self.owner.keyboard_navigation)
        user32.EnableWindow(self.owner.hwnd, False)
        self._modal = True
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.SetFocus(self.controls[focus_key].hwnd)

    def run_modal(self, focus_key: str) -> None:
        self.show_modal(focus_key)
        message = MSG()
        while user32.IsWindow(self.hwnd):
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result <= 0:
                if result == 0:
                    user32.PostQuitMessage(message.wParam)
                break
            self.track_input(message.message, message.wParam)
            if message.message == 0x0100 and message.wParam == 27:
                user32.SendMessageW(self.hwnd, WM_CLOSE, 0, 0)
            elif not user32.IsDialogMessageW(self.hwnd, ctypes.byref(message)):
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        if user32.IsWindow(self.hwnd):
            user32.DestroyWindow(self.hwnd)

    def style_button(self, key: str, *, primary: bool = False, selected: bool = False,
                     danger: bool = False) -> None:
        if primary and danger:
            raise ValueError("a button cannot be both primary and danger")
        style = "primary" if primary else "danger" if danger else "secondary"
        if self.button_styles.get(key, "secondary") == style and (key in self.selected_buttons) == selected:
            return
        self.button_styles[key] = style
        self.selected_buttons.discard(key)
        if selected:
            self.selected_buttons.add(key)
        user32.InvalidateRect(self.controls[key].hwnd, None, False)

    def table(self, key: str, columns: list[str], rect: tuple[int, int, int, int], *,
              command: Callable[[str], None] | None = None, kind: str = "table") -> Control:
        # The header is a child HWND. Without clipping, composited painting can
        # repeatedly invalidate the table and header through each other's area.
        control = self._control(key, kind, "SysListView32", "",
                                WS_TABSTOP | WS_CLIPCHILDREN | 0x0001 | 0x0004 | 0x0008 | 0x1000, rect)
        self._table_rows[int(control.hwnd)] = ()
        if command is not None:
            self._table_callbacks[int(control.hwnd)] = command
        user32.SendMessageW(control.hwnd, 0x1036, 0, 0x00000020 | 0x00010000)
        for message, color in ((0x1001, "canvas"), (0x1024, "text"), (0x1026, "canvas")):
            user32.SendMessageW(control.hwnd, message, 0, self.COLORS[color])
        for index, title in enumerate(columns):
            buffer = ctypes.create_unicode_buffer(title)
            column = LVCOLUMNW(mask=0x000F, cx=200, pszText=ctypes.cast(buffer, wintypes.LPWSTR), iSubItem=index)
            user32.SendMessageW(control.hwnd, 0x1061, index, ctypes.addressof(column))
        header = user32.SendMessageW(control.hwnd, 0x101F, 0, 0)
        def paint_header(hdc: int, hwnd: int) -> None:
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            user32.FillRect(hdc, ctypes.byref(rect), self._brushes["raised"])
            gdi32.SetTextColor(hdc, self.COLORS["quiet"])
            gdi32.SetBkMode(hdc, TRANSPARENT)
            gdi32.SelectObject(hdc, self._font)
            for index, title in enumerate(columns):
                cell = wintypes.RECT()
                user32.SendMessageW(hwnd, 0x1207, index, ctypes.addressof(cell))
                cell.left += self.px(8)
                user32.DrawTextW(hdc, title, -1, ctypes.byref(cell), DT_LEFT | DT_VCENTER | DT_SINGLELINE)
        self._custom_paint(header, paint_header)
        return control

    def _custom_paint(self, hwnd: int, painter: Callable[[int, int], None]) -> None:
        @self._guard_subclass
        def dispatch(handle, message, wparam, lparam, subclass_id, reference):
            if message == 0x0014:  # The custom painter fills its complete client area.
                return 1
            if message == WM_PAINT:
                paint = PAINTSTRUCT()
                hdc = user32.BeginPaint(handle, ctypes.byref(paint))
                try:
                    painter(hdc, handle)
                finally:
                    user32.EndPaint(handle, ctypes.byref(paint))
                return 0
            if message == 0x0318:  # WM_PRINTCLIENT uses the caller's offscreen DC.
                painter(wparam, handle)
                return 0
            return comctl32.DefSubclassProc(handle, message, wparam, lparam)
        if not comctl32.SetWindowSubclass(hwnd, dispatch, 1, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        self._subclasses.append(dispatch)

    def set_rows(self, key: str, rows: list[tuple[str, ...]]) -> None:
        hwnd = self.controls[key].hwnd
        rows = tuple(tuple(str(cell) for cell in row) for row in rows)
        if self._table_rows.get(int(hwnd)) == rows:
            return
        self._table_rows[int(hwnd)] = rows
        visible = bool(user32.GetWindowLongW(hwnd, -16) & WS_VISIBLE)
        if visible:
            user32.SendMessageW(hwnd, 0x000B, 0, 0)
        try:
            # LVS_OWNERDATA asks for visible cells via LVN_GETDISPINFOW.
            state = LVITEMW(state=0, stateMask=3)
            user32.SendMessageW(hwnd, 0x102B, WPARAM(-1).value, ctypes.addressof(state))
            user32.SendMessageW(hwnd, 0x102F, len(rows), 0x0002)
        finally:
            if visible:
                user32.SendMessageW(hwnd, 0x000B, 1, 0)
                user32.InvalidateRect(hwnd, None, False)

    def set_table_column_widths(self, key: str, widths) -> None:
        """Set explicit ListView column widths in DIPs for responsive layouts."""
        hwnd = self.controls[key].hwnd
        for index, width in enumerate(widths):
            if int(width) < 24:
                raise UIRefusal("NATIVE_TABLE_COLUMN_WIDTH_REFUSED", f"{key}:{index}")
            user32.SendMessageW(hwnd, 0x101E, index, self.px(int(width)))  # LVM_SETCOLUMNWIDTH

    def set_table_selection(self, key: str, value: str) -> None:
        hwnd = self.controls[key].hwnd
        rows = self._table_rows.get(int(hwnd), ())
        target = next((index for index, row in enumerate(rows) if row and row[0] == str(value)), -1)
        self._table_sync.add(int(hwnd))
        try:
            state = LVITEMW(state=0, stateMask=0x0002)
            user32.SendMessageW(hwnd, 0x102B, WPARAM(-1).value, ctypes.addressof(state))
            if target >= 0:
                state.state = 0x0002
                user32.SendMessageW(hwnd, 0x102B, target, ctypes.addressof(state))
                user32.SendMessageW(hwnd, 0x1013, target, 0)
        finally:
            self._table_sync.discard(int(hwnd))

    def combo(self, key: str, values: list[str], rect: tuple[int, int, int, int], *, selected: int = 0,
              command: Callable[[str], None] | None = None, editable: bool = False) -> Control:
        def activate() -> None:
            if command:
                command(self.combo_value(key))

        style = WS_TABSTOP | CBS_HASSTRINGS | (CBS_DROPDOWN if editable else CBS_DROPDOWNLIST | CBS_OWNERDRAWFIXED)
        notifications = {CBN_SELCHANGE, CBN_EDITCHANGE} if editable else {CBN_SELCHANGE}
        control = self._control(key, "combo", "COMBOBOX", "", style, rect,
                                activate if command else None, notifications if command else None)
        for value in values:
            buffer = ctypes.create_unicode_buffer(value)
            user32.SendMessageW(control.hwnd, CB_ADDSTRING, 0, ctypes.addressof(buffer))
        user32.SendMessageW(control.hwnd, CB_SETCURSEL, selected, 0)
        user32.SendMessageW(control.hwnd, 0x0153, WPARAM(-1).value, self.px(26))
        if not editable:
            def paint_combo(hdc: int, hwnd: int) -> None:
                rect = wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rect))
                item = DRAWITEMSTRUCT(CtlType=ODT_COMBOBOX, itemID=0xFFFFFFFF, hwndItem=hwnd, hDC=hdc, rcItem=rect)
                self._draw_combo(item)
                arrow = wintypes.RECT(rect.right - self.px(24), rect.top, rect.right - self.px(4), rect.bottom)
                user32.DrawTextW(hdc, "\u2304", -1, ctypes.byref(arrow), DT_CENTER | DT_VCENTER | DT_SINGLELINE)
            self._custom_paint(control.hwnd, paint_combo)
        return control

    def listbox(self, key: str, values: list[str], rect: tuple[int, int, int, int], *, selected: int = 0,
                command: Callable[[str], None] | None = None, kind: str = "list") -> Control:
        def activate() -> None:
            if command:
                command(self.list_value(key))

        control = self._control(
            key, kind, "LISTBOX", "", WS_TABSTOP | WS_BORDER | WS_VSCROLL | LBS_NOTIFY | LBS_NOINTEGRALHEIGHT,
            rect, activate if command else None, {LBN_SELCHANGE} if command else None,
        )
        for value in values:
            buffer = ctypes.create_unicode_buffer(str(value))
            user32.SendMessageW(control.hwnd, LB_ADDSTRING, 0, ctypes.addressof(buffer))
        user32.SendMessageW(control.hwnd, LB_SETCURSEL, selected, 0)
        return control

    def list_value(self, key: str) -> str:
        hwnd = self.controls[key].hwnd
        index = int(user32.SendMessageW(hwnd, LB_GETCURSEL, 0, 0))
        if index < 0:
            return ""
        length = int(user32.SendMessageW(hwnd, LB_GETTEXTLEN, index, 0))
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.SendMessageW(hwnd, LB_GETTEXT, index, ctypes.addressof(buffer))
        return buffer.value

    def set_list_value(self, key: str, value: str) -> None:
        hwnd = self.controls[key].hwnd
        count = int(user32.SendMessageW(hwnd, 0x018B, 0, 0))
        for index in range(max(0, count)):
            length = int(user32.SendMessageW(hwnd, LB_GETTEXTLEN, index, 0))
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.SendMessageW(hwnd, LB_GETTEXT, index, ctypes.addressof(buffer))
            if buffer.value == str(value):
                user32.SendMessageW(hwnd, LB_SETCURSEL, index, 0)
                return

    def set_list_items(self, key: str, values: list[str], selected: str | None = None) -> None:
        """Replace a list control's bounded items while preserving one explicit selection."""
        hwnd = self.controls[key].hwnd
        user32.SendMessageW(hwnd, 0x0184, 0, 0)  # LB_RESETCONTENT
        for value in values:
            buffer = ctypes.create_unicode_buffer(str(value))
            user32.SendMessageW(hwnd, LB_ADDSTRING, 0, ctypes.addressof(buffer))
        if values:
            self.set_list_value(key, selected if selected in values else values[0])

    def progress(self, key: str, rect: tuple[int, int, int, int]) -> Control:
        control = self._control(key, "progress", "msctls_progress32", "", 0, rect)
        uxtheme.SetWindowTheme(control.hwnd, "", "")
        user32.SendMessageW(control.hwnd, PBM_SETRANGE32, 0, 100)
        user32.SendMessageW(control.hwnd, PBM_SETBKCOLOR, 0, self.COLORS["field"])
        user32.SendMessageW(control.hwnd, PBM_SETBARCOLOR, 0, self.COLORS["accent"])
        return control

    def text(self, key: str) -> str:
        hwnd = self.controls[key].hwnd
        length = int(user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0))
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.SendMessageW(hwnd, WM_GETTEXT, length + 1, ctypes.addressof(buffer))
        return buffer.value

    def set_text(self, key: str, value: str) -> None:
        if self.text(key) != str(value):
            user32.SetWindowTextW(self.controls[key].hwnd, str(value))

    def combo_value(self, key: str) -> str:
        control = self.controls[key]
        index = int(user32.SendMessageW(control.hwnd, CB_GETCURSEL, 0, 0))
        if index < 0:
            return self.text(key)
        length = int(user32.SendMessageW(control.hwnd, 0x0149, index, 0))
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.SendMessageW(control.hwnd, 0x0148, index, ctypes.addressof(buffer))
        return buffer.value

    def set_combo_value(self, key: str, value: str) -> None:
        control = self.controls[key]
        count = int(user32.SendMessageW(control.hwnd, 0x0146, 0, 0))  # CB_GETCOUNT
        for index in range(max(0, count)):
            length = int(user32.SendMessageW(control.hwnd, 0x0149, index, 0))
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.SendMessageW(control.hwnd, 0x0148, index, ctypes.addressof(buffer))
            if buffer.value == str(value):
                user32.SendMessageW(control.hwnd, CB_SETCURSEL, index, 0)
                user32.InvalidateRect(control.hwnd, None, False)
                return

    def set_combo_items(self, key: str, values, selected: str | None = None) -> None:
        """Replace a combo's bounded choices and retain one explicit valid selection."""
        values = tuple(str(value) for value in values)
        if not values:
            raise ValueError("combo requires at least one value")
        control = self.controls[key]
        current_values = []
        count = int(user32.SendMessageW(control.hwnd, 0x0146, 0, 0))
        for index in range(max(0, count)):
            length = int(user32.SendMessageW(control.hwnd, 0x0149, index, 0))
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.SendMessageW(control.hwnd, 0x0148, index, ctypes.addressof(buffer))
            current_values.append(buffer.value)
        selected = str(selected) if selected in values else values[0]
        if tuple(current_values) == values:
            self.set_combo_value(key, selected)
            return
        user32.SendMessageW(control.hwnd, 0x014B, 0, 0)  # CB_RESETCONTENT
        for value in values:
            buffer = ctypes.create_unicode_buffer(value)
            user32.SendMessageW(control.hwnd, CB_ADDSTRING, 0, ctypes.addressof(buffer))
        self.set_combo_value(key, selected)

    def set_enabled(self, key: str, enabled: bool) -> None:
        hwnd = self.controls[key].hwnd
        if bool(user32.IsWindowEnabled(hwnd)) != bool(enabled):
            user32.EnableWindow(hwnd, bool(enabled))

    def show(self, key: str, visible: bool) -> None:
        self.set_visibility({key: visible})

    def set_visibility(self, values: dict[str, bool]) -> None:
        changes = [(self.controls[key].hwnd, visible) for key, visible in values.items()
                   if bool(user32.GetWindowLongW(self.controls[key].hwnd, -16) & WS_VISIBLE) != visible]
        if not changes:
            return
        batch = user32.BeginDeferWindowPos(len(changes))
        if not batch:
            raise ctypes.WinError(ctypes.get_last_error())
        for hwnd, visible in changes:
            flags = 0x0001 | 0x0002 | SWP_NOZORDER | SWP_NOACTIVATE | (0x0040 if visible else 0x0080)
            batch = user32.DeferWindowPos(batch, hwnd, None, 0, 0, 0, 0, flags)
            if not batch:
                raise ctypes.WinError(ctypes.get_last_error())
        if not user32.EndDeferWindowPos(batch):
            raise ctypes.WinError(ctypes.get_last_error())

    def move(self, key: str, rect: tuple[int, int, int, int]) -> None:
        """Place a control at a DIP rect (layout units); realization converts to device pixels."""
        if self._rects.get(key) == rect:
            return
        x, y, width, height = scale_rect(rect, self.scale)
        if not user32.SetWindowPos(self.controls[key].hwnd, None, x, y, max(1, width), max(1, height), SWP_NOZORDER | SWP_NOACTIVATE):
            raise ctypes.WinError(ctypes.get_last_error())
        self._rects[key] = rect
        if self.controls[key].kind in {"table", "data_grid"}:
            for index, fraction in enumerate((0.32, 0.20, 0.45)):
                user32.SendMessageW(self.controls[key].hwnd, 0x101E, index, int(width * fraction))

    def move_many(self, rects: dict[str, tuple[int, int, int, int]]) -> None:
        """Move existing child HWNDs as one redraw-bounded resize transaction."""
        changes = [(key, rect) for key, rect in rects.items() if self._rects.get(key) != rect]
        if not changes:
            return
        batch = user32.BeginDeferWindowPos(len(changes))
        if not batch:
            raise ctypes.WinError(ctypes.get_last_error())
        for key, rect in changes:
            x, y, width, height = scale_rect(rect, self.scale)
            batch = user32.DeferWindowPos(
                batch, self.controls[key].hwnd, None, x, y, max(1, width), max(1, height),
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
            if not batch:
                raise ctypes.WinError(ctypes.get_last_error())
        if not user32.EndDeferWindowPos(batch):
            raise ctypes.WinError(ctypes.get_last_error())
        for key, rect in changes:
            self._rects[key] = rect
            if self.controls[key].kind in {"table", "data_grid"}:
                width = rect[2]
                for index, fraction in enumerate((0.32, 0.20, 0.45)):
                    user32.SendMessageW(self.controls[key].hwnd, 0x101E, index, int(width * fraction))

    def send_to_back(self, key: str) -> None:
        """Place a structural control behind its siblings without changing geometry."""
        flags = 0x0001 | 0x0002 | SWP_NOACTIVATE
        if not user32.SetWindowPos(self.controls[key].hwnd, 1, 0, 0, 0, 0, flags):
            raise ctypes.WinError(ctypes.get_last_error())

    def set_progress(self, key: str, percent: float) -> None:
        value = int(max(0, min(100, percent)))
        if self._progress_values.get(key) != value:
            user32.SendMessageW(self.controls[key].hwnd, PBM_SETPOS, value, 0)
            self._progress_values[key] = value

    def set_progress_state(self, key: str, mode: str, percent: float = 0) -> None:
        """Apply determinate, indeterminate, paused, or failed native progress behavior."""
        if mode not in {"determinate", "indeterminate", "paused", "failed"}:
            raise UIRefusal("NATIVE_PROGRESS_STATE_REFUSED", mode)
        hwnd = self.controls[key].hwnd
        style = int(user32.GetWindowLongW(hwnd, -16))
        updated = style | 0x0008 if mode == "indeterminate" else style & ~0x0008
        if updated != style:
            user32.SetWindowLongW(hwnd, -16, updated)
            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0027)
        user32.SendMessageW(hwnd, 0x040A, int(mode == "indeterminate"), 30)
        user32.SendMessageW(hwnd, 0x0410, 2 if mode == "failed" else 3 if mode == "paused" else 1, 0)
        if mode != "indeterminate":
            self.set_progress(key, percent)

    def invalidate(self) -> None:
        user32.InvalidateRect(self.hwnd, None, False)

    def redraw(self) -> None:
        """Synchronously repaint the owned window and its child HWNDs for evidence capture."""
        flags = 0x0001 | 0x0004 | 0x0080 | 0x0100  # INVALIDATE | ERASE | ALLCHILDREN | UPDATENOW
        if not user32.RedrawWindow(self.hwnd, None, None, flags):
            raise ctypes.WinError(ctypes.get_last_error())

    def set_timer(self, milliseconds: int, handler: Callable[[], None]) -> None:
        self.timer_handler = handler
        user32.SetTimer(self.hwnd, 1, milliseconds, None)

    @staticmethod
    def _com_method(interface: ctypes.c_void_p, index: int, restype, *argtypes):
        vtable = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])

    @staticmethod
    def _check_hresult(value: int, operation: str) -> None:
        if value < 0:
            raise OSError(f"{operation} failed (HRESULT 0x{value & 0xFFFFFFFF:08X})")

    def _browse_folder_modern(self, title: str, initial: str = "") -> str | None:
        """Use Windows' current filesystem folder dialog through the stdlib ctypes COM ABI."""
        clsid = GUID.parse("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")
        dialog_iid = GUID.parse("D57C7288-D4AD-4768-BE02-9D969532D960")
        shell_item_iid = GUID.parse("43826D1E-E718-42EE-BC55-A1E261C37BFE")
        dialog = ctypes.c_void_p()
        self._check_hresult(ole32.CoCreateInstance(ctypes.byref(clsid), None, CLSCTX_INPROC_SERVER,
                                                   ctypes.byref(dialog_iid), ctypes.byref(dialog)),
                            "Create folder dialog")
        try:
            options = wintypes.DWORD()
            get_options = self._com_method(dialog, 10, ctypes.c_long, ctypes.POINTER(wintypes.DWORD))
            set_options = self._com_method(dialog, 9, ctypes.c_long, wintypes.DWORD)
            set_title = self._com_method(dialog, 17, ctypes.c_long, wintypes.LPCWSTR)
            self._check_hresult(get_options(dialog, ctypes.byref(options)), "Read folder dialog options")
            self._check_hresult(set_options(dialog, options.value | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM |
                                            FOS_PATHMUSTEXIST), "Configure folder dialog")
            self._check_hresult(set_title(dialog, title), "Set folder dialog title")
            start = Path(initial).expanduser() if initial else None
            if start and start.is_dir():
                item = ctypes.c_void_p()
                created = shell32.SHCreateItemFromParsingName(str(start.resolve()), None,
                                                               ctypes.byref(shell_item_iid), ctypes.byref(item))
                if created >= 0:
                    try:
                        set_folder = self._com_method(dialog, 12, ctypes.c_long, ctypes.c_void_p)
                        self._check_hresult(set_folder(dialog, item), "Set initial folder")
                    finally:
                        self._com_method(item, 2, wintypes.ULONG)(item)
            show = self._com_method(dialog, 3, ctypes.c_long, wintypes.HWND)
            shown = show(dialog, self.hwnd)
            if shown == ERROR_CANCELLED_HRESULT:
                return None
            self._check_hresult(shown, "Show folder dialog")
            selected = ctypes.c_void_p()
            get_result = self._com_method(dialog, 20, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))
            self._check_hresult(get_result(dialog, ctypes.byref(selected)), "Read selected folder")
            try:
                value = ctypes.c_void_p()
                get_name = self._com_method(selected, 5, ctypes.c_long, wintypes.DWORD,
                                            ctypes.POINTER(ctypes.c_void_p))
                self._check_hresult(get_name(selected, SIGDN_FILESYSPATH, ctypes.byref(value)),
                                    "Resolve selected folder")
                try:
                    return ctypes.wstring_at(value)
                finally:
                    ole32.CoTaskMemFree(value)
            finally:
                self._com_method(selected, 2, wintypes.ULONG)(selected)
        finally:
            self._com_method(dialog, 2, wintypes.ULONG)(dialog)

    def _browse_folder_legacy(self, title: str, initial: str = "") -> str | None:
        opened = False
        initial_buffer = ctypes.create_unicode_buffer(initial) if initial else None

        @BFFCALLBACK
        def callback(hwnd, message, lparam, data):
            nonlocal opened
            if message == BFFM_INITIALIZED:
                opened = True
                if initial_buffer is not None:
                    user32.SendMessageW(hwnd, BFFM_SETSELECTIONW, 1, ctypes.addressof(initial_buffer))
            return 0

        display = ctypes.create_unicode_buffer(MAX_PATH)
        info = BROWSEINFOW(self.hwnd, None, display, title, BIF_RETURNONLYFSDIRS | BIF_USENEWUI,
                           ctypes.cast(callback, ctypes.c_void_p), 0, 0)
        item = shell32.SHBrowseForFolderW(ctypes.byref(info))
        if not item:
            if not opened:
                raise OSError("Legacy folder dialog did not open")
            return None
        path = ctypes.create_unicode_buffer(32768)
        try:
            if shell32.SHGetPathFromIDListW(item, path):
                return path.value
            return None
        finally:
            ole32.CoTaskMemFree(item)

    def browse_folder(self, title: str, initial: str = "") -> str | None:
        try:
            return self._browse_folder_modern(title, initial)
        except OSError as modern_error:
            try:
                return self._browse_folder_legacy(title, initial)
            except OSError as legacy_error:
                raise OSError(f"Native folder dialogs failed: {modern_error}; {legacy_error}") from legacy_error

    def browse_file(self, title: str, initial: str = "") -> str | None:
        """Select one existing filesystem file through the native shell dialog."""
        clsid = GUID.parse("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")
        dialog_iid = GUID.parse("D57C7288-D4AD-4768-BE02-9D969532D960")
        shell_item_iid = GUID.parse("43826D1E-E718-42EE-BC55-A1E261C37BFE")
        dialog = ctypes.c_void_p()
        self._check_hresult(ole32.CoCreateInstance(ctypes.byref(clsid), None, CLSCTX_INPROC_SERVER,
                                                   ctypes.byref(dialog_iid), ctypes.byref(dialog)),
                            "Create file dialog")
        try:
            options = wintypes.DWORD()
            get_options = self._com_method(dialog, 10, ctypes.c_long, ctypes.POINTER(wintypes.DWORD))
            set_options = self._com_method(dialog, 9, ctypes.c_long, wintypes.DWORD)
            set_title = self._com_method(dialog, 17, ctypes.c_long, wintypes.LPCWSTR)
            self._check_hresult(get_options(dialog, ctypes.byref(options)), "Read file dialog options")
            self._check_hresult(set_options(dialog, options.value | FOS_FORCEFILESYSTEM |
                                            FOS_PATHMUSTEXIST | FOS_FILEMUSTEXIST),
                                "Configure file dialog")
            self._check_hresult(set_title(dialog, title), "Set file dialog title")
            start = Path(initial).expanduser() if initial else None
            folder = start if start and start.is_dir() else start.parent if start else None
            if folder and folder.is_dir():
                item = ctypes.c_void_p()
                created = shell32.SHCreateItemFromParsingName(str(folder.resolve()), None,
                                                               ctypes.byref(shell_item_iid), ctypes.byref(item))
                if created >= 0:
                    try:
                        set_folder = self._com_method(dialog, 12, ctypes.c_long, ctypes.c_void_p)
                        self._check_hresult(set_folder(dialog, item), "Set initial file folder")
                    finally:
                        self._com_method(item, 2, wintypes.ULONG)(item)
            show = self._com_method(dialog, 3, ctypes.c_long, wintypes.HWND)
            shown = show(dialog, self.hwnd)
            if shown == ERROR_CANCELLED_HRESULT:
                return None
            self._check_hresult(shown, "Show file dialog")
            selected = ctypes.c_void_p()
            get_result = self._com_method(dialog, 20, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))
            self._check_hresult(get_result(dialog, ctypes.byref(selected)), "Read selected file")
            try:
                value = ctypes.c_void_p()
                get_name = self._com_method(selected, 5, ctypes.c_long, wintypes.DWORD,
                                            ctypes.POINTER(ctypes.c_void_p))
                self._check_hresult(get_name(selected, SIGDN_FILESYSPATH, ctypes.byref(value)),
                                    "Resolve selected file")
                try:
                    selected_path = ctypes.wstring_at(value)
                finally:
                    ole32.CoTaskMemFree(value)
            finally:
                self._com_method(selected, 2, wintypes.ULONG)(selected)
            if not Path(selected_path).is_file():
                raise OSError("Native file dialog did not return an existing file")
            return selected_path
        finally:
            self._com_method(dialog, 2, wintypes.ULONG)(dialog)

    def message(self, title: str, text: str, *, error: bool = False) -> None:
        user32.MessageBoxW(self.hwnd, text, title, 0x10 if error else 0x40)

    def confirm(self, title: str, text: str) -> bool:
        return user32.MessageBoxW(self.hwnd, text, title, 0x134) == 6

    def _context_menu(self, target, coordinates):
        x, y = ctypes.c_short(coordinates & 0xFFFF).value, ctypes.c_short((coordinates >> 16) & 0xFFFF).value
        for key, provider in self.context_menus.items():
            hwnd = self.controls[key].hwnd
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            if target != hwnd and not (rect.left <= x < rect.right and rect.top <= y < rect.bottom):
                continue
            items = provider()
            if not items:
                return 0
            if x == y == -1:
                x, y = rect.left, rect.bottom
            menu = user32.CreatePopupMenu()
            if not menu:
                raise ctypes.WinError()
            try:
                for index, (label, _) in enumerate(items, 1):
                    user32.AppendMenuW(menu, 0, index, label)
                choice = user32.TrackPopupMenuEx(menu, 0x0102, x, y, self.hwnd, None)
            finally:
                user32.DestroyMenu(menu)
            if 1 <= choice <= len(items):
                items[choice - 1][1]()
            return 0
        return user32.DefWindowProcW(self.hwnd, 0x007B, target, coordinates)

    def _dispatch(self, message: int, wparam: int, lparam: int) -> int:
        if message == 0x007B:
            return self._context_menu(wparam, lparam)
        if message == 0x0024:
            if self.owner is not None:
                return user32.DefWindowProcW(self.hwnd, message, wparam, lparam)
            info = ctypes.cast(lparam, ctypes.POINTER(MINMAXINFO)).contents
            minimum_width, minimum_height = self.minimum_client_size
            rect = wintypes.RECT(0, 0, self.px(minimum_width), self.px(minimum_height))
            user32.AdjustWindowRect(ctypes.byref(rect), WS_OVERLAPPEDWINDOW, False)
            info.minimum_track.x = rect.right - rect.left
            info.minimum_track.y = rect.bottom - rect.top
            return 0
        if message == WM_COMMAND:
            control_id = int(wparam) & 0xFFFF
            notification = (int(wparam) >> 16) & 0xFFFF
            binding = self.handlers.get(control_id)
            if binding and (binding[0] is None or notification in binding[0]):
                binding[1]()
                return 0
        elif message == 0x004E and lparam:  # WM_NOTIFY
            header = ctypes.cast(lparam, ctypes.POINTER(NMHDR)).contents
            if header.code == (-177 & 0xFFFFFFFF):  # LVN_GETDISPINFOW
                info = ctypes.cast(lparam, ctypes.POINTER(NMLVDISPINFOW)).contents
                rows = self._table_rows.get(int(header.hwndFrom), ())
                item = info.item
                if item.mask & 1:
                    text = rows[item.iItem][item.iSubItem] if 0 <= item.iItem < len(rows) and 0 <= item.iSubItem < len(rows[item.iItem]) else ""
                    buffer = ctypes.create_unicode_buffer(text)
                    self._table_text_buffers.append(buffer)
                    info.item.pszText = ctypes.cast(buffer, wintypes.LPWSTR)
                return 0
            if header.code == (-179 & 0xFFFFFFFF):  # LVN_ODFINDITEMW: keyboard prefix search
                info = ctypes.cast(lparam, ctypes.POINTER(NMLVFINDITEMW)).contents
                rows = self._table_rows.get(int(header.hwndFrom), ())
                if not rows or not info.lvfi.psz or info.lvfi.flags & (1 | 0x40):
                    return -1
                needle = info.lvfi.psz.casefold()
                start = min(len(rows), max(0, info.iStart))
                count = len(rows) if info.lvfi.flags & 0x20 else len(rows) - start
                for offset in range(count):
                    index = (start + offset) % len(rows)
                    text = rows[index][0].casefold() if rows[index] else ""
                    if text.startswith(needle) if info.lvfi.flags & (4 | 8) else text == needle:
                        return index
                return -1
            if header.code == (-101 & 0xFFFFFFFF) and int(header.hwndFrom) in self._table_callbacks:
                info = ctypes.cast(lparam, ctypes.POINTER(NMLISTVIEW)).contents
                selected = bool(info.uNewState & 0x0002) and not bool(info.uOldState & 0x0002)
                rows = self._table_rows.get(int(header.hwndFrom), ())
                if selected and int(header.hwndFrom) not in self._table_sync \
                        and 0 <= info.iItem < len(rows) and rows[info.iItem]:
                    self._table_callbacks[int(header.hwndFrom)](rows[info.iItem][0])
                return 0
        elif message == WM_TIMER:
            if self.timer_handler:
                self.timer_handler()
            return 0
        elif message == WM_SIZE:
            if int(wparam) == 1:  # SIZE_MINIMIZED has no usable client area.
                return 0
            if self.layout_handler:
                self.layout_handler(int((int(lparam) & 0xFFFF) / self.scale),
                                    int(((int(lparam) >> 16) & 0xFFFF) / self.scale))
            return 0
        elif message == WM_DPICHANGED:
            self._apply_dpi(int(wparam) & 0xFFFF)
            suggested = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
            user32.SetWindowPos(self.hwnd, None, suggested.left, suggested.top, suggested.right - suggested.left,
                                suggested.bottom - suggested.top, SWP_NOZORDER | SWP_NOACTIVATE)
            return 0
        elif message == WM_DRAWITEM:
            return self._draw_item(lparam)
        elif message in {WM_CTLCOLORSTATIC, WM_CTLCOLOREDIT, WM_CTLCOLORLISTBOX, WM_CTLCOLORBTN, WM_CTLCOLORDLG}:
            hdc = int(wparam)
            style = self.label_styles.get(int(lparam), "body")
            color = "accent" if style in {"metric", "accent"} else "quiet" if style == "quiet" else "text"
            background = self.control_backgrounds.get(
                int(lparam), "canvas" if message == WM_CTLCOLORSTATIC else "field",
            )
            gdi32.SetTextColor(hdc, self.COLORS[color])
            gdi32.SetBkColor(hdc, self.COLORS[background])
            gdi32.SetBkMode(hdc, TRANSPARENT if message == WM_CTLCOLORSTATIC else 2)
            return int(self._brushes[background])
        elif message == WM_PAINT:
            paint = PAINTSTRUCT()
            hdc = user32.BeginPaint(self.hwnd, ctypes.byref(paint))
            user32.FillRect(hdc, ctypes.byref(paint.rcPaint), self._brushes["canvas"])
            user32.EndPaint(self.hwnd, ctypes.byref(paint))
            return 0
        elif message == WM_CLOSE:
            if self.close_handler:
                if self.close_handler() is False:
                    return 0
            self._clear_accessibility()
            user32.DestroyWindow(self.hwnd)
            return 0
        elif message == WM_DESTROY:
            for icon in self._icons:
                user32.DestroyIcon(icon)
            self._icons.clear()
            if self.owner is None:
                user32.PostQuitMessage(0)
            elif self._modal and user32.IsWindow(self.owner.hwnd):
                user32.EnableWindow(self.owner.hwnd, True)
                self.owner.set_keyboard_cues(self._owner_keyboard_navigation)
                if self._owner_focus and user32.IsWindow(self._owner_focus):
                    user32.SetFocus(self._owner_focus)
            return 0
        elif message == 0x0082:  # WM_NCDESTROY follows destruction of the child controls.
            result = user32.DefWindowProcW(self.hwnd, message, wparam, lparam)
            for handle in [*self._brushes.values(), *self._fonts.values()]:
                gdi32.DeleteObject(handle)
            if self._vector is not None:
                self._vector.close()
                self._vector = None
            _windows.pop(int(self.hwnd), None)
            if self._com_initialized:
                ole32.CoUninitialize()
                self._com_initialized = False
            return result
        return user32.DefWindowProcW(self.hwnd, message, wparam, lparam)

    def _draw_item(self, pointer: int) -> int:
        item = ctypes.cast(pointer, ctypes.POINTER(DRAWITEMSTRUCT)).contents
        if item.CtlType == ODT_COMBOBOX:
            return self._draw_combo(item)
        key = next((key for key, control in self.controls.items() if control.hwnd == item.hwndItem), "")
        if item.CtlType == ODT_LISTBOX and key and self.controls[key].kind == "catalog_list":
            return self._draw_catalog_item(item)
        if item.CtlType == ODT_STATIC or key in self._components:
            return self._draw_component(item)
        selected = bool(item.itemState & ODS_SELECTED)
        disabled = bool(item.itemState & ODS_DISABLED)
        if key in self._images:
            rect = item.rcItem
            user32.FillRect(item.hDC, ctypes.byref(rect), self._brushes["canvas"])
            inset = self.px(2)
            side = min(rect.right - rect.left, rect.bottom - rect.top) - 2 * inset
            self._images[key].draw(item.hDC, (rect.left + inset, rect.top + inset, side, side))
            if item.itemState & 0x0010 and self.keyboard_navigation:
                self._round_rect(item.hDC, (rect.left, rect.top, rect.right, rect.bottom), None, "focus")
            return 1
        style = self.button_styles.get(key, "secondary")
        primary = style == "primary" and not disabled
        danger = style == "danger" and not disabled
        active = key in self.selected_buttons
        hovered = key == self.hovered
        # State precedence: DISABLED > PRESSED/selected > HOVER > idle primary/secondary.
        fill = ("field" if disabled else "selection" if selected or active
                else "refused" if danger and hovered
                else ("accent_hover" if primary else "surface_hover") if hovered
                else "accent" if primary else "field" if danger else "raised")
        border = ("focus" if item.itemState & 0x0010 and self.keyboard_navigation
                  else "refused" if danger else "accent" if active or primary else "border")
        background = self.control_backgrounds.get(item.hwndItem, "canvas")
        user32.FillRect(item.hDC, ctypes.byref(item.rcItem), self._brushes[background])
        self._round_rect(item.hDC, (item.rcItem.left, item.rcItem.top, item.rcItem.right, item.rcItem.bottom),
                         fill, border)
        text_color = ("quiet" if disabled else "canvas" if (primary or (danger and hovered)) and not selected
                      else "refused" if danger else "text")
        gdi32.SetTextColor(item.hDC, self.COLORS[text_color])
        gdi32.SetBkMode(item.hDC, TRANSPARENT)
        gdi32.SelectObject(item.hDC, self._font)
        text_length = user32.GetWindowTextLengthW(item.hwndItem)
        buffer = ctypes.create_unicode_buffer(text_length + 1)
        user32.GetWindowTextW(item.hwndItem, buffer, text_length + 1)
        user32.DrawTextW(item.hDC, buffer, -1, ctypes.byref(item.rcItem), DT_CENTER | DT_VCENTER | DT_SINGLELINE)
        return 1

    def _round_rect(self, hdc: int, rect: tuple[int, int, int, int], fill: str | None, border: str,
                    radius: int | None = None) -> None:
        """Paint one 1px-bordered rounded rectangle from colour and radius tokens.

        GDI+ antialiasing is preferred. If it fails, the failure is recorded and this window
        returns permanently to the pre-r005 GDI RoundRect renderer with identical geometry.
        """
        radius = self.px(self.TOKENS["radii"]["md"]) if radius is None else radius
        radius = max(1, radius)  # Tiny transient geometry is clamped, never treated as a renderer failure.
        stroke = max(1, self.px(1))
        if self._vector is not None:
            try:
                self._vector.round_rect(hdc, rect, radius, None if fill is None else self.COLORS[fill],
                                        self.COLORS[border], stroke)
                return
            except (OSError, ValueError):
                self.record_callback_failure()
                self._vector.close()
                self._vector = None
        pen = gdi32.CreatePen(0, stroke, self.COLORS[border])
        old_pen = gdi32.SelectObject(hdc, pen)
        old_brush = gdi32.SelectObject(hdc, self._brushes[fill] if fill else gdi32.GetStockObject(5))  # NULL_BRUSH
        gdi32.RoundRect(hdc, *rect, radius * 2, radius * 2)
        gdi32.SelectObject(hdc, old_brush)
        gdi32.SelectObject(hdc, old_pen)
        gdi32.DeleteObject(pen)

    # --- L4 components: one owner-drawn STATIC each; window text carries the full plain content. ---

    def _component(self, key: str, kind: str, rect, data: dict) -> Control:
        control = self._control(key, kind, "STATIC", "", SS_OWNERDRAW, rect)
        self._components[key] = data
        return control

    def _update_component(self, key: str, data: dict, text: str) -> None:
        if self._components[key] == data and self.text(key) == text:
            return
        self._components[key] = data
        user32.SetWindowTextW(self.controls[key].hwnd, text)
        user32.InvalidateRect(self.controls[key].hwnd, None, False)

    def badge(self, key: str, rect) -> Control:
        return self._component(key, "badge", rect, {"text": "", "tone": "quiet"})

    def set_badge(self, key: str, text: str, tone: str) -> None:
        self._update_component(key, {"text": str(text), "tone": tone}, str(text))

    def key_value(self, key: str, title: str, rect, *, columns: int = 1) -> Control:
        control = self._component(
            key, "key_value", rect,
            {"title": title, "rows": (), "columns": columns, "flat": False},
        )
        user32.SetWindowTextW(control.hwnd, title)
        return control

    def flat_key_value(self, key: str, title: str, rect, *, columns: int = 1) -> Control:
        """Create an unframed evidence reader for a structural inspector region."""
        control = self._component(
            key, "key_value", rect,
            {"title": title, "rows": (), "columns": columns, "flat": True},
        )
        user32.SetWindowTextW(control.hwnd, title)
        return control

    def set_key_value(self, key: str, rows) -> None:
        rows = tuple((str(label), str(value), bool(mono)) for label, value, mono in rows)
        data = dict(self._components[key], rows=rows)
        text = "\r\n".join([data["title"], *(f"{label}: {value}" for label, value, _ in rows)])
        self._update_component(key, data, text)

    def swatch_grid(self, key: str, entries, rect) -> Control:
        """Render named theme-token swatches for foundation review."""
        values = tuple((str(label), str(tone)) for label, tone in entries)
        if not values or any(tone not in self.COLORS for _, tone in values):
            raise UIRefusal("NATIVE_SWATCH_GRID_REFUSED", key)
        text = "\r\n".join(f"{label}: {tone}" for label, tone in values)
        control = self._component(key, "swatch_grid", rect, {"entries": values})
        user32.SetWindowTextW(control.hwnd, text)
        return control

    def type_scale(self, key: str, rows, rect) -> Control:
        """Render declared typography roles using their actual role fonts."""
        values = tuple((str(role), str(sample)) for role, sample in rows)
        if not values or any(role not in self._fonts for role, _ in values):
            raise UIRefusal("NATIVE_TYPE_SCALE_REFUSED", key)
        text = "\r\n".join(f"{role}: {sample}" for role, sample in values)
        control = self._component(key, "type_scale", rect, {"rows": values})
        user32.SetWindowTextW(control.hwnd, text)
        return control

    def token_scale(self, key: str, title: str, entries, rect) -> Control:
        """Render numeric design tokens as a comparable ruler."""
        values = tuple((str(label), max(0, int(value))) for label, value in entries)
        if not values:
            raise UIRefusal("NATIVE_TOKEN_SCALE_REFUSED", key)
        text = "\r\n".join([str(title), *(f"{label}: {value}" for label, value in values)])
        control = self._component(key, "token_scale", rect, {"title": str(title), "entries": values})
        user32.SetWindowTextW(control.hwnd, text)
        return control

    def stepper(self, key: str, steps, rect, *, selected=0,
                command: Callable[[str], None] | None = None) -> Control:
        steps = tuple(str(step) for step in steps)
        if not steps:
            raise ValueError("stepper requires at least one step")
        try:
            index = steps.index(str(selected)) if str(selected) in steps else int(selected)
        except (TypeError, ValueError):
            index = 0
        index = min(len(steps) - 1, max(0, index))
        if command is None:
            return self._component(key, "stepper", rect, {"steps": steps, "index": index, "tone": "accent"})

        def activate() -> None:
            data = self._components[key]
            if key in self._choice_pointer_pending:
                self._choice_pointer_pending.discard(key)
            else:
                data["index"] = min(len(data["steps"]) - 1, data["index"] + 1)
            user32.InvalidateRect(self.controls[key].hwnd, None, False)
            command(str(data["steps"][data["index"]]))

        control = self._control(key, "stepper", "BUTTON", steps[index], WS_TABSTOP | BS_OWNERDRAW,
                                rect, activate, {BN_CLICKED})
        self._components[key] = {"steps": steps, "index": index, "tone": "accent"}
        return control

    def set_steps(self, key: str, steps, index: int, tone: str) -> None:
        if key in self._choice_pointer_pending:
            return
        steps = tuple(str(step) for step in steps)
        text = " > ".join(f"[{step}]" if position == index else step for position, step in enumerate(steps))
        self._update_component(key, {"steps": steps, "index": int(index), "tone": tone}, text)

    def _choice_component(self, key: str, kind: str, options, rect, *, selected=None,
                          command: Callable[[str], None] | None = None) -> Control:
        options = tuple(str(option) for option in options)
        if not options:
            raise ValueError(f"{kind} requires at least one option")
        selected = str(selected) if selected in options else options[0]

        def activate() -> None:
            data = self._components[key]
            if key in self._choice_pointer_pending:
                self._choice_pointer_pending.discard(key)
            else:
                index = (data["options"].index(data["selected"]) + 1) % len(data["options"])
                data["selected"] = data["options"][index]
            user32.SetWindowTextW(self.controls[key].hwnd, str(data["selected"]))
            user32.InvalidateRect(self.controls[key].hwnd, None, False)
            if command:
                command(str(data["selected"]))

        control = self._control(key, kind, "BUTTON", selected, WS_TABSTOP | BS_OWNERDRAW, rect, activate,
                                {BN_CLICKED})
        self._components[key] = {"options": options, "selected": selected}
        return control

    def segmented(self, key: str, options, rect, *, selected=None,
                  command: Callable[[str], None] | None = None) -> Control:
        return self._choice_component(key, "segmented", options, rect, selected=selected, command=command)

    def set_segmented(self, key: str, options, selected) -> None:
        if key in self._choice_pointer_pending:
            return
        options = tuple(str(option) for option in options)
        selected = str(selected) if selected in options else options[0]
        self._update_component(key, {"options": options, "selected": selected}, selected)

    def tab_bar(self, key: str, tabs, rect, *, selected=None,
                command: Callable[[str], None] | None = None) -> Control:
        return self._choice_component(key, "tab_bar", tabs, rect, selected=selected, command=command)

    def workspace_tabs(self, key: str, tabs, rect, *, selected=None,
                       command: Callable[[str], None] | None = None) -> Control:
        """Render compact shell tabs with an underline instead of boxed segments."""
        options = tuple(str(tab) for tab in tabs)
        if not options:
            raise ValueError("workspace tabs require at least one option")
        selected = str(selected) if selected in options else ""

        def activate() -> None:
            data = self._components[key]
            if key in self._choice_pointer_pending:
                self._choice_pointer_pending.discard(key)
            elif data["selected"] in data["options"]:
                index = (data["options"].index(data["selected"]) + 1) % len(data["options"])
                data["selected"] = data["options"][index]
            else:
                data["selected"] = data["options"][0]
            user32.SetWindowTextW(self.controls[key].hwnd, str(data["selected"]))
            user32.InvalidateRect(self.controls[key].hwnd, None, False)
            if command:
                command(str(data["selected"]))

        control = self._control(
            key, "workspace_tabs", "BUTTON", selected, WS_TABSTOP | BS_OWNERDRAW,
            rect, activate, {BN_CLICKED},
        )
        self._components[key] = {"options": options, "selected": selected}
        return control

    def set_workspace_tabs(self, key: str, tabs, selected) -> None:
        if key in self._choice_pointer_pending:
            return
        options = tuple(str(tab) for tab in tabs)
        selected = str(selected) if selected in options else ""
        self._update_component(key, {"options": options, "selected": selected}, selected)

    def set_tabs(self, key: str, tabs, selected) -> None:
        self.set_segmented(key, tabs, selected)

    def menu(self, key: str, options, rect, *, selected=None,
             command: Callable[[str], None] | None = None) -> Control:
        return self._choice_component(key, "menu", options, rect, selected=selected, command=command)

    def navigation(self, key: str, options, rect, *, selected=None,
                   command: Callable[[str], None] | None = None) -> Control:
        return self._choice_component(key, "navigation", options, rect, selected=selected, command=command)

    def radio_group(self, key: str, options, rect, *, selected=None,
                    command: Callable[[str], None] | None = None) -> Control:
        return self._choice_component(key, "radio_group", options, rect, selected=selected, command=command)

    def set_choice(self, key: str, options, selected) -> None:
        self.set_segmented(key, options, selected)

    def panel(self, key: str, title: str, rect) -> Control:
        control = self._component(key, "panel", rect, {"title": str(title)})
        user32.SetWindowTextW(control.hwnd, str(title))
        return control

    def surface(self, key: str, rect, *, fill: str = "surface", border: str = "border",
                edges: str = "all") -> Control:
        """Create a flat structural band with explicit separator edges."""
        if fill not in self.COLORS or border not in self.COLORS or edges not in {
            "none", "all", "top", "bottom", "left", "right", "vertical", "horizontal",
        }:
            raise UIRefusal("NATIVE_SURFACE_REFUSED", key)
        return self._component(
            key, "surface", rect, {"fill": fill, "border": border, "edges": edges},
        )

    def catalog_list(self, key: str, values: list[str], rect, *, selected: int = 0,
                     command: Callable[[str], None] | None = None) -> Control:
        """Create a scan-first owner-drawn ontology catalog with semantic headings."""
        def activate() -> None:
            if command:
                command(self.list_value(key))

        control = self._control(
            key, "catalog_list", "LISTBOX", "",
            WS_TABSTOP | WS_VSCROLL | LBS_NOTIFY | LBS_OWNERDRAWFIXED | LBS_HASSTRINGS | LBS_NOINTEGRALHEIGHT,
            rect, activate if command else None, {LBN_SELCHANGE} if command else None,
        )
        self._components[key] = {"heading_suffix": "::heading"}
        for value in values:
            buffer = ctypes.create_unicode_buffer(str(value))
            user32.SendMessageW(control.hwnd, LB_ADDSTRING, 0, ctypes.addressof(buffer))
        user32.SendMessageW(control.hwnd, LB_SETCURSEL, selected, 0)
        user32.SendMessageW(control.hwnd, 0x01A0, 0, self.px(26))  # LB_SETITEMHEIGHT
        return control

    def dialog(self, key: str, title: str, message: str, decisions, rect, *, selected=None,
               command: Callable[[str], None] | None = None) -> Control:
        decisions = tuple(str(value) for value in decisions)
        if not decisions:
            raise ValueError("dialog requires at least one decision")
        selected = str(selected) if selected in decisions else decisions[0]
        text = "\r\n".join((str(title), str(message), " / ".join(decisions)))
        data = {"title": str(title), "message": str(message), "decisions": decisions, "selected": selected}
        if command is None:
            control = self._component(key, "dialog", rect, data)
        else:
            def activate() -> None:
                current = self._components[key]
                if key in self._choice_pointer_pending:
                    self._choice_pointer_pending.discard(key)
                command(str(current["selected"]))
            control = self._control(key, "dialog", "BUTTON", text, WS_TABSTOP | BS_OWNERDRAW,
                                    rect, activate, {BN_CLICKED})
            self._components[key] = data
        user32.SetWindowTextW(control.hwnd, text)
        return control

    def tooltip(self, key: str, text: str, rect) -> Control:
        control = self._component(key, "tooltip", rect, {"text": str(text)})
        user32.SetWindowTextW(control.hwnd, str(text))
        return control

    def notification(self, key: str, text: str, rect, *, tone: str = "info") -> Control:
        control = self._component(key, "notification", rect, {"text": str(text), "tone": str(tone)})
        user32.SetWindowTextW(control.hwnd, str(text))
        return control

    def set_notification(self, key: str, text: str, tone: str = "info") -> None:
        self._update_component(key, {"text": str(text), "tone": str(tone)}, str(text))

    def _text(self, hdc: int, text: str, rect, color: str, font: int, flags: int) -> None:
        gdi32.SetTextColor(hdc, self.COLORS[color])
        gdi32.SetBkMode(hdc, TRANSPARENT)
        gdi32.SelectObject(hdc, font)
        user32.DrawTextW(hdc, text, -1, ctypes.byref(rect), flags | DT_NOPREFIX | DT_SINGLELINE | DT_VCENTER)

    def _draw_component(self, item: DRAWITEMSTRUCT) -> int:
        key = next((key for key, control in self.controls.items() if control.hwnd == item.hwndItem), "")
        data = self._components.get(key)
        if data is None:
            return 0
        hdc, box = item.hDC, item.rcItem
        left, top, right, bottom = box.left, box.top, box.right, box.bottom
        background = self.control_backgrounds.get(item.hwndItem, "canvas")
        user32.FillRect(hdc, ctypes.byref(box), self._brushes[background])
        kind = self.controls[key].kind
        spacing = self.TOKENS["spacing"]
        if kind == "badge":
            self._round_rect(hdc, (left, top, right, bottom), "surface", data["tone"], radius=(bottom - top) // 2)
            self._text(hdc, data["text"], wintypes.RECT(left, top, right, bottom), data["tone"], self._font_bold,
                       DT_CENTER)
        elif kind == "key_value":
            pad = self.px(spacing["md"])
            if not data.get("flat", False):
                self._round_rect(hdc, (left, top, right, bottom), "surface", "border")
            title_height, row_height, gap = self.px(26), self.px(24), self.px(spacing["lg"])
            self._text(hdc, data["title"], wintypes.RECT(left + pad, top + pad, right - pad, top + pad + title_height),
                       "text", self._font_bold, DT_LEFT)
            rows, columns = data["rows"], max(1, data["columns"])
            per_column = -(-len(rows) // columns) if rows else 0
            column_width = (right - left - 2 * pad - gap * (columns - 1)) // columns
            label_width = min(self.px(150), int(column_width * 0.42))
            first = top + pad + title_height + self.px(spacing["xs"])
            for index, (label, value, mono) in enumerate(rows):
                column, line = divmod(index, per_column)
                x = left + pad + column * (column_width + gap)
                y = first + line * row_height
                if y + row_height > bottom - self.px(spacing["xs"]):
                    continue  # Clipped rows remain available in window text and Copy.
                self._text(hdc, label, wintypes.RECT(x, y, x + label_width - self.px(spacing["sm"]), y + row_height),
                           "quiet", self._font, DT_LEFT | DT_END_ELLIPSIS)
                self._text(hdc, compact_identifier(value) if mono else value,
                           wintypes.RECT(x + label_width, y, x + column_width, y + row_height),
                           "text", self._fonts["mono"] if mono else self._font, DT_LEFT | DT_END_ELLIPSIS)
        elif kind == "swatch_grid":
            entries = data["entries"]
            columns = min(3, len(entries))
            rows = math.ceil(len(entries) / columns)
            gap, pad = self.px(spacing["sm"]), self.px(spacing["sm"])
            cell_width = max(1, (right - left - 2 * pad - gap * (columns - 1)) // columns)
            cell_height = max(1, (bottom - top - 2 * pad - gap * (rows - 1)) // rows)
            light = {"text", "text_quiet", "accent", "focus", "pending", "refused", "info"}
            for index, (label, tone) in enumerate(entries):
                row, column = divmod(index, columns)
                x0 = left + pad + column * (cell_width + gap)
                y0 = top + pad + row * (cell_height + gap)
                rect = wintypes.RECT(x0, y0, x0 + cell_width, y0 + cell_height)
                user32.FillRect(hdc, ctypes.byref(rect), self._brushes[tone])
                user32.FrameRect(hdc, ctypes.byref(rect), self._brushes["border"])
                self._text(hdc, label, wintypes.RECT(x0 + pad, y0, x0 + cell_width - pad, y0 + cell_height),
                           "canvas" if tone in light else "text", self._font_bold, DT_LEFT | DT_END_ELLIPSIS)
        elif kind == "type_scale":
            rows = data["rows"]
            pad, row_height = self.px(spacing["sm"]), max(1, (bottom - top - self.px(spacing["sm"]) * 2) // len(rows))
            for index, (role, sample) in enumerate(rows):
                y0 = top + pad + index * row_height
                label_width = self.px(70)
                self._text(hdc, role, wintypes.RECT(left + pad, y0, left + pad + label_width, y0 + row_height),
                           "quiet", self._font, DT_LEFT | DT_END_ELLIPSIS)
                self._text(hdc, sample, wintypes.RECT(left + pad + label_width, y0, right - pad, y0 + row_height),
                           "text", self._fonts[role], DT_LEFT | DT_END_ELLIPSIS)
        elif kind == "token_scale":
            entries = data["entries"]
            pad, label_width = self.px(spacing["md"]), self.px(82)
            title_height, row_height = self.px(28), max(1, (bottom - top - self.px(spacing["md"]) * 2 - self.px(28)) // len(entries))
            maximum = max((value for _, value in entries), default=1)
            self._text(hdc, data["title"], wintypes.RECT(left + pad, top + pad, right - pad, top + pad + title_height),
                       "text", self._font_bold, DT_LEFT)
            for index, (label, value) in enumerate(entries):
                y0 = top + pad + title_height + index * row_height
                self._text(hdc, f"{label}  {value}", wintypes.RECT(left + pad, y0, left + pad + label_width, y0 + row_height),
                           "quiet", self._font, DT_LEFT | DT_END_ELLIPSIS)
                available = max(1, right - (left + pad + label_width) - pad)
                bar = wintypes.RECT(left + pad + label_width, y0 + self.px(5),
                                    left + pad + label_width + max(self.px(2), available * value // maximum),
                                    y0 + max(self.px(7), row_height - self.px(5)))
                user32.FillRect(hdc, ctypes.byref(bar), self._brushes["accent"])
        elif kind == "stepper":
            steps, current = data["steps"], data["index"]
            segment = (right - left) // max(1, len(steps))
            diameter, middle = self.px(14), (top + bottom) // 2
            for index, step in enumerate(steps):
                x = left + index * segment
                circle = (x, middle - diameter // 2, x + diameter, middle - diameter // 2 + diameter)
                if index < current:
                    fill, border, color, font = "accent", "accent", "text", self._font
                elif index == current:
                    fill, border, color, font = data["tone"], data["tone"], "text", self._font_bold
                else:
                    fill, border, color, font = "surface", "border", "quiet", self._font
                if index + 1 < len(steps):
                    line = wintypes.RECT(x + diameter + self.px(spacing["sm"]) + self.px(120), middle - self.px(1),
                                         x + segment - self.px(spacing["sm"]), middle - self.px(1) + max(1, self.px(2)))
                    if line.right > line.left:
                        user32.FillRect(hdc, ctypes.byref(line), self._brushes["accent" if index < current else "border"])
                self._round_rect(hdc, circle, fill, border, radius=diameter // 2)
                self._text(hdc, step, wintypes.RECT(x + diameter + self.px(spacing["sm"]), top,
                                                    x + diameter + self.px(spacing["sm"]) + self.px(118), bottom),
                           color, font, DT_LEFT | DT_END_ELLIPSIS)
        elif kind == "workspace_tabs":
            options = data["options"]
            segment = max(1, (right - left) // len(options))
            for index, option in enumerate(options):
                x0 = left + index * segment
                x1 = right if index + 1 == len(options) else left + (index + 1) * segment
                active = option == data["selected"]
                if active:
                    underline = wintypes.RECT(x0, bottom - self.px(2), x1, bottom)
                    user32.FillRect(hdc, ctypes.byref(underline), self._brushes["accent"])
                self._text(
                    hdc, option, wintypes.RECT(x0 + self.px(3), top, x1 - self.px(3), bottom - self.px(2)),
                    "text" if active else "quiet", self._font,
                    DT_CENTER | DT_END_ELLIPSIS,
                )
        elif kind in {"segmented", "tab_bar", "menu", "navigation", "radio_group"}:
            options = data["options"]
            segment = max(1, (right - left) // len(options))
            focused = bool(item.itemState & 0x0010) and self.keyboard_navigation
            choice_font = self._fonts[self._font_roles.get(key, "body")]
            for index, option in enumerate(options):
                x0 = left + index * segment
                x1 = right if index + 1 == len(options) else left + (index + 1) * segment
                active = option == data["selected"]
                fill = "selection" if active else "surface"
                border = "focus" if focused else "accent" if active else "border"
                radius = self.px(self.TOKENS["radii"]["sm"])
                self._round_rect(hdc, (x0, top, x1, bottom), fill, border, radius=radius)
                label = f"(*) {option}" if kind == "radio_group" and active else f"( ) {option}" if kind == "radio_group" else option
                self._text(hdc, label, wintypes.RECT(x0 + self.px(4), top, x1 - self.px(4), bottom),
                           "text" if active else "quiet", choice_font,
                           DT_CENTER | DT_END_ELLIPSIS)
        elif kind == "panel":
            self._round_rect(hdc, (left, top, right, bottom), "surface", "border")
            pad = self.px(spacing["md"])
            self._text(hdc, data["title"], wintypes.RECT(left + pad, top + pad, right - pad, top + pad + self.px(28)),
                       "text", self._font_bold, DT_LEFT | DT_END_ELLIPSIS)
        elif kind == "surface":
            user32.FillRect(hdc, ctypes.byref(box), self._brushes[data["fill"]])
            edge = max(1, self.px(1))
            edges = data["edges"]
            if edges in {"all", "top", "horizontal"}:
                rect = wintypes.RECT(left, top, right, top + edge)
                user32.FillRect(hdc, ctypes.byref(rect), self._brushes[data["border"]])
            if edges in {"all", "bottom", "horizontal"}:
                rect = wintypes.RECT(left, bottom - edge, right, bottom)
                user32.FillRect(hdc, ctypes.byref(rect), self._brushes[data["border"]])
            if edges in {"all", "left", "vertical"}:
                rect = wintypes.RECT(left, top, left + edge, bottom)
                user32.FillRect(hdc, ctypes.byref(rect), self._brushes[data["border"]])
            if edges in {"all", "right", "vertical"}:
                rect = wintypes.RECT(right - edge, top, right, bottom)
                user32.FillRect(hdc, ctypes.byref(rect), self._brushes[data["border"]])
        elif kind == "dialog":
            self._round_rect(hdc, (left, top, right, bottom), "raised", "focus")
            pad = self.px(spacing["lg"])
            self._text(hdc, data["title"], wintypes.RECT(left + pad, top + pad, right - pad, top + pad + self.px(30)),
                       "text", self._font_bold, DT_LEFT | DT_END_ELLIPSIS)
            self._text(hdc, data["message"], wintypes.RECT(left + pad, top + pad + self.px(38), right - pad,
                                                          top + pad + self.px(68)),
                       "text", self._font, DT_LEFT | DT_END_ELLIPSIS)
            decisions = " / ".join(
                f"[{decision}]" if decision == data.get("selected") else decision
                for decision in data["decisions"]
            )
            self._text(hdc, decisions, wintypes.RECT(left + pad, bottom - self.px(42), right - pad, bottom - self.px(10)),
                       "accent", self._font_bold, DT_RIGHT | DT_END_ELLIPSIS)
        elif kind == "tooltip":
            self._round_rect(hdc, (left, top, right, bottom), "raised", "quiet",
                             radius=self.px(self.TOKENS["radii"]["sm"]))
            pad = self.px(spacing["sm"])
            self._text(hdc, data["text"], wintypes.RECT(left + pad, top, right - pad, bottom),
                       "text", self._font, DT_LEFT | DT_END_ELLIPSIS)
        elif kind == "notification":
            self._round_rect(hdc, (left, top, right, bottom), "raised", data["tone"],
                             radius=self.px(self.TOKENS["radii"]["sm"]))
            pad = self.px(spacing["md"])
            self._text(hdc, data["text"], wintypes.RECT(left + pad, top, right - pad, bottom),
                       "text", self._font, DT_LEFT | DT_END_ELLIPSIS)
        return 1

    def _draw_catalog_item(self, item: DRAWITEMSTRUCT) -> int:
        box = item.rcItem
        selected = bool(item.itemState & ODS_SELECTED)
        index = int(item.itemID)
        text = ""
        if index >= 0:
            length = int(user32.SendMessageW(item.hwndItem, LB_GETTEXTLEN, index, 0))
            buffer = ctypes.create_unicode_buffer(max(1, length + 1))
            user32.SendMessageW(item.hwndItem, LB_GETTEXT, index, ctypes.addressof(buffer))
            text = buffer.value
        heading = text.endswith("::heading")
        visible = text.removesuffix("::heading")
        visible, _, subject_type = visible.partition("\t")
        fill = "canvas" if heading else "selection" if selected else "canvas"
        user32.FillRect(item.hDC, ctypes.byref(box), self._brushes[fill])
        if selected and not heading:
            accent = wintypes.RECT(box.left, box.top, box.left + self.px(3), box.bottom)
            user32.FillRect(item.hDC, ctypes.byref(accent), self._brushes["accent"])
        inset = self.px(10 if heading else 16)
        rect = wintypes.RECT(box.left + inset, box.top, box.right - self.px(8), box.bottom)
        self._text(
            item.hDC, visible, rect, "quiet" if heading else "accent" if selected else "text",
            self._font_bold if selected and not heading else self._font,
            DT_LEFT | DT_END_ELLIPSIS,
        )
        if subject_type and not heading:
            type_rect = wintypes.RECT(box.left + self.px(112), box.top, box.right - self.px(8), box.bottom)
            self._text(item.hDC, subject_type, type_rect, "accent" if selected else "quiet", self._fonts["mono"],
                       DT_RIGHT | DT_END_ELLIPSIS)
        return 1

    def _draw_combo(self, item: DRAWITEMSTRUCT) -> int:
        selected = bool(item.itemState & ODS_SELECTED)
        disabled = bool(item.itemState & ODS_DISABLED)
        brush = self._brushes["selection" if selected else "field"]
        user32.FillRect(item.hDC, ctypes.byref(item.rcItem), brush)
        user32.FrameRect(item.hDC, ctypes.byref(item.rcItem), self._brushes["border"])
        index = int(item.itemID)
        if index == 0xFFFFFFFF:
            index = int(user32.SendMessageW(item.hwndItem, CB_GETCURSEL, 0, 0))
        if index >= 0:
            length = int(user32.SendMessageW(item.hwndItem, 0x0149, index, 0))
            buffer = ctypes.create_unicode_buffer(max(1, length + 1))
            user32.SendMessageW(item.hwndItem, 0x0148, index, ctypes.addressof(buffer))
            rect = wintypes.RECT(item.rcItem.left + 8, item.rcItem.top, item.rcItem.right - 24, item.rcItem.bottom)
            gdi32.SetTextColor(item.hDC, self.COLORS["quiet" if disabled else "text"])
            gdi32.SetBkMode(item.hDC, TRANSPARENT)
            gdi32.SelectObject(item.hDC, self._font)
            user32.DrawTextW(item.hDC, buffer, -1, ctypes.byref(rect), DT_LEFT | DT_VCENTER | DT_SINGLELINE)
        return 1

    def run(self) -> int:
        user32.ShowWindow(self.hwnd, SW_SHOW)
        user32.UpdateWindow(self.hwnd)
        message = MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            target = next((window for window in list(_windows.values())
                           if window.owner is self and (message.hwnd == window.hwnd or user32.IsChild(window.hwnd, message.hwnd))), self)
            target.track_input(message.message, message.wParam)
            if not user32.IsDialogMessageW(target.hwnd, ctypes.byref(message)):
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        return int(message.wParam)

    def close(self) -> None:
        if user32.IsWindow(self.hwnd):
            user32.SendMessageW(self.hwnd, WM_CLOSE, 0, 0)


def assert_native_contract(payload: dict) -> None:
    realization = payload.get("realization", {})
    expected = {
        "target": "WIN32_CTYPES_NATIVE", "browser_intermediary": False,
        "tkinter": False, "third_party_packages": [],
    }
    actual = {key: realization.get(key) for key in expected}
    if actual != expected:
        raise RuntimeError(f"generated native UI contract refused: {actual!r}")

