# Mac Token Broker

Deterministic local Python credential broker for macOS.

## Purpose

Mac Token Broker provides one centralized place for local Python programs and services to obtain the credentials they are authorized to use.

Credentials belong to the broker. Consumer services do not maintain provider tokens, API keys, refresh tokens, per-service secret files, or provider-specific refresh logic.

## Core Rules

- One central broker.
- One copy of a credential unless there is a real reason for another.
- Stable service IDs identify local consumers.
- Services may retrieve only credentials explicitly assigned to them.
- Multiple services may share one centrally managed credential when authorized.
- Provider-specific refresh and renewal behavior stays inside the broker.
- Long-lived credentials remain long-lived when the provider permits it.
- Secret values are never committed to Git or written to logs.
- Failures are explicit. The broker never silently substitutes another credential.

## Planned Interface

Consumers will request credentials through a small local Python-facing interface.

Conceptually:

```python
get_credential(service_id, credential_id)
```

or:

```python
get_credential(service_id, provider_id)
```

The broker will validate the service, enforce assignment authorization, ensure the credential is usable, refresh it when provider rules require refresh, and return the usable credential.

## Project Layout

```text
src/mac_token_broker/
    __init__.py
    broker.py
    errors.py
    models.py
    storage.py
    audit.py
    cli.py
    providers/
        __init__.py
tests/
pyproject.toml
.gitignore
```

Provider modules will remain isolated from broker core logic.

## macOS Runtime

The finished broker will run locally on the Mac as a background service, persist registry and credential state across restarts, start automatically at login or reboot, and restart automatically after failure using the appropriate macOS service mechanism.

## Status

Repository initialized. Implementation is in progress.
