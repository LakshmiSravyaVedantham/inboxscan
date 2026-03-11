from datetime import date, timedelta
from inboxscan.detector import detect_service, classify_status, KNOWN_SERVICES
from inboxscan.models import ParsedEmail, SubscriptionStatus


def test_detect_netflix_by_sender():
    e = ParsedEmail("id1", "billing@netflix.com", "Your Netflix receipt", date.today(), "", 15.99)
    result = detect_service(e)
    assert result is not None
    assert result.service_name == "Netflix"


def test_detect_notion_by_sender():
    e = ParsedEmail("id2", "billing@notion.so", "Notion receipt", date.today(), "", 16.00)
    result = detect_service(e)
    assert result is not None
    assert result.service_name == "Notion"


def test_unknown_service_returns_none():
    e = ParsedEmail("id3", "billing@unknownxyz123.com", "Your receipt", date.today(), "", 9.99)
    result = detect_service(e)
    assert result is None


def test_classify_active_recent():
    status = classify_status(date.today() - timedelta(days=20))
    assert status == SubscriptionStatus.ACTIVE


def test_classify_dormant_old():
    status = classify_status(date.today() - timedelta(days=120))
    assert status == SubscriptionStatus.DORMANT


def test_known_services_has_minimum_entries():
    assert len(KNOWN_SERVICES) >= 20
