from __future__ import annotations

from ..models import CredentialRecord
from ..secrets import SecretStore


class StaticProvider:
    provider_id = "static"

    def ensure_usable(self, record: CredentialRecord, secrets: SecretStore) -> tuple[str, CredentialRecord]:
        return secrets.get(record.secret_ref), record
