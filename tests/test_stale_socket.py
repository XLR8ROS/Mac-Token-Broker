import os
import socket
import tempfile
import unittest
from pathlib import Path

from mac_token_broker.server import _clear_stale_socket


class StaleSocketTests(unittest.TestCase):
    def test_recover_unconnected_local_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broker.sock"
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(path))
            server.close()
            _clear_stale_socket(path)
            self.assertFalse(path.exists())

    def test_refuse_active_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broker.sock"
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(path))
            server.listen(1)
            try:
                with self.assertRaises(RuntimeError):
                    _clear_stale_socket(path)
                self.assertTrue(path.exists())
            finally:
                server.close()

    def test_refuse_non_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broker.sock"
            path.write_text("not a socket")
            with self.assertRaises(RuntimeError):
                _clear_stale_socket(path)
            self.assertEqual(path.read_text(), "not a socket")


if __name__ == "__main__":
    unittest.main()
