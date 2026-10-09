from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from .errors import CredentialNotAssigned
from .secrets import SecretStore


def auth_ref(service_id: str) -> str:
    return "service-auth:" + service_id


def enroll(service_id: str, store: SecretStore) -> None:
    store.put(auth_ref(service_id), secrets.token_hex(32))


def sign(service_id: str, nonce: str, store: SecretStore) -> str:
    secret = store.get(auth_ref(service_id))
    return hmac.new(secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()


def verify(service_id: str, nonce: str, proof: str, store: SecretStore) -> None:
    expected = sign(service_id, nonce, store)
    if not hmac.compare_digest(expected, proof):
        raise CredentialNotAssigned("Service authentication failed.")
