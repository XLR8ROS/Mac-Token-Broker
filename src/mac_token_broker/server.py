from __future__ import annotations

import json
import os
import socketserver
from pathlib import Path

from .errors import TokenBrokerError
from .runtime import build_broker


class BrokerRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        try:
            payload = json.loads(self.rfile.readline().decode("utf-8"))
            service_id = payload.get("service_id")
            if not service_id:
                raise ValueError("service_id is required")
            value = self.server.broker.get_credential(
                service_id=service_id,
                credential_id=payload.get("credential_id"),
                provider_id=payload.get("provider_id"),
            )
            result = {"ok": True, "credential": value}
        except (TokenBrokerError, ValueError, json.JSONDecodeError) as exc:
            result = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        except Exception as exc:
            result = {"ok": False, "error": "BrokerFailure", "message": str(exc)}
        self.wfile.write((json.dumps(result) + "\n").encode("utf-8"))


class UnixBrokerServer(socketserver.UnixStreamServer):
    def __init__(self, socket_path: Path):
        self.broker = build_broker()
        super().__init__(str(socket_path), BrokerRequestHandler)


def serve(socket_path: Path) -> None:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    server = UnixBrokerServer(socket_path)
    os.chmod(socket_path, 0o600)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        if socket_path.exists():
            socket_path.unlink()
