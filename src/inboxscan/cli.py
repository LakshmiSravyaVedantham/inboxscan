import typer
from rich.console import Console
from inboxscan import __version__

app = typer.Typer(help="Find every subscription hiding in your email.")
auth_app = typer.Typer(help="Manage connected Gmail accounts.")
app.add_typer(auth_app, name="auth")
console = Console()


@auth_app.command("add")
def auth_add():
    """Connect a Gmail account via Google sign-in."""
    from inboxscan.auth import add_account
    console.print("[dim]Opening browser for Google sign-in...[/dim]")
    email = add_account()
    console.print(f"[green]Connected:[/green] {email}")


@auth_app.command("list")
def auth_list():
    """Show all connected Gmail accounts."""
    from inboxscan.auth import list_accounts
    accounts = list_accounts()
    if not accounts:
        console.print("[dim]No accounts connected. Run: inboxscan auth add[/dim]")
        return
    console.print("\n[bold]Connected accounts:[/bold]")
    for account in accounts:
        console.print(f"  {account}")
    console.print()


@auth_app.command("remove")
def auth_remove(email: str = typer.Argument(..., help="Email address to disconnect")):
    """Disconnect a Gmail account."""
    from inboxscan.auth import remove_account
    try:
        remove_account(email)
        console.print(f"[yellow]Disconnected:[/yellow] {email}")
    except FileNotFoundError:
        console.print(f"[red]Not found:[/red] {email}")
        raise typer.Exit(1)


@app.command()
def run(
    email: list[str] = typer.Option(
        None, "--email", "-e",
        help="Email to scan (optional — uses all connected accounts if not specified)"
    ),
    password: str = typer.Option(
        None, "--password", "-p",
        help="Gmail app password (fallback if not using OAuth)"
    ),
):
    """Scan your email for active subscriptions."""
    from inboxscan.models import EmailAccount, ScanResult
    from inboxscan.connector import fetch_emails
    from inboxscan.parser import parse_raw_email
    from inboxscan.detector import detect_service
    from inboxscan.reporter import print_report
    from inboxscan.cache import save_result
    from inboxscan.auth import list_accounts, get_access_token

    accounts_to_scan = list(email) if email else list_accounts()

    if not accounts_to_scan:
        console.print("[red]No accounts connected.[/red] Run: inboxscan auth add")
        raise typer.Exit(1)

    all_subscriptions = []
    seen_services: set[str] = set()

    for email_addr in accounts_to_scan:
        console.print(f"\n[dim]Scanning {email_addr}...[/dim]")
        if password:
            account = EmailAccount(email=email_addr, password=password)
        else:
            try:
                access_token = get_access_token(email_addr)
                account = EmailAccount(email=email_addr, access_token=access_token)
            except ValueError as e:
                console.print(f"[red]{e}[/red]")
                continue

        parsed_emails = []
        for msg_id, raw in fetch_emails(account):
            parsed = parse_raw_email(raw, msg_id, email_addr)
            if parsed is not None:
                parsed_emails.append(parsed)

        from inboxscan.detector import detect_from_batch
        for sub in detect_from_batch(parsed_emails):
            key = f"{sub.service_name}:{email_addr}"
            if key in seen_services:
                continue
            seen_services.add(key)
            sub.source_email = email_addr
            all_subscriptions.append(sub)

    result = ScanResult(
        accounts_scanned=accounts_to_scan,
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
