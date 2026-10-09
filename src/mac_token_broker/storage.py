from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .errors import BrokerStorageFailure, CredentialMissing, UnknownService
from .models import AssignmentRecord, CredentialRecord, ServiceRecord


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class BrokerStorage:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(self.path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            self._migrate()
        except sqlite3.Error as exc:
            raise BrokerStorageFailure(str(exc)) from exc

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS services (
                service_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS credentials (
                credential_id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                secret_ref TEXT NOT NULL UNIQUE,
                expires_at TEXT,
                refresh_ref TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assignments (
                service_id TEXT NOT NULL,
                credential_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(service_id, credential_id),
                FOREIGN KEY(service_id) REFERENCES services(service_id) ON DELETE CASCADE,
                FOREIGN KEY(credential_id) REFERENCES credentials(credential_id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def add_service(self, rec: ServiceRecord) -> None:
        try:
            self.conn.execute(
                "INSERT INTO services(service_id,name,metadata_json,created_at) VALUES(?,?,?,?)",
                (rec.service_id, rec.name, json.dumps(rec.metadata), rec.created_at.isoformat()),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            raise BrokerStorageFailure(str(exc)) from exc

    def remove_service(self, service_id: str) -> None:
        self.conn.execute("DELETE FROM services WHERE service_id=?", (service_id,))
        self.conn.commit()

    def get_service(self, service_id: str) -> ServiceRecord:
        row = self.conn.execute("SELECT * FROM services WHERE service_id=?", (service_id,)).fetchone()
        if row is None:
            raise UnknownService(service_id)
        return ServiceRecord(
            service_id=row["service_id"],
            name=row["name"],
            metadata=json.loads(row["metadata_json"]),
            created_at=_dt(row["created_at"]),
        )

    def list_services(self) -> list[ServiceRecord]:
        rows = self.conn.execute("SELECT service_id FROM services ORDER BY service_id")
        return [self.get_service(row["service_id"]) for row in rows]

    def add_credential(self, rec: CredentialRecord) -> None:
        try:
            self.conn.execute(
                """INSERT INTO credentials(
                    credential_id,provider_id,secret_ref,expires_at,refresh_ref,metadata_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    rec.credential_id,
                    rec.provider_id,
                    rec.secret_ref,
                    rec.expires_at.isoformat() if rec.expires_at else None,
                    rec.refresh_ref,
                    json.dumps(rec.metadata),
                    rec.created_at.isoformat(),
                    rec.updated_at.isoformat(),
                ),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            raise BrokerStorageFailure(str(exc)) from exc

    def update_credential(self, rec: CredentialRecord) -> None:
        cur = self.conn.execute(
            """UPDATE credentials SET provider_id=?, secret_ref=?, expires_at=?, refresh_ref=?,
               metadata_json=?, updated_at=? WHERE credential_id=?""",
            (
                rec.provider_id,
                rec.secret_ref,
                rec.expires_at.isoformat() if rec.expires_at else None,
                rec.refresh_ref,
                json.dumps(rec.metadata),
                rec.updated_at.isoformat(),
                rec.credential_id,
            ),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise CredentialMissing(rec.credential_id)

    def remove_credential(self, credential_id: str) -> None:
        self.conn.execute("DELETE FROM credentials WHERE credential_id=?", (credential_id,))
        self.conn.commit()

    def get_credential(self, credential_id: str) -> CredentialRecord:
        row = self.conn.execute("SELECT * FROM credentials WHERE credential_id=?", (credential_id,)).fetchone()
        if row is None:
            raise CredentialMissing(credential_id)
        return CredentialRecord(
            credential_id=row["credential_id"],
            provider_id=row["provider_id"],
            secret_ref=row["secret_ref"],
            expires_at=_dt(row["expires_at"]),
            refresh_ref=row["refresh_ref"],
            metadata=json.loads(row["metadata_json"]),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
        )

    def list_credentials(self) -> list[CredentialRecord]:
        rows = self.conn.execute("SELECT credential_id FROM credentials ORDER BY credential_id")
        return [self.get_credential(row["credential_id"]) for row in rows]

    def assign(self, rec: AssignmentRecord) -> None:
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO assignments(service_id,credential_id,created_at) VALUES(?,?,?)",
                (rec.service_id, rec.credential_id, rec.created_at.isoformat()),
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            raise BrokerStorageFailure(str(exc)) from exc

    def revoke(self, service_id: str, credential_id: str) -> None:
        self.conn.execute(
            "DELETE FROM assignments WHERE service_id=? AND credential_id=?",
            (service_id, credential_id),
        )
        self.conn.commit()

    def is_assigned(self, service_id: str, credential_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM assignments WHERE service_id=? AND credential_id=?",
            (service_id, credential_id),
        ).fetchone()
        return row is not None

    def assignments_for_service(self, service_id: str) -> list[AssignmentRecord]:
        self.get_service(service_id)
        rows = self.conn.execute(
            "SELECT * FROM assignments WHERE service_id=? ORDER BY credential_id",
            (service_id,),
        )
        return [
            AssignmentRecord(
                service_id=row["service_id"],
                credential_id=row["credential_id"],
                created_at=_dt(row["created_at"]),
            )
            for row in rows
        ]

    def find_assigned_by_provider(self, service_id: str, provider_id: str) -> list[CredentialRecord]:
        self.get_service(service_id)
        rows = self.conn.execute(
            """SELECT c.credential_id FROM credentials c
               JOIN assignments a ON a.credential_id=c.credential_id
               WHERE a.service_id=? AND c.provider_id=?
               ORDER BY c.credential_id""",
            (service_id, provider_id),
        )
        return [self.get_credential(row["credential_id"]) for row in rows]
