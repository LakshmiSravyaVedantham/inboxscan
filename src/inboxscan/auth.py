import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from rich.console import Console

logger = logging.getLogger(__name__)

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


def _email_from_id_token(creds: Credentials) -> Optional[str]:
    """Decode the ID token JWT payload to extract the email address.

    The ID token is returned by Google when openid + userinfo.email scopes are
    requested.  Decoding it locally avoids a second network call that can fail
    with HTTP 401 on certain Python versions / environments.
    """
    id_token = creds.id_token
    if not id_token:
        return None
    try:
        # JWT = header.payload.signature — we only need the payload
        payload_b64 = id_token.split(".")[1]
        # Add padding — base64 requires length to be a multiple of 4
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        email = payload.get("email")
        if email and payload.get("email_verified", False):
            return email
        return email  # return even if unverified — caller decides
    except (IndexError, ValueError, json.JSONDecodeError) as exc:
        logger.debug("Could not decode ID token: %s", exc)
        return None


def _email_from_userinfo(creds: Credentials) -> str:
    """Call Google's userinfo endpoint using google-auth's authenticated transport.

    This is the fallback when the ID token is unavailable or missing the email
    claim.  Uses AuthorizedSession (requests-based) instead of raw
    urllib.request so that token refresh, retries, and proper auth headers are
    handled by the library.
    """
    session = AuthorizedSession(creds)
    resp = session.get("https://www.googleapis.com/oauth2/v2/userinfo")
    resp.raise_for_status()
    data = resp.json()
    email = data.get("email")
    if not email:
        raise RuntimeError(
            "Google userinfo response did not contain an email address. "
            "Ensure the 'userinfo.email' scope was granted."
        )
    return email


def add_account() -> str:
    """Run OAuth flow in browser. Returns the authenticated email address."""
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    flow = InstalledAppFlow.from_client_config(_client_config(), SCOPES)
    for port in (8080, 8081, 8082, 9000, 9001):
        try:
            creds = flow.run_local_server(port=port, prompt="consent")
            break
        except OSError:
            continue
    else:
        raise RuntimeError("Could not find a free port for OAuth callback (tried 8080-8082, 9000-9001)")

    # Extract email: prefer local ID token decoding (no network call),
    # fall back to authenticated userinfo request.
    email = _email_from_id_token(creds)
    if not email:
        email = _email_from_userinfo(creds)

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
