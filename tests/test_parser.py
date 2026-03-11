from datetime import date
from inboxscan.parser import parse_amount, is_subscription_email


def test_parse_amount_dollar_sign():
    assert parse_amount("Your charge of $15.99 has been processed") == 15.99


def test_parse_amount_usd_format():
    assert parse_amount("Amount: USD 54.99") == 54.99


def test_parse_amount_no_amount():
    assert parse_amount("Welcome to our newsletter") is None


def test_is_subscription_email_receipt():
    assert is_subscription_email("Your Netflix receipt for March") is True


def test_is_subscription_email_renewal():
    assert is_subscription_email("Your subscription has been renewed") is True


def test_is_subscription_email_negative():
    assert is_subscription_email("Your friend sent you a message") is False
