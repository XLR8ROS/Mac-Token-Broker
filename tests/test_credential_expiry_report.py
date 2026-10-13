import importlib.util
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("expiry_report", Path(__file__).resolve().parents[1] / "tools/credential_expiry_report.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CredentialExpiryReportTests(unittest.TestCase):
    def test_known_unknown_and_access_expiry_not_confused(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp)/"registry.sqlite"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE credentials (credential_id TEXT, provider_id TEXT, refresh_ref TEXT, metadata_json TEXT, created_at TEXT)")
            now = datetime(2026, 10, 13, tzinfo=timezone.utc)
            conn.executemany("INSERT INTO credentials VALUES (?,?,?,?,?)", [
                ("google", "google", "refresh:google", json.dumps({"authorization_expires_at": (now+timedelta(days=10)).isoformat()}), now.isoformat()),
                ("unknown", "oauth2", "refresh:unknown", "{}", now.isoformat()),
                ("static", "static", None, "{}", now.isoformat()),
            ])
            conn.commit()
            conn.close()
            result = MODULE.inspect(db, now)
            self.assertEqual([x["status"] for x in result["credentials"]], ["warning", "unknown"])
            self.assertEqual(len(result["credentials"]), 2)


if __name__ == "__main__":
    unittest.main()
