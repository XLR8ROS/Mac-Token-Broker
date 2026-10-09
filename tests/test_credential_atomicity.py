import tempfile
import unittest
from pathlib import Path

from mac_token_broker.audit import AuditLogger
from mac_token_broker.broker import TokenBroker
from mac_token_broker.errors import BrokerStorageFailure
from mac_token_broker.secrets import MemorySecretStore
from mac_token_broker.storage import BrokerStorage


class CredentialAtomicityTests(unittest.TestCase):
    def test_duplicate_registration_preserves_original_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = BrokerStorage(root / "broker.sqlite")
            try:
                secrets = MemorySecretStore()
                broker = TokenBroker(storage, secrets, AuditLogger(root / "audit.jsonl"))
                broker.register_service("worker", "Worker")
                broker.add_credential("shared", "static", "original-synthetic-secret")
                broker.assign("worker", "shared")
                with self.assertRaises(BrokerStorageFailure):
                    broker.add_credential("shared", "static", "replacement-synthetic-secret")
                self.assertEqual(broker.get_credential("worker", "shared"), "original-synthetic-secret")
                self.assertEqual(len(storage.list_credentials()), 1)
            finally:
                storage.close()


if __name__ == "__main__":
    unittest.main()
