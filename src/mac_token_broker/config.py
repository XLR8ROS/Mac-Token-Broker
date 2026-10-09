from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_SUPPORT = Path.home() / "Library" / "Application Support" / "XLR8ROS" / "TokenBroker"
RUNTIME_DIR = APP_SUPPORT / "run"
DEFAULT_DB = APP_SUPPORT / "broker.sqlite3"
DEFAULT_AUDIT_LOG = APP_SUPPORT / "audit.jsonl"
DEFAULT_SOCKET = RUNTIME_DIR / "broker.sock"
KEYCHAIN_SERVICE = "com.xlr8ros.token-broker"


@dataclass(frozen=True)
class BrokerConfig:
    db_path: Path = DEFAULT_DB
    audit_path: Path = DEFAULT_AUDIT_LOG
    socket_path: Path = DEFAULT_SOCKET

    def ensure_dirs(self) -> None:
        for path in (self.db_path.parent, self.audit_path.parent, self.socket_path.parent):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(path, 0o700)
