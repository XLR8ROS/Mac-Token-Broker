import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from mac_token_broker.errors import CredentialNotAssigned
from mac_token_broker.server import UnixBrokerServer


class SocketAuthenticationTests(unittest.TestCase):
    def exchange(self, uid, authorized):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broker.sock"
            with patch("mac_token_broker.server.build_broker") as make_broker:
                make_broker.return_value.get_credential.return_value = "test-value"
                server = UnixBrokerServer(path)
            try:
                worker = threading.Thread(target=server.handle_request, daemon=True)
                worker.start()
                with patch("mac_token_broker.server.peer_uid", return_value=uid), patch(
                    "mac_token_broker.server.authorize_peer",
                    side_effect=None if authorized else CredentialNotAssigned("not authorized"),
                ) as authorization:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                        client.connect(str(path))
                        client.sendall((json.dumps({
                            "service_id": "worker",
                            "credential_id": "test-credential",
                        }) + "\n").encode())
                        result = json.loads(client.makefile("rb").readline())
                    worker.join(timeout=2)
                    authorization.assert_called_once()
                if authorized:
                    make_broker.return_value.get_credential.assert_called_once()
                else:
                    make_broker.return_value.get_credential.assert_not_called()
                return result
            finally:
                server.server_close()

    def test_unverified_peer_cannot_retrieve_secret(self):
        result = self.exchange(501, authorized=False)
        self.assertFalse(result["ok"])
        self.assertNotIn("test-value", json.dumps(result))

    def test_verified_peer_dispatches_assigned_request(self):
        result = self.exchange(902, authorized=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["credential"], "test-value")


if __name__ == "__main__":
    unittest.main()
