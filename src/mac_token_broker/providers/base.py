from __future__ import annotations

from typing import Protocol

from ..models import CredentialRecord
from ..secrets import SecretStore


class ProviderAdapter(Protocol):
    provider_id: str

    def ensure_usable(self, record: CredentialRecord, secrets: SecretStore) -> tuple[str, CredentialRecord]:
        ...
