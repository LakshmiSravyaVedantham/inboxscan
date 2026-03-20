import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inboxscan.auth import (
    _email_from_id_token,
    _email_from_userinfo,
    add_account,
    get_token_path,
    list_accounts,
    load_token,
    remove_account,
    save_token,
)


# ---------------------------------------------------------------------------
# Helper: build a fake JWT with a given payload
# ---------------------------------------------------------------------------
def _make_jwt(payload: dict) -> str:
    """Build a minimal unsigned JWT (header.payload.signature) for testing."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    sig = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=")
    return f"{header.decode()}.{body.decode()}.{sig.decode()}"


# ---------------------------------------------------------------------------
# Existing token storage tests
# ---------------------------------------------------------------------------
def test_get_token_path_sanitizes_email(tmp_path):
    path = get_token_path("sravya@gmail.com", base=tmp_path)
    assert path == tmp_path / "sravya_gmail_com.json"


def test_save_and_load_token_roundtrip(tmp_path):
    token_data = {"token": "abc123", "refresh_token": "refresh456", "email": "test@gmail.com"}
    save_token("test@gmail.com", token_data, base=tmp_path)
    loaded = load_token("test@gmail.com", base=tmp_path)
    assert loaded == token_data


def test_load_token_missing_returns_none(tmp_path):
    result = load_token("nobody@gmail.com", base=tmp_path)
    assert result is None


def test_list_accounts_returns_emails(tmp_path):
    save_token("a@gmail.com", {"token": "x", "email": "a@gmail.com"}, base=tmp_path)
    save_token("b@gmail.com", {"token": "y", "email": "b@gmail.com"}, base=tmp_path)
    accounts = list_accounts(base=tmp_path)
    assert "a@gmail.com" in accounts
    assert "b@gmail.com" in accounts


def test_remove_account_deletes_token(tmp_path):
    save_token("remove@gmail.com", {"token": "x"}, base=tmp_path)
    remove_account("remove@gmail.com", base=tmp_path)
    assert load_token("remove@gmail.com", base=tmp_path) is None


def test_remove_account_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        remove_account("nobody@gmail.com", base=tmp_path)


# ---------------------------------------------------------------------------
# _email_from_id_token tests
# ---------------------------------------------------------------------------
class TestEmailFromIdToken:
    def test_extracts_verified_email(self):
        creds = MagicMock()
        creds.id_token = _make_jwt({
            "email": "user@gmail.com",
            "email_verified": True,
            "sub": "12345",
        })
        assert _email_from_id_token(creds) == "user@gmail.com"

    def test_extracts_unverified_email(self):
        """Returns email even when email_verified is False."""
        creds = MagicMock()
        creds.id_token = _make_jwt({
            "email": "user@example.com",
            "email_verified": False,
        })
        assert _email_from_id_token(creds) == "user@example.com"

    def test_returns_none_when_no_id_token(self):
        creds = MagicMock()
        creds.id_token = None
        assert _email_from_id_token(creds) is None

    def test_returns_none_when_empty_id_token(self):
        creds = MagicMock()
        creds.id_token = ""
        assert _email_from_id_token(creds) is None

    def test_returns_none_when_no_email_claim(self):
        creds = MagicMock()
        creds.id_token = _make_jwt({"sub": "12345"})
        assert _email_from_id_token(creds) is None

    def test_returns_none_on_malformed_jwt(self):
        creds = MagicMock()
        creds.id_token = "not-a-jwt"
        assert _email_from_id_token(creds) is None

    def test_returns_none_on_invalid_base64(self):
        creds = MagicMock()
        creds.id_token = "header.!!!invalid!!!.sig"
        assert _email_from_id_token(creds) is None

    def test_handles_padded_and_unpadded_base64(self):
        """JWT base64 often omits padding — verify we handle both."""
        payload = {"email": "padtest@gmail.com", "email_verified": True}
        # Make a JWT with standard (padded) base64
        body_padded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        body_unpadded = body_padded.rstrip("=")
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()

        for body in (body_padded, body_unpadded):
            creds = MagicMock()
            creds.id_token = f"{header}.{body}.fakesig"
            assert _email_from_id_token(creds) == "padtest@gmail.com"


# ---------------------------------------------------------------------------
# _email_from_userinfo tests
# ---------------------------------------------------------------------------
class TestEmailFromUserinfo:
    @patch("inboxscan.auth.AuthorizedSession")
    def test_returns_email_on_success(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"email": "user@gmail.com", "verified_email": True}
        mock_resp.raise_for_status = MagicMock()
        mock_session_cls.return_value.get.return_value = mock_resp

        creds = MagicMock()
        assert _email_from_userinfo(creds) == "user@gmail.com"
        mock_session_cls.return_value.get.assert_called_once_with(
            "https://www.googleapis.com/oauth2/v2/userinfo"
        )

    @patch("inboxscan.auth.AuthorizedSession")
    def test_raises_on_http_error(self, mock_session_cls):
        from requests.exceptions import HTTPError

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_session_cls.return_value.get.return_value = mock_resp

        creds = MagicMock()
        with pytest.raises(HTTPError):
            _email_from_userinfo(creds)

    @patch("inboxscan.auth.AuthorizedSession")
    def test_raises_on_missing_email(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "12345"}  # no email field
        mock_resp.raise_for_status = MagicMock()
        mock_session_cls.return_value.get.return_value = mock_resp

        creds = MagicMock()
        with pytest.raises(RuntimeError, match="did not contain an email"):
            _email_from_userinfo(creds)


# ---------------------------------------------------------------------------
# add_account integration tests (OAuth flow mocked)
# ---------------------------------------------------------------------------
class TestAddAccount:
    @patch("inboxscan.auth.save_token")
    @patch("inboxscan.auth.InstalledAppFlow")
    def test_uses_id_token_when_available(self, mock_flow_cls, mock_save, tmp_path):
        """Primary path: email extracted from ID token, no userinfo call."""
        mock_creds = MagicMock()
        mock_creds.token = "access-token-123"
        mock_creds.refresh_token = "refresh-456"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "test-client-id"
        mock_creds.client_secret = "test-client-secret"
        mock_creds.scopes = {"openid", "email"}
        mock_creds.id_token = _make_jwt({
            "email": "user@gmail.com",
            "email_verified": True,
        })

        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_config.return_value = mock_flow

        with patch.dict("os.environ", {
            "INBOXSCAN_CLIENT_ID": "fake-id",
            "INBOXSCAN_CLIENT_SECRET": "fake-secret",
        }):
            result = add_account()

        assert result == "user@gmail.com"
        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][1]
        assert saved_data["email"] == "user@gmail.com"
        assert saved_data["token"] == "access-token-123"

    @patch("inboxscan.auth.AuthorizedSession")
    @patch("inboxscan.auth.save_token")
    @patch("inboxscan.auth.InstalledAppFlow")
    def test_falls_back_to_userinfo_when_no_id_token(
        self, mock_flow_cls, mock_save, mock_session_cls
    ):
        """Fallback path: no ID token, calls userinfo endpoint."""
        mock_creds = MagicMock()
        mock_creds.token = "access-token-789"
        mock_creds.refresh_token = "refresh-012"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "test-client-id"
        mock_creds.client_secret = "test-client-secret"
        mock_creds.scopes = {"openid", "email"}
        mock_creds.id_token = None  # no ID token

        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_config.return_value = mock_flow

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"email": "fallback@gmail.com"}
        mock_resp.raise_for_status = MagicMock()
        mock_session_cls.return_value.get.return_value = mock_resp

        with patch.dict("os.environ", {
            "INBOXSCAN_CLIENT_ID": "fake-id",
            "INBOXSCAN_CLIENT_SECRET": "fake-secret",
        }):
            result = add_account()

        assert result == "fallback@gmail.com"
        mock_session_cls.return_value.get.assert_called_once()

    @patch("inboxscan.auth.InstalledAppFlow")
    def test_tries_multiple_ports(self, mock_flow_cls):
        """Retries on OSError (port in use) until a port works."""
        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = [
            OSError("port 8080 in use"),
            OSError("port 8081 in use"),
            MagicMock(
                token="tok",
                refresh_token="ref",
                token_uri="uri",
                client_id="cid",
                client_secret="csec",
                scopes={"openid"},
                id_token=_make_jwt({"email": "retry@gmail.com", "email_verified": True}),
            ),
        ]
        mock_flow_cls.from_client_config.return_value = mock_flow

        with patch.dict("os.environ", {
            "INBOXSCAN_CLIENT_ID": "fake-id",
            "INBOXSCAN_CLIENT_SECRET": "fake-secret",
        }), patch("inboxscan.auth.save_token"):
            result = add_account()
            assert result == "retry@gmail.com"
            assert mock_flow.run_local_server.call_count == 3

    @patch("inboxscan.auth.InstalledAppFlow")
    def test_raises_when_all_ports_taken(self, mock_flow_cls):
        """Raises RuntimeError when every port attempt fails."""
        mock_flow = MagicMock()
        mock_flow.run_local_server.side_effect = OSError("port in use")
        mock_flow_cls.from_client_config.return_value = mock_flow

        with patch.dict("os.environ", {
            "INBOXSCAN_CLIENT_ID": "fake-id",
            "INBOXSCAN_CLIENT_SECRET": "fake-secret",
        }):
            with pytest.raises(RuntimeError, match="Could not find a free port"):
                add_account()
