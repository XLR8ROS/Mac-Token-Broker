from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ServiceRecord:
    service_id: str
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CredentialRecord:
    credential_id: str
    provider_id: str
    secret_ref: str
    expires_at: datetime | None = None
    refresh_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssignmentRecord:
    service_id: str
    credential_id: str
