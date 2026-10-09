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

Every independently authorized consumer needs its own dedicated macOS service
account (UID). The administrator must create or designate those accounts,
arrange for service processes to run under their respective UIDs, and permit
an end-to-end retrieval test. The remote execution account cannot perform
these privileged account changes.

Service registration uses:

```sh
PYTHONPATH=src python3 -m mac_token_broker.cli service-add SERVICE_ID "Service Name" --peer-uid UID
```

The UID must be a dedicated, non-root OS identity. Do not register multiple
services with the same UID. Run administrative CLI commands only from the
broker owner's trusted account.

The shared socket is at
`/Users/Shared/XLR8ROS-TokenBroker/broker.sock`. Its name is discoverable,
but secret delivery is conditional on kernel-verified UID and explicit
credential assignment. The SQLite registry and Keychain remain private to
the broker account.

## Operational caution

Do not add production credentials until the cross-user positive retrieval
test, negative cross-user impersonation test, and full acceptance verification
have passed. Native Keychain tests use synthetic credentials only.

This broker is standalone and does not replace Paperclip's own secret handling.
