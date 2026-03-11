# tests/test_providers.py
import pytest
from inboxscan.providers import detect_provider, IMAP_PROVIDERS


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
