import os
import socket
import unittest
from unittest.mock import Mock, patch

from mac_token_broker.errors import CredentialNotAssigned
from mac_token_broker.models import ServiceRecord
from mac_token_broker.peer_identity import authorize_peer, peer_uid


class PeerIdentityTests(unittest.TestCase):
    def test_real_macos_socket_reports_kernel_peer_uid(self):
        left, right = socket.socketpair()
        try:
            self.assertEqual(peer_uid(left), os.getuid())
        finally:
            left.close()
            right.close()

    def test_uid_mismatch_denied(self):
        store = Mock()
        store.get_service.return_value = ServiceRecord("worker", "Worker", {"peer_uid": 902})
        with self.assertRaises(CredentialNotAssigned):
            authorize_peer("worker", 903, store)

    def test_shared_nonowner_uid_denied(self):
        store = Mock()
        store.get_service.return_value = ServiceRecord("worker", "Worker", {"peer_uid": 902})
        store.list_services.return_value = [
            ServiceRecord("worker", "Worker", {"peer_uid": 902}),
            ServiceRecord("other", "Other", {"peer_uid": 902}),
        ]
        with self.assertRaises(CredentialNotAssigned):
            authorize_peer("worker", 902, store)

    def test_same_owner_uid_allowed(self):
        store = Mock()
        store.get_service.return_value = ServiceRecord("stenographer", "Stenographer", {"peer_uid": 501})
        with patch("mac_token_broker.peer_identity.os.getuid", return_value=501):
            authorize_peer("stenographer", 501, store)

    def test_dedicated_different_uid_allowed(self):
        store = Mock()
        store.get_service.return_value = ServiceRecord("worker", "Worker", {"peer_uid": 902})
        store.list_services.return_value = [
            ServiceRecord("worker", "Worker", {"peer_uid": 902}),
            ServiceRecord("other", "Other", {"peer_uid": 903}),
        ]
        with patch("mac_token_broker.peer_identity.os.getuid", return_value=501):
            authorize_peer("worker", 902, store)


if __name__ == "__main__":
    unittest.main()
