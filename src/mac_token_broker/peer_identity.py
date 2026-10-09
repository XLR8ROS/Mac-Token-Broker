from __future__ import annotations

import ctypes
import os
import socket
import sys

from .errors import CredentialNotAssigned


def peer_uid(sock: socket.socket) -> int:
    """Return UID bound to connected AF_UNIX peer by the operating system."""
    if sys.platform != "darwin":
        raise CredentialNotAssigned("Unix peer authentication requires macOS.")
    libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    uid = ctypes.c_uint()
    gid = ctypes.c_uint()
    rc = libc.getpeereid(ctypes.c_int(sock.fileno()), ctypes.byref(uid), ctypes.byref(gid))
    if rc != 0:
        raise CredentialNotAssigned("Unable to verify socket peer identity.")
    return int(uid.value)


def authorize_peer(service_id: str, uid: int, storage) -> None:
    rec = storage.get_service(service_id)
    required = rec.metadata.get("peer_uid")
    if type(required) is not int or required != uid:
        raise CredentialNotAssigned("Service process identity does not match registration.")
    # One dedicated OS identity per independently authorized service.
    for other in storage.list_services():
        if other.service_id != service_id and other.metadata.get("peer_uid") == uid:
            raise CredentialNotAssigned("OS user is shared by multiple registered services.")
    if uid == os.getuid():
        raise CredentialNotAssigned("Broker owner identity cannot authenticate as a consumer.")
