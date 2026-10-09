from __future__ import annotations

import ctypes as C
from dataclasses import dataclass
from typing import Protocol

from .config import KEYCHAIN_SERVICE
from .errors import BrokerStorageFailure, CredentialMissing


class SecretStore(Protocol):
    def put(self, ref: str, secret: str) -> None: ...
    def get(self, ref: str) -> str: ...
    def delete(self, ref: str) -> None: ...


class _Security:
    def __init__(self):
        self.api = C.CDLL("/System/Library/Frameworks/Security.framework/Security")
        self.cf = C.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        U, P = C.c_uint32, C.c_void_p
        self.api.SecKeychainFindGenericPassword.argtypes = [P, U, P, U, P, C.POINTER(U), C.POINTER(P), C.POINTER(P)]
        self.api.SecKeychainFindGenericPassword.restype = C.c_int32
        self.api.SecKeychainAddGenericPassword.argtypes = [P, U, P, U, P, U, P, C.POINTER(P)]
        self.api.SecKeychainAddGenericPassword.restype = C.c_int32
        self.api.SecKeychainItemModifyAttributesAndData.argtypes = [P, P, U, P]
        self.api.SecKeychainItemModifyAttributesAndData.restype = C.c_int32
        self.api.SecKeychainItemDelete.argtypes = [P]
        self.api.SecKeychainItemDelete.restype = C.c_int32
        self.api.SecKeychainItemFreeContent.argtypes = [P, P]
        self.api.SecKeychainItemFreeContent.restype = C.c_int32
        self.cf.CFRelease.argtypes = [P]

    def item(self, service: bytes, account: bytes):
        item = C.c_void_p()
        result = self.api.SecKeychainFindGenericPassword(
            None, len(service), C.c_char_p(service), len(account), C.c_char_p(account),
            None, None, C.byref(item))
        if result == -25300:
            return None
        if result:
            raise BrokerStorageFailure(f"Keychain lookup failed (OSStatus {result}).")
        return item


@dataclass
class MacOSKeychainStore:
    service_name: str = KEYCHAIN_SERVICE

    def put(self, ref: str, secret: str) -> None:
        api = _Security()
        service, account, value = self.service_name.encode(), ref.encode(), secret.encode()
        item = api.item(service, account)
        try:
            if item is None:
                status = api.api.SecKeychainAddGenericPassword(
                    None, len(service), C.c_char_p(service), len(account), C.c_char_p(account),
                    len(value), C.c_char_p(value), None)
            else:
                status = api.api.SecKeychainItemModifyAttributesAndData(
                    item, None, len(value), C.c_char_p(value))
            if status:
                raise BrokerStorageFailure(f"Keychain write failed (OSStatus {status}).")
        finally:
            if item is not None:
                api.cf.CFRelease(item)

    def get(self, ref: str) -> str:
        api = _Security()
        service, account = self.service_name.encode(), ref.encode()
        size, data = C.c_uint32(), C.c_void_p()
        status = api.api.SecKeychainFindGenericPassword(
            None, len(service), C.c_char_p(service), len(account), C.c_char_p(account),
            C.byref(size), C.byref(data), None)
        if status == -25300:
            raise CredentialMissing(f"Secret reference not found: {ref}")
        if status:
            raise BrokerStorageFailure(f"Keychain read failed (OSStatus {status}).")
        try:
            return C.string_at(data, size.value).decode()
        finally:
            api.api.SecKeychainItemFreeContent(None, data)

    def delete(self, ref: str) -> None:
        api = _Security()
        item = api.item(self.service_name.encode(), ref.encode())
        if item is None:
            return
        try:
            status = api.api.SecKeychainItemDelete(item)
            if status:
                raise BrokerStorageFailure(f"Keychain delete failed (OSStatus {status}).")
        finally:
            api.cf.CFRelease(item)


class MemorySecretStore:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def put(self, ref: str, secret: str) -> None:
        self._values[ref] = secret

    def get(self, ref: str) -> str:
        try:
            return self._values[ref]
        except KeyError as exc:
            raise CredentialMissing(f"Secret reference not found: {ref}") from exc

    def delete(self, ref: str) -> None:
        self._values.pop(ref, None)
