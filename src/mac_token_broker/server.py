from __future__ import annotations

import errno
import json
import os
import socket
import socketserver
import stat
from pathlib import Path

from .errors import TokenBrokerError
from .peer_identity import authorize_peer, peer_uid
from .runtime import build_broker


class BrokerRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        try:
            payload = json.loads(self.rfile.readline().decode("utf-8"))
            service_id = payload.get("service_id")
            if not isinstance(service_id, str) or not service_id:
                raise ValueError("service_id is required")
            uid = peer_uid(self.request)
            authorize_peer(service_id, uid, self.server.broker.storage)
            value = self.server.broker.get_credential(
                service_id=service_id,
                credential_id=payload.get("credential_id"),
                provider_id=payload.get("provider_id"),
            )
            result = {"ok": True, "credential": value}
        except (TokenBrokerError, ValueError, json.JSONDecodeError) as exc:
            result = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        except Exception:
            result = {"ok": False, "error": "BrokerFailure", "message": "Request handling failed."}
        self.wfile.write((json.dumps(result) + "\n").encode("utf-8"))


class UnixBrokerServer(socketserver.UnixStreamServer):
    def __init__(self, socket_path: Path):
        self.broker = build_broker()
        super().__init__(str(socket_path), BrokerRequestHandler)


def _clear_stale_socket(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError("Refusing to replace non-socket or foreign-owned endpoint.")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        try:
            probe.connect(str(path))
        except OSError as exc:
            if exc.errno != errno.ECONNREFUSED:
                raise RuntimeError("Cannot establish whether socket is stale.") from exc
        else:
            raise RuntimeError("Broker endpoint is already active.")
    path.unlink()


def serve(socket_path: Path) -> None:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    parent = socket_path.parent.stat()
    if parent.st_uid != os.getuid() or parent.st_mode & 0o022:
        raise RuntimeError("Insecure or unowned broker socket directory.")
    _clear_stale_socket(socket_path)
    server = UnixBrokerServer(socket_path)
    os.chmod(socket_path, 0o666)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        if socket_path.exists():
            socket_path.unlink()
