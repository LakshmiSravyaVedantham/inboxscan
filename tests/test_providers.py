# tests/test_providers.py
import pytest
from unittest.mock import patch
from inboxscan.providers import detect_provider, IMAP_PROVIDERS  # noqa: F401


def test_gmail_detected():
    host, port = detect_provider("me@gmail.com", interactive=False)
    assert host == "imap.gmail.com"
    assert port == 993


def test_googlemail_detected():
    host, port = detect_provider("me@googlemail.com", interactive=False)
    assert host == "imap.gmail.com"
    assert port == 993


def test_outlook_detected():
    host, port = detect_provider("me@outlook.com", interactive=False)
    assert host == "imap.outlook.com"
    assert port == 993


def test_hotmail_detected():
    host, port = detect_provider("me@hotmail.com", interactive=False)
    assert host == "imap.outlook.com"
    assert port == 993


def test_yahoo_detected():
    host, port = detect_provider("me@yahoo.com", interactive=False)
    assert host == "imap.mail.yahoo.com"
    assert port == 993


def test_icloud_detected():
    host, port = detect_provider("me@icloud.com", interactive=False)
    assert host == "imap.mail.me.com"
    assert port == 993


def test_fastmail_detected():
    host, port = detect_provider("me@fastmail.com", interactive=False)
    assert host == "imap.fastmail.com"
    assert port == 993


def test_protonmail_detected():
    host, port = detect_provider("me@protonmail.com", interactive=False)
    assert host == "127.0.0.1"
    assert port == 1143


def test_proton_me_detected():
    host, port = detect_provider("me@proton.me", interactive=False)
    assert host == "127.0.0.1"
    assert port == 1143


def test_unknown_domain_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        detect_provider("me@mycompany.com", interactive=False)


def test_explicit_host_override():
    host, port = detect_provider("me@anything.com", interactive=False, imap_host="custom.host.com")
    assert host == "custom.host.com"
    assert port == 993


def test_explicit_host_and_port_override():
    host, port = detect_provider("me@anything.com", interactive=False, imap_host="custom.host.com", imap_port=143)
    assert host == "custom.host.com"
    assert port == 143


def test_me_com_detected():
    host, port = detect_provider("me@me.com", interactive=False)
    assert host == "imap.mail.me.com"
    assert port == 993


def test_mac_com_detected():
    host, port = detect_provider("me@mac.com", interactive=False)
    assert host == "imap.mail.me.com"
    assert port == 993


def test_live_com_detected():
    host, port = detect_provider("me@live.com", interactive=False)
    assert host == "imap.outlook.com"
    assert port == 993


def test_zoho_com_detected():
    host, port = detect_provider("me@zoho.com", interactive=False)
    assert host == "imap.zoho.com"
    assert port == 993


def test_aol_com_detected():
    host, port = detect_provider("me@aol.com", interactive=False)
    assert host == "imap.aol.com"
    assert port == 993


def test_custom_provider_from_config():
    with patch(
        "inboxscan.providers._load_custom_providers",
        return_value={"customco.com": ("imap.customco.com", 993)}
    ):
        host, port = detect_provider("me@customco.com", interactive=False)
        assert host == "imap.customco.com"
        assert port == 993


def test_invalid_email_no_at_sign():
    with pytest.raises(ValueError, match="Invalid email"):
        detect_provider("notanemail", interactive=False)


def test_empty_string_host_falls_through_to_domain_lookup():
    # Empty string imap_host should NOT override — falls through to domain detection
    host, port = detect_provider("me@gmail.com", interactive=False, imap_host=None)
    assert host == "imap.gmail.com"


def test_interactive_path_saves_and_returns(tmp_path, monkeypatch):
    import inboxscan.providers as p
    monkeypatch.setattr(p, "_CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr("builtins.input", lambda prompt: "mail.corp.com" if "host" in prompt.lower() else "")
    host, port = detect_provider("me@corp.com", interactive=True)
    assert host == "mail.corp.com"
    assert port == 993
    # Verify it was saved
    assert (tmp_path / "config.json").exists()


def test_interactive_bad_port_falls_back_to_993(tmp_path, monkeypatch):
    import inboxscan.providers as p
    monkeypatch.setattr(p, "_CONFIG_PATH", tmp_path / "config.json")
    responses = iter(["mail.corp.com", "notaport"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))
    host, port = detect_provider("me@corp2.com", interactive=True)
    assert host == "mail.corp.com"
    assert port == 993
