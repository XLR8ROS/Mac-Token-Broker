from __future__ import annotations

from ..errors import CredentialRefreshFailed
from ..models import CredentialRecord
from ..secrets import SecretStore
from .oauth2 import OAuth2Provider

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleOAuthProvider(OAuth2Provider):
    """Google refresh adapter using the broker's existing OAuth2 lifecycle."""

    provider_id = "google"

    def ensure_usable(self, record: CredentialRecord, secrets: SecretStore):
        if not record.metadata.get("client_id"):
            raise CredentialRefreshFailed("Google credential requires client_id.")
        if record.metadata.get("token_url", GOOGLE_TOKEN_URL) != GOOGLE_TOKEN_URL:
            raise CredentialRefreshFailed("Google credential has a non-Google token endpoint.")
        record.metadata["token_url"] = GOOGLE_TOKEN_URL
        return super().ensure_usable(record, secrets)
