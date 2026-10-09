from __future__ import annotations
import argparse
import getpass
import json
from datetime import datetime
from .config import DEFAULT_SOCKET
from .launchd import install as install_launchd, uninstall as uninstall_launchd
from .runtime import build_broker
from .server import serve

def build_parser():
    p = argparse.ArgumentParser(prog="token-broker")
    p.add_argument("--version", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    for cmd in ("service-add", "service-remove", "service-list", "credential-add", "credential-update", "credential-remove", "credential-list", "assign", "revoke", "assignments", "status", "serve", "install", "uninstall"):
        s = sub.add_parser(cmd)
        if cmd == "service-add":
            s.add_argument("service_id"); s.add_argument("name"); s.add_argument("--peer-uid", type=int, required=True)
        elif cmd in ("service-remove", "assignments"):
            s.add_argument("service_id")
        elif cmd == "credential-add":
            s.add_argument("credential_id"); s.add_argument("provider_id", choices=["static", "oauth2"])
            s.add_argument("--expires-at"); s.add_argument("--token-url"); s.add_argument("--client-id")
        elif cmd == "credential-update":
            s.add_argument("credential_id"); s.add_argument("--expires-at")
        elif cmd == "credential-remove":
            s.add_argument("credential_id")
        elif cmd in ("assign", "revoke"):
            s.add_argument("service_id"); s.add_argument("credential_id")
    return p

def main():
    p = build_parser()
    a = p.parse_args()
    if a.version:
        from . import __version__
        print(__version__)
        return 0
    if not a.cmd:
        p.print_help(); return 0
    if a.cmd == "serve":
        serve(DEFAULT_SOCKET); return 0
    if a.cmd == "install":
        print(install_launchd()); return 0
    if a.cmd == "uninstall":
        uninstall_launchd(); return 0
    b = build_broker()
    if a.cmd == "service-add":
        if a.peer_uid <= 0:
            p.error("--peer-uid must be a dedicated non-root macOS service UID")
        b.register_service(a.service_id, a.name, metadata={"peer_uid": a.peer_uid})
    elif a.cmd == "service-remove": b.remove_service(a.service_id)
    elif a.cmd == "service-list":
        print(json.dumps([vars(x) for x in b.storage.list_services()], default=str, indent=2))
    elif a.cmd == "credential-add":
        secret = getpass.getpass("Credential secret: ")
        refresh = getpass.getpass("Refresh secret: ") if a.provider_id == "oauth2" else None
        metadata = {}
        if a.provider_id == "oauth2":
            if not a.token_url or not a.client_id:
                p.error("OAuth2 requires --token-url and --client-id")
            metadata = {"token_url": a.token_url, "client_id": a.client_id}
        b.add_credential(a.credential_id, a.provider_id, secret,
                         expires_at=datetime.fromisoformat(a.expires_at) if a.expires_at else None,
                         refresh_secret=refresh, metadata=metadata)
    elif a.cmd == "credential-update":
        secret = getpass.getpass("Replacement secret: ")
        b.update_credential_secret(a.credential_id, secret,
                                   expires_at=datetime.fromisoformat(a.expires_at) if a.expires_at else None)
    elif a.cmd == "credential-remove": b.remove_credential(a.credential_id)
    elif a.cmd == "credential-list":
        print(json.dumps([{"credential_id": x.credential_id, "provider_id": x.provider_id,
                           "expires_at": x.expires_at, "has_refresh": bool(x.refresh_ref)}
                          for x in b.storage.list_credentials()], default=str, indent=2))
    elif a.cmd == "assign": b.assign(a.service_id, a.credential_id)
    elif a.cmd == "revoke": b.revoke(a.service_id, a.credential_id)
    elif a.cmd == "assignments":
        print(json.dumps([vars(x) for x in b.storage.assignments_for_service(a.service_id)], default=str, indent=2))
    elif a.cmd == "status":
        print(json.dumps({"services": len(b.storage.list_services()),
                          "credentials": len(b.storage.list_credentials()),
                          "socket": str(DEFAULT_SOCKET)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
