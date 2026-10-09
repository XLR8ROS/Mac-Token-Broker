import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from mac_token_broker.audit import AuditLogger
from mac_token_broker.broker import TokenBroker
from mac_token_broker.errors import CredentialRefreshFailed
from mac_token_broker.secrets import MemorySecretStore
from mac_token_broker.storage import BrokerStorage


class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self):
        return json.dumps({
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }).encode()


class OAuthTests(unittest.TestCase):
    def test_expired_refreshes_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            store = BrokerStorage(folder / "broker.sqlite")
            self.addCleanup(store.close)
            secrets = MemorySecretStore()
            broker = TokenBroker(store, secrets, AuditLogger(folder / "audit.jsonl"))
            broker.register_service("worker", "Worker")
            broker.add_credential(
                "oauth", "oauth2", "old-access",
                refresh_secret="old-refresh",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                metadata={"token_url": "https://example.invalid/token", "client_id": "demo"},
            )
            broker.assign("worker", "oauth")
            with patch("mac_token_broker.providers.oauth2.urllib.request.urlopen", return_value=FakeResponse()) as request:
                self.assertEqual(broker.get_credential("worker", "oauth"), "new-access")
                request.assert_called_once()
            self.assertEqual(secrets.get("refresh:oauth"), "new-refresh")
            self.assertGreater(store.get_credential("oauth").expires_at, datetime.now(timezone.utc))
            audit = (folder / "audit.jsonl").read_text()
            self.assertIn("refresh_succeeded", audit)
            self.assertNotIn("new-access", audit)
            self.assertNotIn("old-refresh", audit)

    def test_expired_without_refresh_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            store = BrokerStorage(folder / "broker.sqlite")
            self.addCleanup(store.close)
            broker = TokenBroker(store, MemorySecretStore(), AuditLogger(folder / "audit.jsonl"))
            broker.register_service("worker", "Worker")
            broker.add_credential("oauth", "oauth2", "expired",
                                  expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
            broker.assign("worker", "oauth")
            with self.assertRaises(CredentialRefreshFailed):
                broker.get_credential("worker", "oauth")


if __name__ == "__main__":
    unittest.main()
