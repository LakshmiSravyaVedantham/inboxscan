from datetime import date
from inboxscan.models import ScanResult, Subscription, SubscriptionStatus


def test_total_monthly_burn_active_only():
    result = ScanResult(
        accounts_scanned=["test@gmail.com"],
        subscriptions=[
            Subscription("Netflix", 15.99, "USD", "monthly", date.today(), "test@gmail.com", SubscriptionStatus.ACTIVE),
            Subscription("Adobe", 54.99, "USD", "monthly", date.today(), "test@gmail.com", SubscriptionStatus.ACTIVE),
        ],
    )
    assert result.total_monthly_burn == 70.98


def test_annual_subscription_divided_by_12():
    result = ScanResult(
        accounts_scanned=["test@gmail.com"],
        subscriptions=[
            Subscription("GitHub", 48.00, "USD", "annual", date.today(), "test@gmail.com", SubscriptionStatus.ACTIVE),
        ],
    )
    assert result.total_monthly_burn == 4.0


def test_dormant_not_counted_in_active_burn():
    result = ScanResult(
        accounts_scanned=["test@gmail.com"],
        subscriptions=[
            Subscription("Netflix", 15.99, "USD", "monthly", date.today(), "test@gmail.com", SubscriptionStatus.ACTIVE),
            Subscription("Audible", 14.95, "USD", "monthly", date.today(), "test@gmail.com", SubscriptionStatus.DORMANT),
        ],
    )
    assert result.total_monthly_burn == 15.99
    assert result.dormant_monthly_waste == 14.95
