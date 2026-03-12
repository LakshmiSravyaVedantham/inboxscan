import json
import os
import re
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from rich.console import Console

console = Console()

TOKEN_DIR = Path.home() / ".inboxscan" / "tokens"

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _client_config() -> dict:
    client_id = os.environ.get("INBOXSCAN_CLIENT_ID")
    client_secret = os.environ.get("INBOXSCAN_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError(
            "OAuth credentials not configured. "
            "Set INBOXSCAN_CLIENT_ID and INBOXSCAN_CLIENT_SECRET environment variables."
        )
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def _sanitize(email: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", email)


def get_token_path(email: str, base: Optional[Path] = None) -> Path:
    directory = base if base is not None else TOKEN_DIR
    return directory / f"{_sanitize(email)}.json"


def save_token(email: str, token_data: dict, base: Optional[Path] = None) -> None:
    directory = base if base is not None else TOKEN_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = get_token_path(email, base=directory)
    path.write_text(json.dumps(token_data))


def load_token(email: str, base: Optional[Path] = None) -> Optional[dict]:
    path = get_token_path(email, base=base)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_accounts(base: Optional[Path] = None) -> list[str]:
    directory = base if base is not None else TOKEN_DIR
    if not directory.exists():
        return []
    emails = []
    for f in directory.glob("*.json"):
        data = json.loads(f.read_text())
        if "email" in data:
            emails.append(data["email"])
    return emails


def remove_account(email: str, base: Optional[Path] = None) -> None:
    path = get_token_path(email, base=base)
    if not path.exists():
        raise FileNotFoundError(f"No token found for {email}")
    path.unlink()


def add_account() -> str:
    """Run OAuth flow in browser. Returns the authenticated email address."""
    flow = InstalledAppFlow.from_client_config(_client_config(), SCOPES)
    for port in (8080, 8081, 8082, 9000, 9001):
        try:
            creds = flow.run_local_server(port=port, prompt="consent")
            break
        except OSError:
            continue
    else:
        raise RuntimeError("Could not find a free port for OAuth callback (tried 8080-8082, 9000-9001)")

    import urllib.request
    req = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
    )
    with urllib.request.urlopen(req) as response:
        user_info = json.loads(response.read())
    email = user_info["email"]

    token_data = {
        "email": email,
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    save_token(email, token_data)
    return email


def get_access_token(email: str) -> str:
    """Load stored token, refresh if expired, return valid access token."""
    data = load_token(email)
    if data is None:
        raise ValueError(f"No token for {email}. Run: inboxscan auth add")

    creds = Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", SCOPES),
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data["token"] = creds.token
        save_token(email, data)

    return creds.token


def build_xoauth2_string(email: str, access_token: str) -> bytes:
    """Return raw XOAUTH2 bytes — imaplib.authenticate base64-encodes internally."""
    auth_string = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
    return auth_string.encode()
