import tempfile
import unittest
from pathlib import Path

from mac_token_broker.audit import AuditLogger
from mac_token_broker.broker import TokenBroker
from mac_token_broker.errors import CredentialNotAssigned, UnknownService
from mac_token_broker.secrets import MemorySecretStore
from mac_token_broker.storage import BrokerStorage


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = Path(self.tmp.name)
        self.db = p / "registry.sqlite3"
        self.audit = p / "audit.jsonl"
        self.secrets = MemorySecretStore()
        self.storage = BrokerStorage(self.db)
        self.broker = TokenBroker(self.storage, self.secrets, AuditLogger(self.audit))

    def test_authorized_shared_credential_and_denials(self):
        b = self.broker
        b.register_service("one", "First Service")
        b.register_service("two", "Second Service")
        b.register_service("unassigned", "Unassigned")
        b.add_credential("shared", "static", "test-private-value")
        b.assign("one", "shared")
        b.assign("two", "shared")
        self.assertEqual(b.get_credential("one", "shared"), "test-private-value")
        self.assertEqual(b.get_credential("two", provider_id="static"), "test-private-value")
        with self.assertRaises(CredentialNotAssigned):
            b.get_credential("unassigned", "shared")
        with self.assertRaises(UnknownService):
            b.get_credential("unknown", "shared")
        self.assertNotIn("test-private-value", self.audit.read_text())

    def test_registry_restart_persistence(self):
        self.broker.register_service("one", "First Service")
        self.broker.add_credential("shared", "static", "test-private-value")
        self.broker.assign("one", "shared")
        self.storage.close()
        reopened = BrokerStorage(self.db)
        self.addCleanup(reopened.close)
        b = TokenBroker(reopened, self.secrets, AuditLogger(self.audit))
        self.assertEqual(b.get_credential("one", "shared"), "test-private-value")
        b.revoke("one", "shared")
        with self.assertRaises(CredentialNotAssigned):
            b.get_credential("one", "shared")


if __name__ == "__main__":
    unittest.main()
