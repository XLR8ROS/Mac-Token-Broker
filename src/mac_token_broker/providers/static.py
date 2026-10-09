from __future__ import annotations

from datetime import datetime, timezone

from ..errors import CredentialInvalid
from ..models import CredentialRecord
from ..secrets import SecretStore


class StaticProvider:
    provider_id = "static"

    def ensure_usable(self, record: CredentialRecord, secrets: SecretStore) -> tuple[str, CredentialRecord]:
        if record.expires_at is not None:
            expiry = record.expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc):
                raise CredentialInvalid(f"Credential {record.credential_id} has expired.")
        return secrets.get(record.secret_ref), record
