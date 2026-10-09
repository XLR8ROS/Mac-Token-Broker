import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from mac_token_broker.server import UnixBrokerServer


class SocketAuthenticationTests(unittest.TestCase):
    def test_service_id_claim_alone_never_returns_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broker.sock"
            with patch("mac_token_broker.server.build_broker") as make_broker:
                make_broker.return_value.get_credential.return_value = "must-not-leak"
                server = UnixBrokerServer(path)
            try:
                worker = threading.Thread(target=server.handle_request, daemon=True)
                worker.start()
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(str(path))
                    client.sendall((json.dumps({
                        "service_id": "trusted-service",
                        "credential_id": "secret-a",
                    }) + "\n").encode())
                    result = json.loads(client.makefile("rb").readline())
                worker.join(timeout=2)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"], "ServiceAuthenticationUnavailable")
                self.assertNotIn("must-not-leak", json.dumps(result))
                make_broker.return_value.get_credential.assert_not_called()
            finally:
                server.server_close()


if __name__ == "__main__":
    unittest.main()
