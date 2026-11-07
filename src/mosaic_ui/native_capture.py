"""Capture only an owned Win32 client window, without desktop input or focus."""
from __future__ import annotations

import ctypes
import struct
import zlib
from ctypes import wintypes
from pathlib import Path

from .win32 import NativeWindow, user32, gdi32


class BitmapHeader(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("width", wintypes.LONG),
                ("height", wintypes.LONG), ("planes", wintypes.WORD),
                ("bits", wintypes.WORD), ("compression", wintypes.DWORD),
                ("image_size", wintypes.DWORD), ("xppm", wintypes.LONG),
                ("yppm", wintypes.LONG), ("used", wintypes.DWORD),
                ("important", wintypes.DWORD)]


def capture_client(window: NativeWindow, output: Path) -> dict:
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                     ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    rect = wintypes.RECT()
    if not user32.GetClientRect(window.hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    width, height = rect.right, rect.bottom
    window.relayout()  # Layout handlers take DIPs; the client rect is in device pixels.
    header = BitmapHeader(ctypes.sizeof(BitmapHeader), width, -height, 1, 32)
    screen = user32.GetDC(window.hwnd)
    dc = gdi32.CreateCompatibleDC(screen)
    bits = ctypes.c_void_p()
    bitmap = gdi32.CreateDIBSection(screen, ctypes.byref(header), 0, ctypes.byref(bits), None, 0)
    old = None
    try:
        if not dc or not bitmap or not bits.value:
            raise ctypes.WinError(ctypes.get_last_error())
        old = gdi32.SelectObject(dc, bitmap)
        if not user32.PrintWindow(window.hwnd, dc, 1):
            raise RuntimeError("Owned-window PrintWindow capture failed")
        bgra = ctypes.string_at(bits, width * height * 4)
        if len(set(bgra[0::4])) < 2:
            raise RuntimeError("Owned-window capture is blank; show the window without activation before capture")
        rgb = bytearray(width * height * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = bgra[2::4], bgra[1::4], bgra[0::4]
        stride = width * 3
        scanlines = b"".join(b"\0" + rgb[y * stride:(y + 1) * stride] for y in range(height))
        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b"")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(png)
        return {"path": str(output.resolve()), "width": width, "height": height,
                "method": "OWNED_HWND_PRINTWINDOW", "desktop_input": False}
    finally:
        if old:
            gdi32.SelectObject(dc, old)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if dc:
            gdi32.DeleteDC(dc)
        user32.ReleaseDC(window.hwnd, screen)
