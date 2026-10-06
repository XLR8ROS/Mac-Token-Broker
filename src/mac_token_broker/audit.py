from __future__ import annotations


class AuditLogger:
    """Records broker events without secret values."""

    def record(self, event: str, **fields: object) -> None:
        raise NotImplementedError("Audit backend not implemented yet.")
