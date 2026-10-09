from __future__ import annotations

from .audit import AuditLogger
from .broker import TokenBroker
from .config import BrokerConfig
from .secrets import MacOSKeychainStore
from .storage import BrokerStorage


def build_broker(config: BrokerConfig | None = None) -> TokenBroker:
    cfg = config or BrokerConfig()
    cfg.ensure_dirs()
    return TokenBroker(
        storage=BrokerStorage(cfg.db_path),
        secrets=MacOSKeychainStore(),
        audit=AuditLogger(cfg.audit_path),
    )
