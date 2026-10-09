# Mac Token Broker

Deterministic standalone credential broker for local Python services on macOS.

## Design

One central broker and one centrally stored copy of a provider credential.
Registered services receive explicit credential assignments. Consumers must not
store provider tokens or implement provider refresh themselves.

## Implemented

- SQLite registry for services, credentials, and assignments
- macOS Keychain secret store
- Provider-independent broker, static credentials, OAuth2 refresh adapter
- Administrative CLI, Unix socket server, and Python client
- JSONL audit log with allowlisted metadata and restricted file permissions
- launchd LaunchAgent installer and startup configuration
- Automated tests for authorization decisions, persistence, expiration,
  OAuth refresh, audit data protection, LaunchAgent import path, and
  fail-closed socket behavior

## Critical security state

**The Unix socket server is intentionally fail-closed.** It does not dispense
secrets, even if a request names a registered service. A caller-provided
`service_id` does not authenticate that caller. An HMAC helper exists but
is not integrated into the service protocol. Merely moving an authentication
key into a shared user Keychain does not provide process isolation when
multiple services run under the same macOS user.

Before production use, establish and verify an enforceable service identity
boundary, such as separate OS accounts with peer-credential authorization,
or an equivalent system-enforced mechanism. An application-level HMAC is
insufficient if another same-user service can obtain its proof material.

The current in-process `TokenBroker.get_credential` handles assignments but
is an administrative/trusted-context API, **not** a safe untrusted-service
interface.

## Run tests

From the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The Mac test environment has been running these tests with Python 3.9.6,
although the package metadata targets Python 3.11 or newer. This discrepancy
must be resolved before the installation can pass acceptance.

## Deployment is not complete

The LaunchAgent is committed, but live Keychain operations, automatic
startup, crash recovery, and per-service access are not yet acceptance-tested.
Do not register production secrets until the service identity gate passes.

## Source

Repository: `XLR8ROS/Mac-Token-Broker`

The Token Broker is standalone and is not a prerequisite for Paperclip's
built-in secrets functionality.
