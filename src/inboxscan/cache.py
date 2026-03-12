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
            cancellation_url TEXT,
            start_date TEXT,
            next_renewal_date TEXT,
            trial_end_date TEXT,
            cancellation_date TEXT
        )
    """)
    # Migrate existing databases that are missing the new columns
    existing = {row[1] for row in conn.execute("PRAGMA table_info(subscriptions)")}
    for col in ("start_date", "next_renewal_date", "trial_end_date", "cancellation_date"):
        if col not in existing:
            conn.execute(f"ALTER TABLE subscriptions ADD COLUMN {col} TEXT")
    conn.commit()
    return conn


def _d(val: Optional[str]) -> Optional[date]:
    return date.fromisoformat(val) if val else None


def save_result(result: ScanResult, path: Path = CACHE_PATH) -> None:
    conn = _get_conn(path)
    conn.execute("DELETE FROM subscriptions")
    for sub in result.subscriptions:
        conn.execute(
            "INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (sub.service_name, sub.amount, sub.currency, sub.billing_frequency,
             sub.last_charge_date.isoformat(), sub.source_email,
             sub.status.value, sub.cancellation_url,
             sub.start_date.isoformat() if sub.start_date else None,
             sub.next_renewal_date.isoformat() if sub.next_renewal_date else None,
             sub.trial_end_date.isoformat() if sub.trial_end_date else None,
             sub.cancellation_date.isoformat() if sub.cancellation_date else None),
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
            start_date=_d(r[8] if len(r) > 8 else None),
            next_renewal_date=_d(r[9] if len(r) > 9 else None),
            trial_end_date=_d(r[10] if len(r) > 10 else None),
            cancellation_date=_d(r[11] if len(r) > 11 else None),
        )
        for r in rows
    ]
    return ScanResult(subscriptions=subs)
