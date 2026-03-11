import json
from pathlib import Path
import pytest
from inboxscan.auth import (
    get_token_path,
    save_token,
    load_token,
    list_accounts,
    remove_account,
)


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
