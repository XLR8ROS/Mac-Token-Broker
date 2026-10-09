from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from ..errors import CredentialRefreshFailed
from ..models import CredentialRecord
from ..secrets import SecretStore


class OAuth2Provider:
    provider_id = "oauth2"

    def ensure_usable(self, record: CredentialRecord, secrets: SecretStore) -> tuple[str, CredentialRecord]:
        now = datetime.now(timezone.utc)
        skew = int(record.metadata.get("refresh_skew_seconds", 60))
        expiry = record.expires_at
        if expiry is not None and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry is None or expiry > now + timedelta(seconds=skew):
            return secrets.get(record.secret_ref), record

        if not record.refresh_ref:
            raise CredentialRefreshFailed(f"{record.credential_id} is expired and has no refresh credential.")

        token_url = record.metadata.get("token_url")
        client_id = record.metadata.get("client_id")
        if not token_url or not client_id:
            raise CredentialRefreshFailed("OAuth credential metadata requires token_url and client_id.")

        body = {
            "grant_type": "refresh_token",
            "refresh_token": secrets.get(record.refresh_ref),
            "client_id": client_id,
        }
        client_secret_ref = record.metadata.get("client_secret_ref")
        if client_secret_ref:
            body["client_secret"] = secrets.get(client_secret_ref)

        request = urllib.request.Request(
            token_url,
            data=urllib.parse.urlencode(body).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode())
        except Exception as exc:
            raise CredentialRefreshFailed(str(exc)) from exc

        access_token = payload.get("access_token")
        if not access_token:
            raise CredentialRefreshFailed("Provider refresh response did not include access_token.")

        secrets.put(record.secret_ref, access_token)
        new_refresh = payload.get("refresh_token")
        if new_refresh:
            secrets.put(record.refresh_ref, new_refresh)

        expires_in = payload.get("expires_in")
        record.expires_at = now + timedelta(seconds=int(expires_in)) if expires_in is not None else None
        record.updated_at = now
        return access_token, record
