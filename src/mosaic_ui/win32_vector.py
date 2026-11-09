"""Antialiased vector shapes through Windows GDI+, with no Python packages."""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from .win32_image import P, StartupInput, checked, gdiplus

REAL = ctypes.c_float
gdiplus.GdipSetSmoothingMode.argtypes = [P, ctypes.c_int]
gdiplus.GdipSetPixelOffsetMode.argtypes = [P, ctypes.c_int]
gdiplus.GdipCreatePath.argtypes = [ctypes.c_int, ctypes.POINTER(P)]
gdiplus.GdipDeletePath.argtypes = [P]
gdiplus.GdipAddPathArc.argtypes = [P, REAL, REAL, REAL, REAL, REAL, REAL]
gdiplus.GdipClosePathFigure.argtypes = [P]
gdiplus.GdipCreateSolidFill.argtypes = [wintypes.DWORD, ctypes.POINTER(P)]
gdiplus.GdipDeleteBrush.argtypes = [P]
gdiplus.GdipFillPath.argtypes = [P, P, P]
gdiplus.GdipCreatePen1.argtypes = [wintypes.DWORD, REAL, ctypes.c_int, ctypes.POINTER(P)]
gdiplus.GdipDeletePen.argtypes = [P]
gdiplus.GdipDrawPath.argtypes = [P, P, P]

SMOOTHING_ANTIALIAS = 4
PIXEL_OFFSET_HALF = 4  # Pixel centres at +0.5, matching the path coordinates below.
UNIT_PIXEL = 2


def argb(colorref: int) -> int:
    """Convert a GDI COLORREF (0x00BBGGRR) into an opaque GDI+ ARGB value."""
    red, green, blue = colorref & 0xFF, (colorref >> 8) & 0xFF, (colorref >> 16) & 0xFF
    return 0xFF000000 | (red << 16) | (green << 8) | blue


class VectorPainter:
    """Owns one GDI+ startup token for the lifetime of one native window."""

    def __init__(self) -> None:
        self.token = ctypes.c_size_t()
        checked(gdiplus.GdiplusStartup(ctypes.byref(self.token), ctypes.byref(StartupInput(1)), None))

    def round_rect(self, hdc: int, rect: tuple[int, int, int, int], radius: int,
                   fill: int | None, border: int, stroke: int = 1) -> None:
        """Fill and stroke a rounded rectangle inside the integer rect (left, top, right, bottom).

        The path is inset by half the stroke, so a `stroke`-pixel border covers exactly the
        outermost `stroke` pixel rows and columns (PixelOffsetModeHalf), with antialiased corners.
        """
        left, top, right, bottom = rect
        half = stroke / 2.0
        x, y = left + half, top + half
        width, height = right - left - float(stroke), bottom - top - float(stroke)
        diameter = float(min(2 * radius, width, height))
        if width < 1 or height < 1:
            return  # Nothing is visible inside a collapsed control; the caller already filled it.
        if diameter <= 0:
            raise ValueError("round_rect requires a positive radius")
        graphics, path, brush, pen = P(), P(), P(), P()
        checked(gdiplus.GdipCreateFromHDC(hdc, ctypes.byref(graphics)))
        try:
            checked(gdiplus.GdipSetSmoothingMode(graphics, SMOOTHING_ANTIALIAS))
            # GDI+ defaults to integer pixel centres; without Half, 1px strokes straddle two rows.
            checked(gdiplus.GdipSetPixelOffsetMode(graphics, PIXEL_OFFSET_HALF))
            checked(gdiplus.GdipCreatePath(0, ctypes.byref(path)))
            checked(gdiplus.GdipAddPathArc(path, x, y, diameter, diameter, 180.0, 90.0))
            checked(gdiplus.GdipAddPathArc(path, x + width - diameter, y, diameter, diameter, 270.0, 90.0))
            checked(gdiplus.GdipAddPathArc(path, x + width - diameter, y + height - diameter,
                                           diameter, diameter, 0.0, 90.0))
            checked(gdiplus.GdipAddPathArc(path, x, y + height - diameter, diameter, diameter, 90.0, 90.0))
            checked(gdiplus.GdipClosePathFigure(path))
            if fill is not None:
                checked(gdiplus.GdipCreateSolidFill(argb(fill), ctypes.byref(brush)))
                checked(gdiplus.GdipFillPath(graphics, brush, path))
            checked(gdiplus.GdipCreatePen1(argb(border), float(stroke), UNIT_PIXEL, ctypes.byref(pen)))
            checked(gdiplus.GdipDrawPath(graphics, pen, path))
        finally:
            if pen.value:
                gdiplus.GdipDeletePen(pen)
            if brush.value:
                gdiplus.GdipDeleteBrush(brush)
            if path.value:
                gdiplus.GdipDeletePath(path)
            gdiplus.GdipDeleteGraphics(graphics)

    def close(self) -> None:
        if self.token.value:
            gdiplus.GdiplusShutdown(self.token)
            self.token = ctypes.c_size_t()
