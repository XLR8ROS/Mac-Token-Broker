"""Mac-only Google consent and direct Keychain provisioning via Token Broker.

Run with the Stenographer venv Python and PYTHONPATH=src. No tokens are printed,
written to local files, passed on argv, or placed in shell history.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from mac_token_broker.runtime import build_broker

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
]

def main():
    parser = argparse.ArgumentParser(description='Authorize Google for XOS Mac Token Broker')
    parser.add_argument('--client-json', type=Path, required=True,
                        help='Google OAuth Desktop client JSON (stored locally on Mac)')
    parser.add_argument('--credential-id', default='google-stenographer')
    parser.add_argument('--service-id', default='stenographer')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not args.client_json.is_file():
        parser.error('Google OAuth desktop client JSON is absent on this Mac')
    broker = build_broker()
    broker.storage.get_service(args.service_id)
    if any(c.credential_id == args.credential_id for c in broker.storage.list_credentials()):
        parser.error('Credential ID already exists; refusing to overwrite')
    client_data = json.loads(args.client_json.read_text())["installed"]
    flow = InstalledAppFlow.from_client_secrets_file(str(args.client_json), scopes=SCOPES)
    print('Complete Google consent in the Mac browser. Tokens will be stored directly in macOS Keychain.')
    flow.run_local_server(host='127.0.0.1', port=args.port, open_browser=True,
                          access_type='offline', prompt='consent')
    creds = flow.credentials
    if not creds.token or not creds.refresh_token:
        raise RuntimeError('Google did not grant both access and offline refresh tokens; nothing saved')
    secret_ref = f"google-client-secret:{args.credential_id}"
    client_secret = client_data.get("client_secret")
    metadata = {"client_id": creds.client_id}
    if client_secret:
        broker.secrets.put(secret_ref, client_secret)
        metadata["client_secret_ref"] = secret_ref
    broker.add_credential(args.credential_id, 'google', creds.token,
                          refresh_secret=creds.refresh_token,
                          expires_at=creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None,
                          metadata=metadata)
    broker.assign(args.service_id, args.credential_id)
    print('Google credential stored in Mac Keychain and assigned to service:', args.service_id)

if __name__ == '__main__':
    main()
