from __future__ import annotations

import json
import socket
from pathlib import Path

from .config import DEFAULT_SOCKET
from .errors import (
    BrokerStorageFailure, BrokerUnavailable, CredentialInvalid,
    CredentialMissing, CredentialNotAssigned, CredentialRefreshFailed,
    MalformedRequest, ProviderRejectedCredential, TokenBrokerError,
    UnknownService,
)

ERROR_TYPES = {
    cls.__name__: cls for cls in (
        BrokerStorageFailure, BrokerUnavailable, CredentialInvalid,
        CredentialMissing, CredentialNotAssigned, CredentialRefreshFailed,
        MalformedRequest, ProviderRejectedCredential, UnknownService,
    )
}


def get_credential(
    service_id: str,
    credential_id: str | None = None,
    provider_id: str | None = None,
    *,
    socket_path: Path = DEFAULT_SOCKET,
    timeout: float = 5.0,
) -> str:
    payload = {
        "service_id": service_id,
        "credential_id": credential_id,
        "provider_id": provider_id,
    }
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(str(socket_path))
            sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    raise BrokerUnavailable("Broker disconnected without a complete response.")
                data += chunk
    except OSError as exc:
        raise BrokerUnavailable("Unable to communicate with local credential broker.") from exc

    try:
        response = json.loads(data.decode("utf-8"))
        if not isinstance(response, dict):
            raise ValueError("Unexpected broker response.")
    except (ValueError, UnicodeDecodeError) as exc:
        raise BrokerUnavailable("Invalid broker response.") from exc

    if not response.get("ok"):
        error = str(response.get("error", "TokenBrokerError"))
        cls = ERROR_TYPES.get(error, TokenBrokerError)
        raise cls(str(response.get("message", error)))
    credential = response.get("credential")
    if not isinstance(credential, str):
        raise BrokerUnavailable("Broker response omitted a valid credential.")
    return credential
