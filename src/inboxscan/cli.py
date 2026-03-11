import typer
from typing import Optional
from rich.console import Console
from inboxscan import __version__

app = typer.Typer(help="Find every subscription hiding in your email.")
console = Console()


@app.command()
def run(
    email: list[str] = typer.Option(..., "--email", "-e", help="Email address to scan (repeat for multiple)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Gmail app password (prompted if not provided)"),
):
    """Scan your email for active subscriptions."""
    from inboxscan.models import EmailAccount, ScanResult
    from inboxscan.connector import fetch_emails
    from inboxscan.parser import parse_raw_email
    from inboxscan.detector import detect_service
    from inboxscan.reporter import print_report
    from inboxscan.cache import save_result

    all_subscriptions = []
    seen_services: set[str] = set()

    for email_addr in email:
        pw = password or typer.prompt(f"Gmail app password for {email_addr}", hide_input=True)
        account = EmailAccount(email=email_addr, password=pw)
        console.print(f"\n[dim]Scanning {email_addr}...[/dim]")

        for msg_id, raw in fetch_emails(account):
            parsed = parse_raw_email(raw, msg_id, email_addr)
            if parsed is None:
                continue
            sub = detect_service(parsed)
            if sub is None:
                continue
            key = f"{sub.service_name}:{email_addr}"
            if key in seen_services:
                continue
            seen_services.add(key)
            sub.source_email = email_addr
            all_subscriptions.append(sub)

    result = ScanResult(
        accounts_scanned=email,
        subscriptions=all_subscriptions,
    )
    save_result(result)
    print_report(result)


@app.command()
def cancel(service: str = typer.Argument(..., help="Service name (e.g. netflix, spotify)")):
    """Print cancellation instructions for a service."""
    from inboxscan.canceller import cancel_service
    cancel_service(service)


@app.command()
def version():
    """Print the current version."""
    console.print(f"inboxscan {__version__}")


if __name__ == "__main__":
    app()
