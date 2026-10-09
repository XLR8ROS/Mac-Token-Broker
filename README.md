# Mac Token Broker

Standalone Python credential broker for local XOS services on macOS.

## Operating principle

One central credential store, one registry, and explicit service-to-credential
assignments. Consumers request only assigned credentials; the broker manages
the provider lifecycle, persistence, refresh, and auditing.

## Implemented

- SQLite service, credential, and assignment registry
- Native Security.framework macOS Keychain secret storage (no secrets in argv)
- Static and OAuth2 refresh adapters, with expiration handling
- Administrative CLI, Unix-domain socket IPC, and Python client
- Kernel-reported macOS peer UID verification via `getpeereid`
- Allowlisted audit metadata and restrictive filesystem permissions
- LaunchAgent installation, RunAtLoad, KeepAlive, and safe stale-socket recovery
- Typed errors for unknown service, denied assignment, missing/invalid
  credential, refresh failure, storage failure, and unavailable broker

## Verified Mac state (October 9, 2026)

The LaunchAgent `com.xlr8ros.token-broker` runs from the canonical checkout
`/Users/reginaldberry/Projects/Mac-Token-Broker` using macOS Python 3.9.6.

Verified:

- Native Keychain store, retrieve, rotate, and delete using synthetic values
- Explicit denial of a real local socket request from a mismatched macOS UID
- Crash recovery by forcing SIGKILL through launchctl, then verifying restart
- Correct startup module path and Unix socket recreation
- 20 automated tests passing on the Mac
- No production credentials provisioned

To inspect:

```sh
cd /Users/reginaldberry/Projects/Mac-Token-Broker
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m mac_token_broker.cli status
launchctl print gui/$(id -u)/com.xlr8ros.token-broker
```

## Critical deployment dependency

**Cross-user authorized retrieval is not yet acceptance-tested.** A caller
cannot authenticate merely by asserting its `service_id`, and consumers
running under the broker owner's UID are deliberately denied.

XOS programs may run under the broker owner's macOS account. The socket is
restricted to that local account (mode 0600 in an owner-only directory), and
registered service IDs plus assignments are used for routing. There is no
requirement to create separate macOS accounts for ordinary XOS programs.
This deliberately trusts processes already running as that macOS user: a
malicious process under the same account could impersonate another service.
A name, file hash, or fingerprint alone is not a reliable defense against
such a same-user compromise.

Service registration uses:

```sh
PYTHONPATH=src python3 -m mac_token_broker.cli service-add SERVICE_ID "Service Name" --peer-uid UID
```

The optional UID defaults to the Mac account running the broker. Multiple XOS
services may share that account. Run administrative CLI commands only from the
broker owner's trusted account.

The owner-only socket is at
`~/Library/Application Support/XLR8ROS/TokenBroker/run/broker.sock`.
Credential delivery requires an approved service ID and assignment. The SQLite registry and Keychain remain private to
the broker account.

## Operational caution

Do not add production credentials until the cross-user positive retrieval
test, negative cross-user impersonation test, and full acceptance verification
have passed. Native Keychain tests use synthetic credentials only.

This broker is standalone and does not replace Paperclip's own secret handling.
