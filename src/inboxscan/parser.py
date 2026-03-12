import email
import re
from datetime import date, datetime
from email.message import Message
from typing import Optional

from inboxscan.models import ParsedEmail

DATE_FORMATS = [
    "%B %d, %Y",   # January 15, 2026
    "%b %d, %Y",   # Jan 15, 2026
    "%B %d %Y",    # January 15 2026
    "%b %d %Y",    # Jan 15 2026
    "%d %B %Y",    # 15 January 2026
    "%d %b %Y",    # 15 Jan 2026
    "%m/%d/%Y",    # 01/15/2026
    "%Y-%m-%d",    # 2026-01-15
    "%B %d",       # January 15 (no year — assume current/next year)
    "%b %d",       # Jan 15
]

TRIAL_END_PATTERNS = [
    r"(?:free )?trial (?:ends?|expires?)(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"trial period ends(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"your trial (?:ends?|expires?)(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
]

RENEWAL_DATE_PATTERNS = [
    r"(?:next )?(?:billing|renewal) date[:\s]+([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"renews?(?: automatically)?(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"next (?:charge|payment)[:\s]+([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"you(?:'ll| will) be charged(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"subscription renews(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
]

CANCELLATION_DATE_PATTERNS = [
    r"(?:your )?(?:subscription|membership|plan) (?:was |has been )?cancelled(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"cancell?ation (?:effective |date[:\s]+)([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"access (?:ends?|expires?)(?: on)? ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
    r"you(?:'ll| will) (?:lose|have) access until ([A-Za-z0-9, /\-]+?)(?:\.|,|\s{2,}|$)",
]

CANCELLATION_KEYWORDS = [
    "cancellation confirmed", "subscription cancelled", "subscription canceled",
    "you've cancelled", "you have cancelled", "membership cancelled",
    "we've cancelled", "successfully cancelled", "successfully canceled",
]


def _try_parse_date(text: str) -> Optional[date]:
    text = text.strip().rstrip(".,")
    today = date.today()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.year == 1900:
                # No year in format — pick current or next year
                parsed = parsed.replace(year=today.year)
                if parsed.date() < today:
                    parsed = parsed.replace(year=today.year + 1)
            return parsed.date()
        except ValueError:
            continue
    return None


def _extract_date_from_patterns(text: str, patterns: list[str]) -> Optional[date]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = _try_parse_date(match.group(1))
            if candidate:
                return candidate
    return None


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

    full_text = f"{subject}\n{body}"
    trial_end_date = _extract_date_from_patterns(full_text, TRIAL_END_PATTERNS)
    next_renewal_date = _extract_date_from_patterns(full_text, RENEWAL_DATE_PATTERNS)

    cancellation_date = None
    subject_lower = subject.lower()
    if any(kw in subject_lower or kw in body.lower() for kw in CANCELLATION_KEYWORDS):
        cancellation_date = _extract_date_from_patterns(full_text, CANCELLATION_DATE_PATTERNS) or parsed_date

    return ParsedEmail(
        message_id=message_id,
        sender=sender,
        subject=subject,
        date=parsed_date,
        body_text=body,
        amount=amount,
        trial_end_date=trial_end_date,
        next_renewal_date=next_renewal_date,
        cancellation_date=cancellation_date,
    )
