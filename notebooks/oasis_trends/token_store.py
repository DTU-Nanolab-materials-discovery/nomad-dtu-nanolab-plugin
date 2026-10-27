"""Store and load a NOMAD API token using the current Windows user's DPAPI."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_byte)),
    ]


def _windows_apis():
    if os.name != 'nt':
        raise OSError('The encrypted local token store is available only on Windows.')

    crypt32 = ctypes.WinDLL('Crypt32', use_last_error=True)
    kernel32 = ctypes.WinDLL('Kernel32', use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    return crypt32, kernel32


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    return (
        _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))),
        buffer,
    )


def token_path() -> Path:
    local_app_data = os.environ.get('LOCALAPPDATA')
    if not local_app_data:
        raise RuntimeError('Windows LOCALAPPDATA is not set.')
    return Path(local_app_data) / 'NOMAD' / 'oasis-token.dpapi'


def save_token(token: str) -> Path:
    crypt32, kernel32 = _windows_apis()
    plaintext = token.encode('utf-8')
    input_blob, _buffer = _blob(plaintext)
    output_blob = _DataBlob()
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        'NOMAD Oasis API token',
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)

    destination = token_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encrypted)
    return destination


def load_token() -> str | None:
    """Decrypt the token for the current Windows user, if one was saved."""
    path = token_path()
    if not path.exists():
        return None

    crypt32, kernel32 = _windows_apis()
    input_blob, _buffer = _blob(path.read_bytes())
    output_blob = _DataBlob()
    description = wintypes.LPWSTR()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData).decode('utf-8')
    finally:
        kernel32.LocalFree(output_blob.pbData)
        if description:
            kernel32.LocalFree(description)
