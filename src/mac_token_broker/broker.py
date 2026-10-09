from __future__ import annotations

from datetime import datetime, timezone

from .audit import AuditLogger
from .errors import CredentialNotAssigned, MalformedRequest
from .models import AssignmentRecord, CredentialRecord, ServiceRecord
from .providers.oauth2 import OAuth2Provider
from .providers.static import StaticProvider
from .secrets import SecretStore
from .storage import BrokerStorage


class TokenBroker:
    def __init__(self, storage: BrokerStorage, secrets: SecretStore, audit: AuditLogger) -> None:
        self.storage = storage
        self.secrets = secrets
        self.audit = audit
        self.providers = {
            "static": StaticProvider(),
            "oauth2": OAuth2Provider(),
        }

    def register_service(self, service_id: str, name: str, metadata: dict | None = None) -> None:
        self.storage.add_service(ServiceRecord(service_id=service_id, name=name, metadata=metadata or {}))
        self.audit.record("service_registered", service_id=service_id)

    def remove_service(self, service_id: str) -> None:
        self.storage.remove_service(service_id)
        self.audit.record("service_removed", service_id=service_id)

    def add_credential(
        self,
        credential_id: str,
        provider_id: str,
        secret: str,
        *,
        expires_at=None,
        refresh_secret: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        if provider_id not in self.providers:
            raise MalformedRequest(f"Unsupported provider adapter: {provider_id}")
        secret_ref = f"credential:{credential_id}"
        refresh_ref = f"refresh:{credential_id}" if refresh_secret is not None else None
        record = CredentialRecord(
            credential_id=credential_id,
            provider_id=provider_id,
            secret_ref=secret_ref,
            expires_at=expires_at,
            refresh_ref=refresh_ref,
            metadata=metadata or {},
        )
        # Reserve a unique registry ID before touching Keychain. Duplicate
        # registrations must never overwrite an existing credential secret.
        self.storage.add_credential(record)
        try:
            self.secrets.put(secret_ref, secret)
            if refresh_ref is not None:
                self.secrets.put(refresh_ref, refresh_secret)
        except Exception:
            self.storage.remove_credential(credential_id)
            for ref in (secret_ref, refresh_ref):
                if ref is not None:
                    try:
                        self.secrets.delete(ref)
                    except Exception:
                        pass
            raise
        self.audit.record("credential_added", credential_id=credential_id, provider_id=provider_id)

    def update_credential_secret(self, credential_id: str, secret: str, *, expires_at=None) -> None:
        rec = self.storage.get_credential(credential_id)
        self.secrets.put(rec.secret_ref, secret)
        rec.expires_at = expires_at
        rec.updated_at = datetime.now(timezone.utc)
        self.storage.update_credential(rec)
        self.audit.record("credential_updated", credential_id=credential_id, provider_id=rec.provider_id)

    def remove_credential(self, credential_id: str) -> None:
        rec = self.storage.get_credential(credential_id)
        self.storage.remove_credential(credential_id)
        self.secrets.delete(rec.secret_ref)
        if rec.refresh_ref:
            self.secrets.delete(rec.refresh_ref)
        self.audit.record("credential_removed", credential_id=credential_id, provider_id=rec.provider_id)

    def assign(self, service_id: str, credential_id: str) -> None:
        self.storage.get_service(service_id)
        self.storage.get_credential(credential_id)
        self.storage.assign(AssignmentRecord(service_id=service_id, credential_id=credential_id))
        self.audit.record("assignment_added", service_id=service_id, credential_id=credential_id)

    def revoke(self, service_id: str, credential_id: str) -> None:
        self.storage.revoke(service_id, credential_id)
        self.audit.record("assignment_revoked", service_id=service_id, credential_id=credential_id)

    def get_credential(
        self,
        service_id: str,
        credential_id: str | None = None,
        provider_id: str | None = None,
    ) -> str:
        self.storage.get_service(service_id)
        if bool(credential_id) == bool(provider_id):
            raise MalformedRequest("Supply exactly one of credential_id or provider_id.")

        if credential_id:
            record = self.storage.get_credential(credential_id)
            if not self.storage.is_assigned(service_id, credential_id):
                self.audit.record("credential_request_denied", service_id=service_id, credential_id=credential_id)
                raise CredentialNotAssigned(f"{credential_id} is not assigned to {service_id}")
        else:
            matches = self.storage.find_assigned_by_provider(service_id, provider_id or "")
            if len(matches) == 0:
                self.audit.record("credential_request_denied", service_id=service_id, provider_id=provider_id)
                raise CredentialNotAssigned(f"No {provider_id} credential assigned to {service_id}")
            if len(matches) > 1:
                raise MalformedRequest(
                    f"Multiple {provider_id} credentials are assigned to {service_id}; request credential_id explicitly."
                )
            record = matches[0]

        adapter = self.providers.get(record.provider_id)
        if adapter is None:
            raise MalformedRequest(f"Unsupported provider adapter: {record.provider_id}")

        old_updated_at = record.updated_at
        old_expires_at = record.expires_at
        expiry = record.expires_at
        if expiry is not None and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        from datetime import timedelta
        skew = int(record.metadata.get("refresh_skew_seconds", 60))
        needs_refresh = (
            record.provider_id == "oauth2"
            and expiry is not None
            and expiry <= datetime.now(timezone.utc) + timedelta(seconds=skew)
        )
        if needs_refresh:
            self.audit.record(
                "refresh_attempted",
                service_id=service_id,
                credential_id=record.credential_id,
                provider_id=record.provider_id,
            )

        try:
            value, updated = adapter.ensure_usable(record, self.secrets)
            if updated.updated_at != old_updated_at or updated.expires_at != old_expires_at:
                self.storage.update_credential(updated)
            if needs_refresh:
                self.audit.record(
                    "refresh_succeeded",
                    service_id=service_id,
                    credential_id=record.credential_id,
                    provider_id=record.provider_id,
                )
        except Exception:
            if needs_refresh:
                self.audit.record(
                    "refresh_failed",
                    service_id=service_id,
                    credential_id=record.credential_id,
                    provider_id=record.provider_id,
                )
            raise

        self.audit.record(
            "credential_request_allowed",
            service_id=service_id,
            credential_id=record.credential_id,
            provider_id=record.provider_id,
        )
        return value
