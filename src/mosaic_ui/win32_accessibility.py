"""Bounded Windows accessibility annotation and direct IAccessible inspection."""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Any


if sys.platform != "win32":
    raise RuntimeError("mosaic_ui.win32_accessibility requires Windows")


oleacc = ctypes.WinDLL("oleacc", use_last_error=True)
oleaut32 = ctypes.WinDLL("oleaut32", use_last_error=True)
ole32 = ctypes.WinDLL("ole32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

OBJID_CLIENT = 0xFFFFFFFC
CHILDID_SELF = 0
VT_EMPTY = 0
VT_I4 = 3
GWL_STYLE = -16
WS_TABSTOP = 0x00010000


class GUID(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def parse(cls, value: str) -> "GUID":
        import uuid

        raw = uuid.UUID(value).bytes_le
        return cls(int.from_bytes(raw[0:4], "little"), int.from_bytes(raw[4:6], "little"),
                   int.from_bytes(raw[6:8], "little"), (ctypes.c_ubyte * 8)(*raw[8:]))


class VARIANT_VALUE(ctypes.Union):
    _fields_ = [("lVal", ctypes.c_long), ("bstrVal", ctypes.c_void_p),
                ("punkVal", ctypes.c_void_p), ("byref", ctypes.c_void_p)]


class VARIANT(ctypes.Structure):
    _anonymous_ = ("value",)
    _fields_ = [("vt", ctypes.c_ushort), ("reserved1", ctypes.c_ushort),
                ("reserved2", ctypes.c_ushort), ("reserved3", ctypes.c_ushort),
                ("value", VARIANT_VALUE)]


IID_IACCESSIBLE = GUID.parse("618736E0-3C3D-11CF-810C-00AA00389B71")
CLSID_ACC_PROP_SERVICES = GUID.parse("B5F8350B-0548-48B1-A6EE-88BD00B4A5E7")
IID_IACC_PROP_SERVICES = GUID.parse("6E26E776-04F0-495D-80E4-3330352E3169")
PROPID_ACC_NAME = GUID.parse("608D3DF8-8128-4AA7-A428-F55E49267291")
PROPID_ACC_VALUE = GUID.parse("123FE443-211A-4615-9527-C45A7E93717A")
PROPID_ACC_DESCRIPTION = GUID.parse("4D48D353-2D0F-4F1A-BEAC-D3DADAEEC967")
PROPID_ACC_DEFAULTACTION = GUID.parse("180C072B-C27F-43C7-9922-F63562A4632B")

oleacc.AccessibleObjectFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD,
                                              ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
oleacc.AccessibleObjectFromWindow.restype = ctypes.c_long
ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
                                   ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
ole32.CoCreateInstance.restype = ctypes.c_long
oleaut32.SysStringLen.argtypes = [ctypes.c_void_p]
oleaut32.SysStringLen.restype = wintypes.UINT
oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.IsWindowEnabled.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetFocus.restype = wintypes.HWND


ROLE_NAMES = {
    0x09: "window", 0x0A: "client", 0x12: "dialog", 0x18: "table",
    0x1E: "drop-list", 0x21: "list", 0x22: "list-item", 0x29: "text",
    0x2A: "editable-text", 0x2B: "push-button", 0x2C: "check-button",
    0x2E: "combo-box", 0x30: "progress-bar",
}
STATE_BITS = {
    0x00000001: "unavailable", 0x00000002: "selected", 0x00000004: "focused",
    0x00000008: "pressed", 0x00000010: "checked", 0x00000040: "readonly",
    0x00000080: "hottracked", 0x00000200: "expanded", 0x00000400: "collapsed",
    0x00000800: "busy", 0x00008000: "invisible", 0x00010000: "offscreen",
    0x00100000: "focusable", 0x00200000: "selectable", 0x01000000: "multiselectable",
}


def _succeeded(value: int) -> bool:
    return value >= 0


def _set_string(hwnd: int, prop: GUID, value: str) -> None:
    service = ctypes.c_void_p()
    result = ole32.CoCreateInstance(ctypes.byref(CLSID_ACC_PROP_SERVICES), None, 1,
                                    ctypes.byref(IID_IACC_PROP_SERVICES), ctypes.byref(service))
    if not _succeeded(result) or not service.value:
        raise OSError(f"create IAccPropServices failed (HRESULT 0x{result & 0xFFFFFFFF:08X})")
    try:
        method = _method(service, 7, ctypes.c_long, wintypes.HWND, wintypes.DWORD,
                         wintypes.DWORD, GUID, wintypes.LPCWSTR)
        result = method(service, hwnd, OBJID_CLIENT, CHILDID_SELF, prop, str(value))
        if not _succeeded(result):
            raise OSError(f"SetHwndPropStr failed (HRESULT 0x{result & 0xFFFFFFFF:08X})")
    finally:
        _method(service, 2, wintypes.ULONG)(service)


def annotate(hwnd: int, *, name: str, description: str = "", value: str = "",
             default_action: str = "") -> None:
    """Attach semantic strings to the standard HWND accessibility proxy."""
    _set_string(hwnd, PROPID_ACC_NAME, name)
    _set_string(hwnd, PROPID_ACC_DESCRIPTION, description)
    _set_string(hwnd, PROPID_ACC_VALUE, value)
    _set_string(hwnd, PROPID_ACC_DEFAULTACTION, default_action)


def clear(hwnd: int) -> None:
    """Remove every property installed by :func:`annotate` before HWND teardown."""
    service = ctypes.c_void_p()
    result = ole32.CoCreateInstance(ctypes.byref(CLSID_ACC_PROP_SERVICES), None, 1,
                                    ctypes.byref(IID_IACC_PROP_SERVICES), ctypes.byref(service))
    if not _succeeded(result) or not service.value:
        return
    properties = (GUID * 4)(PROPID_ACC_NAME, PROPID_ACC_DESCRIPTION,
                            PROPID_ACC_VALUE, PROPID_ACC_DEFAULTACTION)
    try:
        method = _method(service, 9, ctypes.c_long, wintypes.HWND, wintypes.DWORD,
                         wintypes.DWORD, ctypes.POINTER(GUID), ctypes.c_int)
        method(service, hwnd, OBJID_CLIENT, CHILDID_SELF, properties, len(properties))
    finally:
        _method(service, 2, wintypes.ULONG)(service)


def _method(interface: ctypes.c_void_p, index: int, restype, *argtypes):
    vtable = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])


