import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from inboxscan.models import ScanResult, Subscription, SubscriptionStatus

CACHE_PATH = Path.home() / ".inboxscan" / "cache.db"


def _get_conn(path: Path = CACHE_PATH) -> sqlite3.Connection:
    path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            service_name TEXT,
            amount REAL,
            currency TEXT,
            billing_frequency TEXT,
            last_charge_date TEXT,
            source_email TEXT,
            status TEXT,
            cancellation_url TEXT
        )
    """)
    conn.commit()
    return conn


def save_result(result: ScanResult, path: Path = CACHE_PATH) -> None:
    conn = _get_conn(path)
    conn.execute("DELETE FROM subscriptions")
    for sub in result.subscriptions:
        conn.execute(
            "INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?,?)",
            (sub.service_name, sub.amount, sub.currency, sub.billing_frequency,
             sub.last_charge_date.isoformat(), sub.source_email,
             sub.status.value, sub.cancellation_url),
        )
    conn.commit()
    conn.close()


def load_result(path: Path = CACHE_PATH) -> Optional[ScanResult]:
    if not path.exists():
        return None
    conn = _get_conn(path)
    rows = conn.execute("SELECT * FROM subscriptions").fetchall()
    conn.close()
    if not rows:
        return None
    subs = [
        Subscription(
            service_name=r[0], amount=r[1], currency=r[2],
            billing_frequency=r[3],
            last_charge_date=date.fromisoformat(r[4]),
            source_email=r[5], status=SubscriptionStatus(r[6]),
            cancellation_url=r[7],
        )
        for r in rows
    ]
    return ScanResult(subscriptions=subs)
