from rich.console import Console
from inboxscan.detector import KNOWN_SERVICES

console = Console()

CANCELLATION_TEMPLATES: dict[str, str] = {
    "Netflix": "Subject: Cancel My Subscription\n\nPlease cancel my Netflix subscription immediately and confirm via email.",
    "Spotify": "Subject: Subscription Cancellation Request\n\nPlease cancel my Spotify Premium subscription and confirm.",
    "Adobe CC": "Subject: Cancel Creative Cloud Subscription\n\nI would like to cancel my Adobe Creative Cloud subscription. Please process this immediately.",
    "Audible": "Subject: Cancel Audible Membership\n\nPlease cancel my Audible membership immediately and confirm cancellation.",
    "Skillshare": "Subject: Cancel Skillshare Subscription\n\nPlease cancel my Skillshare subscription effective immediately.",
}


def cancel_service(service_name: str) -> None:
    matched = None
    for domain, (name, url, _) in KNOWN_SERVICES.items():
        if name.lower() == service_name.lower():
            matched = (name, url)
            break

    if not matched:
        console.print(f"[red]Unknown service: {service_name}[/red]")
        console.print("Run [bold]inboxscan run[/bold] to see your active subscriptions.")
        return

    name, url = matched
    console.print(f"\n[bold]Cancel {name}[/bold]")
    console.print("─" * 40)
    console.print(f"Cancellation page: [link={url}]{url}[/link]")

    template = CANCELLATION_TEMPLATES.get(name)
    if template:
        console.print("\n[bold]Email template:[/bold]")
        console.print(f"[dim]{template}[/dim]")
    console.print()
