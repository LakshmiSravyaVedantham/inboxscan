from datetime import date
from pathlib import Path
from inboxscan.cache import save_result, load_result
from inboxscan.models import ScanResult, Subscription, SubscriptionStatus


def test_save_and_load_roundtrip(tmp_path):
    db_path = tmp_path / "cache.db"
    sub = Subscription("Netflix", 15.99, "USD", "monthly", date(2026, 3, 1), "test@gmail.com", SubscriptionStatus.ACTIVE)
    result = ScanResult(accounts_scanned=["test@gmail.com"], subscriptions=[sub])
    save_result(result, path=db_path)
    loaded = load_result(path=db_path)
    assert loaded is not None
    assert len(loaded.subscriptions) == 1
    assert loaded.subscriptions[0].service_name == "Netflix"
    assert loaded.subscriptions[0].amount == 15.99


def test_load_result_missing_file(tmp_path):
    result = load_result(path=tmp_path / "nonexistent.db")
    assert result is None
