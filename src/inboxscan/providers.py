import json
from pathlib import Path
from typing import Optional

IMAP_PROVIDERS: dict[str, tuple[str, int]] = {
    "gmail.com":       ("imap.gmail.com", 993),
    "googlemail.com":  ("imap.gmail.com", 993),
    "outlook.com":     ("imap.outlook.com", 993),
    "hotmail.com":     ("imap.outlook.com", 993),
    "live.com":        ("imap.outlook.com", 993),
    "msn.com":         ("imap.outlook.com", 993),
    "yahoo.com":       ("imap.mail.yahoo.com", 993),
    "yahoo.co.uk":     ("imap.mail.yahoo.com", 993),
    "ymail.com":       ("imap.mail.yahoo.com", 993),
    "icloud.com":      ("imap.mail.me.com", 993),
    "me.com":          ("imap.mail.me.com", 993),
    "mac.com":         ("imap.mail.me.com", 993),
    "fastmail.com":    ("imap.fastmail.com", 993),
    "fastmail.fm":     ("imap.fastmail.com", 993),
    "zoho.com":        ("imap.zoho.com", 993),
    "aol.com":         ("imap.aol.com", 993),
    "protonmail.com":  ("127.0.0.1", 1143),
    "proton.me":       ("127.0.0.1", 1143),
}

_CONFIG_PATH = Path.home() / ".inboxscan" / "config.json"


def _load_custom_providers() -> dict[str, tuple[str, int]]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(_CONFIG_PATH.read_text())
        result = {}
        for domain, cfg in data.get("custom_providers", {}).items():
            result[domain] = (cfg["host"], int(cfg["port"]))
        return result
    except Exception:
        return {}


def _save_custom_provider(domain: str, host: str, port: int) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text())
        except Exception:
            pass
    data.setdefault("custom_providers", {})[domain] = {"host": host, "port": port}
    _CONFIG_PATH.write_text(json.dumps(data, indent=2))


def detect_provider(
    email: str,
    interactive: bool = True,
    imap_host: Optional[str] = None,
    imap_port: Optional[int] = None,
) -> tuple[str, int]:
    """Return (imap_host, imap_port) for the given email address.

    Priority:
    1. Explicit override (imap_host / imap_port args)
    2. Built-in provider table
    3. User-saved custom providers (~/.inboxscan/config.json)
    4. Interactive prompt (if interactive=True)
    5. Raise ValueError (if interactive=False)
    """
    if imap_host:
        return (imap_host, imap_port or 993)

    domain = email.split("@")[-1].lower()

    if domain in IMAP_PROVIDERS:
        return IMAP_PROVIDERS[domain]

    custom = _load_custom_providers()
    if domain in custom:
        return custom[domain]

    if not interactive:
        raise ValueError(f"Unknown provider for {domain}")

    if "proton" in domain:
        print("ProtonMail requires Bridge to be running: proton.me/mail/bridge")

    print(f"Unknown provider for {domain}")
    host = input("IMAP host (e.g. mail.mycompany.com): ").strip()
    port_str = input("IMAP port [993]: ").strip()
    port = int(port_str) if port_str else 993

    _save_custom_provider(domain, host, port)
    print("Saved to ~/.inboxscan/config.json — won't ask again.")

    return (host, port)
