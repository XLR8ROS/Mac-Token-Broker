from __future__ import annotations

import json
import socket
from pathlib import Path

from .config import DEFAULT_SOCKET
from .errors import BrokerUnavailable, TokenBrokerError


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
                    break
                data += chunk
    except OSError as exc:
        raise BrokerUnavailable(str(exc)) from exc

    response = json.loads(data.decode("utf-8"))
    if not response.get("ok"):
        raise TokenBrokerError(f"{response.get('error')}: {response.get('message')}")
    return response["credential"]
