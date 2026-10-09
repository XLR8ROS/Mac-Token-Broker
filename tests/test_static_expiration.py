import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mac_token_broker.audit import AuditLogger
from mac_token_broker.broker import TokenBroker
from mac_token_broker.errors import CredentialInvalid
from mac_token_broker.secrets import MemorySecretStore
from mac_token_broker.storage import BrokerStorage


class ExpirationTests(unittest.TestCase):
    def test_expired_static_credential_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage = BrokerStorage(root / "broker.sqlite")
            try:
                broker = TokenBroker(storage, MemorySecretStore(), AuditLogger(root / "audit.jsonl"))
                broker.register_service("worker", "Worker")
                broker.add_credential(
                    "expired", "static", "expired-secret",
                    expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                )
                broker.assign("worker", "expired")
                with self.assertRaises(CredentialInvalid):
                    broker.get_credential("worker", "expired")
                self.assertNotIn("expired-secret", (root / "audit.jsonl").read_text())
            finally:
                storage.close()


if __name__ == "__main__":
    unittest.main()
