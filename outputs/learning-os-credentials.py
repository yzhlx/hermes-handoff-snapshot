"""Windows Credential Manager boundary for Learning OS provider secrets."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168
_ADVAPI32 = ctypes.WinDLL("Advapi32", use_last_error=True) if os.name == "nt" else None


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", ctypes.c_byte * 8),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    """Stores only the provider secret; callers can receive status but never the key."""

    def __init__(self, target_name: str = "LearningOS.AI.Provider"):
        self.target_name = target_name

    @staticmethod
    def _require_windows() -> None:
        if os.name != "nt":
            raise RuntimeError("Windows Credential Manager is unavailable on this system")

    def set_secret(self, secret: str) -> None:
        self._require_windows()
        if not isinstance(secret, str) or not secret.strip():
            raise ValueError("AI API key is required")
        encoded = secret.strip().encode("utf-16-le")
        blob = (ctypes.c_byte * len(encoded)).from_buffer_copy(encoded)
        credential = _Credential()
        credential.Type = CRED_TYPE_GENERIC
        credential.TargetName = self.target_name
        credential.CredentialBlobSize = len(encoded)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_byte))
        credential.Persist = CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = "Learning OS"
        if not _ADVAPI32.CredWriteW(ctypes.byref(credential), 0):
            raise ctypes.WinError(ctypes.get_last_error())

    def get_secret(self) -> str | None:
        self._require_windows()
        pointer = ctypes.POINTER(_Credential)()
        if not _ADVAPI32.CredReadW(
            self.target_name, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)
        ):
            error = ctypes.get_last_error()
            if error == ERROR_NOT_FOUND:
                return None
            raise ctypes.WinError(error)
        try:
            size = pointer.contents.CredentialBlobSize
            raw = ctypes.string_at(pointer.contents.CredentialBlob, size)
            return raw.decode("utf-16-le")
        finally:
            _ADVAPI32.CredFree(pointer)

    def delete_secret(self) -> None:
        self._require_windows()
        if not _ADVAPI32.CredDeleteW(self.target_name, CRED_TYPE_GENERIC, 0):
            error = ctypes.get_last_error()
            if error != ERROR_NOT_FOUND:
                raise ctypes.WinError(error)

    def status(self) -> dict:
        secret = self.get_secret()
        return {
            "is_configured": bool(secret),
            "key_suffix": secret[-4:] if secret else None,
        }
