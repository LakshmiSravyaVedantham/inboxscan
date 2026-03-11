import imaplib
from typing import Iterator

from inboxscan.models import EmailAccount

SEARCH_SUBJECTS = [
    "receipt", "invoice", "billing", "subscription",
    "renewal", "payment confirmed", "charged",
]


def build_search_query() -> str:
    parts = [f'SUBJECT "{kw}"' for kw in SEARCH_SUBJECTS]
    query = parts[0]
    for part in parts[1:]:
        query = f"OR ({query}) ({part})"
    return query


def _authenticate(imap: imaplib.IMAP4_SSL, account: EmailAccount) -> None:
    if account.access_token:
        from inboxscan.auth import build_xoauth2_string
        auth_string = build_xoauth2_string(account.email, account.access_token)
        imap.authenticate("XOAUTH2", lambda x: auth_string)
    elif account.password:
        imap.login(account.email, account.password)
    else:
        raise ValueError(f"No credentials for {account.email}. Run: inboxscan auth add")


def fetch_emails(account: EmailAccount) -> Iterator[tuple[str, bytes]]:
    with imaplib.IMAP4_SSL(account.imap_host, account.imap_port) as imap:
        _authenticate(imap, account)
        imap.select("INBOX", readonly=True)
        query = build_search_query()
        _, message_numbers = imap.search(None, query)
        if not message_numbers or not message_numbers[0]:
            return
        ids = message_numbers[0].split()
        ids = ids[-500:]
        for msg_id in ids:
            _, data = imap.fetch(msg_id, "(RFC822)")
            if data and data[0]:
                raw = data[0][1]
                if isinstance(raw, bytes):
                    yield msg_id.decode(), raw
