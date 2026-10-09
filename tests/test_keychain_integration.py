import sys
import unittest
import uuid

from mac_token_broker.errors import CredentialMissing
from mac_token_broker.secrets import MacOSKeychainStore


@unittest.skipUnless(sys.platform == "darwin", "Requires macOS Keychain")
class MacOSKeychainIntegrationTests(unittest.TestCase):
    def test_secret_lifecycle_without_cli(self):
        reference = "integration-" + uuid.uuid4().hex
        store = MacOSKeychainStore(service_name="com.xlr8ros.token-broker-integration")
        try:
            store.put(reference, "test-synthetic-first")
            self.assertEqual(store.get(reference), "test-synthetic-first")
            store.put(reference, "test-synthetic-second")
            self.assertEqual(store.get(reference), "test-synthetic-second")
        finally:
            store.delete(reference)
        with self.assertRaises(CredentialMissing):
            store.get(reference)


if __name__ == "__main__":
    unittest.main()
