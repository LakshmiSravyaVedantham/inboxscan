import pytest
from datetime import date
from inboxscan.models import ParsedEmail, Subscription, SubscriptionStatus


@pytest.fixture
def sample_parsed_email():
    return ParsedEmail(
        message_id="abc123",
        sender="billing@netflix.com",
        subject="Your Netflix receipt",
        date=date(2026, 3, 1),
        body_text="Your monthly subscription of $15.99 has been charged.",
        amount=15.99,
    )


@pytest.fixture
def sample_subscription():
    return Subscription(
        service_name="Netflix",
        amount=15.99,
        currency="USD",
        billing_frequency="monthly",
        last_charge_date=date(2026, 3, 1),
        source_email="personal@gmail.com",
        status=SubscriptionStatus.ACTIVE,
    )
