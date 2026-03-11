from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    UNKNOWN = "UNKNOWN"


@dataclass
class EmailAccount:
    email: str
    password: Optional[str] = None       # kept for backwards compat
    access_token: Optional[str] = None   # used for OAuth
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993


@dataclass
class ParsedEmail:
    message_id: str
    sender: str
    subject: str
    date: date
    body_text: str
    amount: Optional[float] = None
    currency: str = "USD"


@dataclass
class Subscription:
    service_name: str
    amount: float
    currency: str
    billing_frequency: str  # "monthly", "annual", "unknown"
    last_charge_date: date
    source_email: str  # which account found this
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    cancellation_url: Optional[str] = None


@dataclass
class ScanResult:
    accounts_scanned: list[str] = field(default_factory=list)
    subscriptions: list[Subscription] = field(default_factory=list)
    unknown_charges: int = 0

    @property
    def total_monthly_burn(self) -> float:
        total = 0.0
        for sub in self.subscriptions:
            if sub.status == SubscriptionStatus.ACTIVE:
                if sub.billing_frequency == "annual":
                    total += sub.amount / 12
                else:
                    total += sub.amount
        return round(total, 2)

    @property
    def dormant_monthly_waste(self) -> float:
        total = 0.0
        for sub in self.subscriptions:
            if sub.status == SubscriptionStatus.DORMANT:
                if sub.billing_frequency == "annual":
                    total += sub.amount / 12
                else:
                    total += sub.amount
        return round(total, 2)
