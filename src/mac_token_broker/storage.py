from __future__ import annotations


class BrokerStorage:
    """Persistent registry/metadata storage abstraction.

    Secret values are intentionally not stored directly in this layer.
    """

    def __init__(self) -> None:
        raise NotImplementedError("Storage backend not implemented yet.")
