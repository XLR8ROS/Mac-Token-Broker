import json
import stat
import tempfile
import unittest
from pathlib import Path

from mac_token_broker.audit import AuditLogger


class AuditSafetyTests(unittest.TestCase):
    def test_unknown_fields_are_never_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            logger = AuditLogger(path)
            logger.record(
                "credential_request_denied",
                service_id="worker",
                credential_id="sample",
                raw_token="sensitive-test-token",
                nested={"password": "sensitive-test-password"},
            )
            text = path.read_text()
            record = json.loads(text)
            self.assertEqual(record["service_id"], "worker")
            self.assertNotIn("sensitive-test-token", text)
            self.assertNotIn("sensitive-test-password", text)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
