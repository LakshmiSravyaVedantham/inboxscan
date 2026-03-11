import email
import re
from datetime import date, datetime
from email.message import Message
from typing import Optional

from inboxscan.models import ParsedEmail

SUBSCRIPTION_KEYWORDS = [
    "receipt", "invoice", "billing", "payment confirmed",
    "subscription", "renewal", "charged", "your order",
    "monthly plan", "annual plan", "membership",
]

AMOUNT_PATTERNS = [
    r"\$\s*(\d+\.\d{2})",
    r"USD\s*(\d+\.\d{2})",
    r"(\d+\.\d{2})\s*USD",
    r"amount[:\s]+\$?(\d+\.\d{2})",
    r"charged[:\s]+\$?(\d+\.\d{2})",
    r"total[:\s]+\$?(\d+\.\d{2})",
]


def is_subscription_email(subject: str) -> bool:
    subject_lower = subject.lower()
    return any(kw in subject_lower for kw in SUBSCRIPTION_KEYWORDS)


def parse_amount(text: str) -> Optional[float]:
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def extract_body_text(msg: Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="ignore")
    return body


def parse_raw_email(raw: bytes, message_id: str, source_email: str) -> Optional[ParsedEmail]:
    msg = email.message_from_bytes(raw)
    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    date_str = msg.get("Date", "")

    if not is_subscription_email(subject):
        return None

    try:
        parsed_date = datetime.strptime(date_str[:16].strip(), "%a, %d %b %Y").date()
    except (ValueError, TypeError):
        parsed_date = date.today()

    body = extract_body_text(msg)
    amount = parse_amount(body) or parse_amount(subject)

    return ParsedEmail(
        message_id=message_id,
        sender=sender,
        subject=subject,
        date=parsed_date,
        body_text=body,
        amount=amount,
    )
