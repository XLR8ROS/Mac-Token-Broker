import json
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path

from mac_token_broker.client import get_credential
from mac_token_broker.errors import BrokerUnavailable, CredentialNotAssigned


class DeniedHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.rfile.readline()
        self.wfile.write((json.dumps({
            "ok": False, "error": "CredentialNotAssigned",
            "message": "Not assigned",
        }) + "\n").encode())


class ClientErrorTests(unittest.TestCase):
    def test_denial_remains_distinct_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "socket"
            with socketserver.UnixStreamServer(str(path), DeniedHandler) as server:
                worker = threading.Thread(target=server.handle_request, daemon=True)
                worker.start()
                with self.assertRaises(CredentialNotAssigned):
                    get_credential("worker", credential_id="private", socket_path=path)
                worker.join(timeout=2)

    def test_unavailable_broker_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(BrokerUnavailable):
                get_credential("worker", credential_id="private", socket_path=Path(tmp) / "missing")


if __name__ == "__main__":
    unittest.main()
