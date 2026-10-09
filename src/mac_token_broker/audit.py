from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **fields: object) -> None:
        forbidden = {"secret", "token", "api_key", "access_token", "refresh_token", "password"}
        safe = {k: v for k, v in fields.items() if k.lower() not in forbidden}
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **safe,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, separators=(",", ":"), default=str) + "\n")
