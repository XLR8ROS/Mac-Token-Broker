from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.xlr8ros.token-broker"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def launch_agent_payload() -> dict:
    package_root = Path(__file__).resolve().parent.parent
    logs = Path.home() / "Library" / "Logs"
    return {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, "-m", "mac_token_broker.cli", "serve"],
        "RunAtLoad": True,
        "KeepAlive": {"SuccessfulExit": False},
        "ProcessType": "Background",
        "StandardOutPath": str(logs / "token-broker.out.log"),
        "StandardErrorPath": str(logs / "token-broker.err.log"),
        "EnvironmentVariables": {
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": str(package_root),
        },
    }


def install() -> Path:
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.chmod(0o700)
    logs = Path.home() / "Library" / "Logs"
    logs.mkdir(parents=True, exist_ok=True)
    with PLIST_PATH.open("wb") as fh:
        plistlib.dump(launch_agent_payload(), fh)
    PLIST_PATH.chmod(0o600)

    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST_PATH)], capture_output=True)
    proc = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "launchctl bootstrap failed")
    subprocess.run(["launchctl", "enable", f"gui/{uid}/{LABEL}"], check=True)
    subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{LABEL}"], check=True)
    return PLIST_PATH


def uninstall() -> None:
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST_PATH)], capture_output=True)
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
