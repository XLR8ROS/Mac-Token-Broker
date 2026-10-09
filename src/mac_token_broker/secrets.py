from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol

from .config import KEYCHAIN_SERVICE
from .errors import BrokerStorageFailure, CredentialMissing


class SecretStore(Protocol):
    def put(self, ref: str, secret: str) -> None: ...
    def get(self, ref: str) -> str: ...
    def delete(self, ref: str) -> None: ...


@dataclass
class MacOSKeychainStore:
    service_name: str = KEYCHAIN_SERVICE

    def put(self, ref: str, secret: str) -> None:
        proc = subprocess.run(
            ["security", "add-generic-password", "-U", "-a", ref, "-s", self.service_name, "-w", secret],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise BrokerStorageFailure(proc.stderr.strip() or "Unable to store secret in macOS Keychain.")

    def get(self, ref: str) -> str:
        proc = subprocess.run(
            ["security", "find-generic-password", "-a", ref, "-s", self.service_name, "-w"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise CredentialMissing(f"Secret reference not found: {ref}")
        return proc.stdout.rstrip("\n")

    def delete(self, ref: str) -> None:
        proc = subprocess.run(
            ["security", "delete-generic-password", "-a", ref, "-s", self.service_name],
            capture_output=True,
            text=True,
        )
        if proc.returncode not in (0, 44):
            raise BrokerStorageFailure(proc.stderr.strip() or "Unable to delete secret from macOS Keychain.")


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
