"""Read-only XOS Token Broker long-lived credential expiry report.

Run weekly via the system scheduler. No access tokens or secrets are read.
"""
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path.home() / "Library/Application Support/XLR8ROS/TokenBroker/broker.sqlite3"
DEFAULT_REPORT = Path.home() / "Library/Application Support/XLR8ROS/TokenBroker/expiry-status.json"


def parse_utc(value):
    if not value:
        return None
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)


def inspect(db_path, now=None, warning_days=14):
    now = now or datetime.now(timezone.utc)
    conn = sqlite3.connect("file:" + str(db_path) + "?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT credential_id, provider_id, refresh_ref, metadata_json, created_at FROM credentials ORDER BY credential_id").fetchall()
    finally:
        conn.close()
    result = []
    for credential_id, provider_id, refresh_ref, meta_json, created_at in rows:
        if not refresh_ref:
            continue
        meta = json.loads(meta_json)
        # Access-token expires_at is deliberately ignored here. This report
        # concerns renewable authorization, not frequent access token rotations.
        authorization_expiry = parse_utc(meta.get("authorization_expires_at"))
        label = "unknown"
        days_left = None
        if authorization_expiry is not None:
            days_left = round((authorization_expiry - now).total_seconds() / 86400, 1)
            label = "expired" if days_left <= 0 else ("warning" if days_left <= warning_days else "ok")
        result.append({
            "credential_id": credential_id,
            "provider_id": provider_id,
            "created_at": created_at,
            "authorization_expires_at": authorization_expiry.isoformat() if authorization_expiry else None,
            "days_left": days_left,
            "status": label,
        })
    return {"checked_at": now.isoformat(), "warning_days": warning_days, "credentials": result}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    p.add_argument("--warning-days", type=int, default=14)
    a = p.parse_args()
    if not 1 <= a.warning_days <= 90:
        p.error("--warning-days must be 1..90")
    data = inspect(a.db, warning_days=a.warning_days)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(data, indent=2) + "\n")
    a.output.chmod(0o600)
    active = [c for c in data["credentials"] if c["status"] in ("warning", "expired", "unknown")]
    print(f"Credential authorization review: {len(active)} of {len(data['credentials'])} require attention")
    for c in active:
        print(f"{c['credential_id']}: {c['status']}" + (f" ({c['days_left']} days)" if c["days_left"] is not None else " (expiry not published)"))


if __name__ == "__main__":
    main()
