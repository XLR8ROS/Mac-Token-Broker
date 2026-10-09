from __future__ import annotations

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
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
