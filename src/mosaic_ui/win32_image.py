"""PNG rendering and window icons through Windows GDI+, with no Python packages."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path


gdiplus = ctypes.WinDLL("gdiplus")


class StartupInput(ctypes.Structure):
    _fields_ = [("version", wintypes.UINT), ("callback", ctypes.c_void_p),
                ("suppress_thread", wintypes.BOOL), ("suppress_codecs", wintypes.BOOL)]


P = ctypes.c_void_p
gdiplus.GdiplusStartup.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(StartupInput), P]
gdiplus.GdiplusShutdown.argtypes = [ctypes.c_size_t]
gdiplus.GdipLoadImageFromFile.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(P)]
gdiplus.GdipDisposeImage.argtypes = [P]
gdiplus.GdipCreateFromHDC.argtypes = [wintypes.HDC, ctypes.POINTER(P)]
gdiplus.GdipDeleteGraphics.argtypes = [P]
gdiplus.GdipSetInterpolationMode.argtypes = [P, ctypes.c_int]
gdiplus.GdipDrawImageRectI.argtypes = [P, P] + [ctypes.c_int] * 4
gdiplus.GdipGetImageThumbnail.argtypes = [P, wintypes.UINT, wintypes.UINT, ctypes.POINTER(P), P, P]
gdiplus.GdipCreateHICONFromBitmap.argtypes = [P, ctypes.POINTER(wintypes.HICON)]


def checked(status: int) -> None:
    if status:
        raise OSError(f"Windows GDI+ image operation failed (status {status})")


class NativeImage:
    def __init__(self, path: Path) -> None:
        self.token = ctypes.c_size_t()
        self.image = P()
        checked(gdiplus.GdiplusStartup(ctypes.byref(self.token), ctypes.byref(StartupInput(1)), None))
        try:
            checked(gdiplus.GdipLoadImageFromFile(str(path.resolve()), ctypes.byref(self.image)))
        except BaseException:
            self.close()
            raise

    def draw(self, hdc: int, rect: tuple[int, int, int, int]) -> None:
        graphics = P()
        checked(gdiplus.GdipCreateFromHDC(hdc, ctypes.byref(graphics)))
        try:
            checked(gdiplus.GdipSetInterpolationMode(graphics, 7))  # HighQualityBicubic
            checked(gdiplus.GdipDrawImageRectI(graphics, self.image, *rect))
        finally:
            gdiplus.GdipDeleteGraphics(graphics)

    def icon(self, size: int) -> int:
        thumbnail = P()
        handle = wintypes.HICON()
        checked(gdiplus.GdipGetImageThumbnail(self.image, size, size, ctypes.byref(thumbnail), None, None))
        try:
            checked(gdiplus.GdipCreateHICONFromBitmap(thumbnail, ctypes.byref(handle)))
            return handle.value
        finally:
            gdiplus.GdipDisposeImage(thumbnail)

    def close(self) -> None:
        if self.image.value:
            gdiplus.GdipDisposeImage(self.image)
            self.image = P()
        if self.token.value:
            gdiplus.GdiplusShutdown(self.token)
            self.token = ctypes.c_size_t()
