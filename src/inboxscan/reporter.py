from rich.console import Console
from rich.table import Table
from rich import box
from inboxscan.models import ScanResult, SubscriptionStatus

console = Console()


def print_report(result: ScanResult) -> None:
    console.print("\n[bold]INBOXSCAN REPORT[/bold]")
    console.print("═" * 60)
    console.print(f"Scanned: {', '.join(result.accounts_scanned)}")
    console.print(
        f"Found: [bold]{len(result.subscriptions)}[/bold] subscriptions  "
        f"|  Total burn: [bold green]${result.total_monthly_burn:.2f}/mo[/bold green]"
    )
    console.print()

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Status", style="bold", width=10)
    table.add_column("Service", width=20)
    table.add_column("Amount", width=12)
    table.add_column("Last charge", width=12)
    table.add_column("Account", style="dim")

    for sub in sorted(result.subscriptions, key=lambda s: s.status.value):
        status_str = {
            SubscriptionStatus.ACTIVE: "[green]\\[ACTIVE][/green]",
            SubscriptionStatus.DORMANT: "[yellow]\\[DORMANT][/yellow]",
            SubscriptionStatus.UNKNOWN: "[dim]\\[UNKNOWN][/dim]",
        }[sub.status]
        table.add_row(
            status_str,
            sub.service_name,
            f"${sub.amount:.2f}/{sub.billing_frequency[:2]}",
            sub.last_charge_date.strftime("%b %d"),
            sub.source_email,
        )

    console.print(table)
    console.print("═" * 60)

    if result.dormant_monthly_waste > 0:
        console.print(
            f"[yellow]Potential savings: ${result.dormant_monthly_waste:.2f}/mo "
            f"(cancel DORMANT subscriptions)[/yellow]"
        )

    if result.unknown_charges > 0:
        console.print(f"[dim]{result.unknown_charges} unrecognized recurring charges — review manually[/dim]")

    console.print("\nRun [bold]inboxscan cancel <service>[/bold] for cancellation steps.\n")
