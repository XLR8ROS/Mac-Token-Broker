import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from mac_token_broker.audit import AuditLogger
from mac_token_broker.broker import TokenBroker
from mac_token_broker.errors import CredentialNotAssigned, CredentialRefreshFailed
from mac_token_broker.secrets import MemorySecretStore
from mac_token_broker.storage import BrokerStorage


class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self):
        return json.dumps({"access_token":"google-fresh","expires_in":3600}).encode()


class GoogleProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name)
        storage = BrokerStorage(folder / "registry.sqlite")
        self.addCleanup(storage.close)
        self.secrets = MemorySecretStore()
        self.broker = TokenBroker(storage, self.secrets, AuditLogger(folder / "audit.jsonl"))
        self.broker.register_service("calendar-worker", "Calendar worker")
        self.broker.register_service("mail-worker", "Mail worker")

    def test_google_refresh_and_assignment(self):
        self.broker.add_credential("google-calendar", "google", "old", refresh_secret="refresh",
            expires_at=datetime.now(timezone.utc)-timedelta(minutes=1),
            metadata={"client_id":"client.apps.googleusercontent.com"})
        self.broker.assign("calendar-worker", "google-calendar")
        with self.assertRaises(CredentialNotAssigned):
            self.broker.get_credential("mail-worker", "google-calendar")
        with patch("mac_token_broker.providers.oauth2.urllib.request.urlopen", return_value=FakeResponse()) as mock:
            self.assertEqual(self.broker.get_credential("calendar-worker", "google-calendar"), "google-fresh")
            self.assertEqual(mock.call_args.args[0].full_url,"https://oauth2.googleapis.com/token")
        self.assertEqual(self.broker.get_credential("calendar-worker", "google-calendar"), "google-fresh")

    def test_wrong_endpoint_rejected_before_network(self):
        self.broker.add_credential("google-calendar", "google", "old", refresh_secret="refresh",
            expires_at=datetime.now(timezone.utc)-timedelta(minutes=1),
            metadata={"client_id":"client","token_url":"https://evil.invalid/token"})
        self.broker.assign("calendar-worker", "google-calendar")
        with self.assertRaises(CredentialRefreshFailed):
            self.broker.get_credential("calendar-worker", "google-calendar")


if __name__ == "__main__":
    unittest.main()
