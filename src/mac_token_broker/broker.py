from __future__ import annotations


class TokenBroker:
    """Core provider-independent token broker."""

    def get_credential(self, service_id: str, credential_id: str) -> str:
        raise NotImplementedError("Broker core not implemented yet.")