def _child() -> VARIANT:
    value = VARIANT()
    value.vt = VT_I4
    value.lVal = CHILDID_SELF
    return value


def _bstr_property(interface: ctypes.c_void_p, index: int) -> str:
    value = ctypes.c_void_p()
    result = _method(interface, index, ctypes.c_long, VARIANT, ctypes.POINTER(ctypes.c_void_p))(
        interface, _child(), ctypes.byref(value),
    )
    if not _succeeded(result) or not value.value:
        return ""
    try:
        return ctypes.wstring_at(value.value, oleaut32.SysStringLen(value))
    finally:
        oleaut32.SysFreeString(value)


def _variant_property(interface: ctypes.c_void_p, index: int) -> int | str | None:
    value = VARIANT()
    result = _method(interface, index, ctypes.c_long, VARIANT, ctypes.POINTER(VARIANT))(
        interface, _child(), ctypes.byref(value),
    )
    if not _succeeded(result):
        return None
    if value.vt == VT_I4:
        return int(value.lVal)
    if value.vt == 8 and value.bstrVal:
        try:
            return ctypes.wstring_at(value.bstrVal, oleaut32.SysStringLen(value.bstrVal))
        finally:
            oleaut32.SysFreeString(value.bstrVal)
    return None


def inspect(hwnd: int) -> dict[str, Any]:
    """Read the HWND's actual standard IAccessible proxy for CHILDID_SELF."""
    interface = ctypes.c_void_p()
    result = oleacc.AccessibleObjectFromWindow(hwnd, OBJID_CLIENT, ctypes.byref(IID_IACCESSIBLE),
                                               ctypes.byref(interface))
    if not _succeeded(result) or not interface.value:
        raise OSError(f"AccessibleObjectFromWindow failed (HRESULT 0x{result & 0xFFFFFFFF:08X})")
    try:
        role = _variant_property(interface, 13)
        state = _variant_property(interface, 14)
        class_name = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        state_value = state if isinstance(state, int) else 0
        return {
            "class_name": class_name.value,
            "name": _bstr_property(interface, 10),
            "value": _bstr_property(interface, 11),
            "description": _bstr_property(interface, 12),
            "role_id": role if isinstance(role, int) else None,
            "role": ROLE_NAMES.get(role, f"role-{role}") if isinstance(role, int) else "unknown",
            "state_bits": state_value,
            "states": [name for bit, name in STATE_BITS.items() if state_value & bit],
            "default_action": _bstr_property(interface, 20),
            "enabled": bool(user32.IsWindowEnabled(hwnd)),
            "visible": bool(user32.IsWindowVisible(hwnd)),
            "tab_stop": bool(user32.GetWindowLongW(hwnd, GWL_STYLE) & WS_TABSTOP),
            "focused": int(user32.GetFocus() or 0) == int(hwnd),
        }
    finally:
        _method(interface, 2, wintypes.ULONG)(interface)


__all__ = ["annotate", "clear", "inspect"]
