"""
inboxscan menu bar app for macOS.

Usage:
    pip install "inboxscan[menubar]"
    inboxscan-menubar

Shows your subscription burn rate in the menu bar. Loads cached results on
startup. "Scan Now" re-scans using stored OAuth tokens (run
`inboxscan auth add` first).

Everything runs locally — no data leaves your machine.
"""
import subprocess
import threading
from typing import Optional

import rumps

from inboxscan.cache import load_result, save_result
from inboxscan.models import ScanResult, Subscription, SubscriptionStatus


def _run_scan_background() -> Optional[ScanResult]:
    """Run a full scan using stored OAuth tokens. Returns None on error."""
    try:
        from inboxscan.auth import list_accounts, get_access_token
        from inboxscan.connector import fetch_emails
        from inboxscan.parser import parse_raw_email
        from inboxscan.detector import detect_from_batch
        from inboxscan.models import EmailAccount, ScanResult

        accounts = list_accounts()
        if not accounts:
            return None

        all_subscriptions = []
        seen_services: set[str] = set()

        for email_addr in accounts:
            try:
                access_token = get_access_token(email_addr)
                account = EmailAccount(email=email_addr, access_token=access_token)
            except ValueError:
                continue

            parsed_emails = []
            for msg_id, raw in fetch_emails(account):
                parsed = parse_raw_email(raw, msg_id, email_addr)
                if parsed is not None:
                    parsed_emails.append(parsed)

            for sub in detect_from_batch(parsed_emails):
                key = f"{sub.service_name}:{email_addr}"
                if key in seen_services:
                    continue
                seen_services.add(key)
                sub.source_email = email_addr
                all_subscriptions.append(sub)

        result = ScanResult(
            accounts_scanned=accounts,
            subscriptions=all_subscriptions,
        )
        save_result(result)
        return result

    except Exception:
        return None


class InboxScanApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("inboxscan", title="💳 —")
        self._result: Optional[ScanResult] = None
        self._scanning = False
        self._load_cached()

    def _load_cached(self) -> None:
        result = load_result()
        if result:
            self._result = result
            self._rebuild_menu()
        else:
            self.title = "💳 —"
            self.menu.clear()
            self.menu = [
                rumps.MenuItem("No scan data yet"),
                None,
                rumps.MenuItem("Scan Now", callback=self._on_scan),
                None,
            ]

    def _remove_subscription(self, sub: Subscription) -> None:
        """Remove a subscription from cache and rebuild the menu."""
        if self._result is None:
            return
        self._result.subscriptions = [
            s for s in self._result.subscriptions
            if not (s.service_name == sub.service_name and s.source_email == sub.source_email)
        ]
        save_result(self._result)
        self._rebuild_menu()

    def _rebuild_menu(self, scanning: bool = False) -> None:
        result = self._result
        if result is None:
            return

        burn = result.total_monthly_burn
        waste = result.dormant_monthly_waste

        self.title = "💳 …" if scanning else f"💳 ${burn:.0f}/mo"

        active = [s for s in result.subscriptions if s.status == SubscriptionStatus.ACTIVE]
        dormant = [s for s in result.subscriptions if s.status == SubscriptionStatus.DORMANT]

        menu_items = []

        if active:
            menu_items.append(rumps.MenuItem("── ACTIVE ──"))
            for sub in sorted(active, key=lambda s: -s.amount):
                label = f"  {sub.service_name:<22} ${sub.amount:.2f}/{sub.billing_frequency[:2]}"
                parent = rumps.MenuItem(label)
                parent.add(rumps.MenuItem(f"  {sub.source_email}"))
                if sub.cancellation_url:
                    url = sub.cancellation_url
                    cancel_item = rumps.MenuItem(
                        "Open cancellation page",
                        callback=lambda _, u=url: subprocess.run(["open", u])
                    )
                    parent.add(cancel_item)
                remove_item = rumps.MenuItem(
                    "Remove from list",
                    callback=lambda _, s=sub: self._remove_subscription(s)
                )
                parent.add(remove_item)
                menu_items.append(parent)

        if dormant:
            menu_items.append(None)
            dormant_parent = rumps.MenuItem(f"Dormant  (${waste:.0f}/mo wasted) ▶")
            for sub in sorted(dormant, key=lambda s: -s.amount):
                label = f"  {sub.service_name:<22} ${sub.amount:.2f}/{sub.billing_frequency[:2]}"
                item = rumps.MenuItem(label)
                item.add(rumps.MenuItem(f"  {sub.source_email}"))
                if sub.cancellation_url:
                    url = sub.cancellation_url
                    item.add(rumps.MenuItem(
                        "Open cancellation page",
                        callback=lambda _, u=url: subprocess.run(["open", u])
                    ))
                item.add(rumps.MenuItem(
                    "Remove from list",
                    callback=lambda _, s=sub: self._remove_subscription(s)
                ))
                dormant_parent.add(item)
            menu_items.append(dormant_parent)

        menu_items.append(None)
        menu_items.append(rumps.MenuItem(f"Total active: ${burn:.2f}/mo"))
        menu_items.append(None)

        scan_label = "Scanning…" if scanning else "Scan Now"
        scan_item = rumps.MenuItem(scan_label, callback=None if scanning else self._on_scan)
        menu_items.append(scan_item)

        if result.accounts_scanned:
            accts = ", ".join(result.accounts_scanned)
            menu_items.append(rumps.MenuItem(f"Accounts: {accts}"))

        menu_items.append(None)

        self.menu.clear()
        self.menu = menu_items

    def _on_scan(self, _: rumps.MenuItem) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._rebuild_menu(scanning=True)

        def _worker() -> None:
            result = _run_scan_background()
            if result is not None:
                self._result = result
            self._scanning = False
            self._rebuild_menu(scanning=False)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()


def main() -> None:
    app = InboxScanApp()
    app.run()


if __name__ == "__main__":
    main()
