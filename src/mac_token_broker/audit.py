from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

SAFE_FIELDS = frozenset({"service_id", "credential_id", "provider_id", "reason"})


class AuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **fields: object) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
        }
        for key in SAFE_FIELDS:
            value = fields.get(key)
            if value is not None and isinstance(value, (str, int, bool)):
                payload[key] = value
        fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, separators=(",", ":")) + "\n")
        except BaseException:
            os.close(fd) if _fd_open(fd) else None
            raise


def _fd_open(fd: int) -> bool:
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False
