#!/usr/bin/env python3
"""
Centinela - AI Market Monitor Agent
Usage: python main.py --help
"""
from __future__ import annotations

import asyncio
import os

import typer
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

_MISSING_KEY = not os.getenv("ANTHROPIC_API_KEY")

app = typer.Typer(
    name="centinela",
    help="Centinela - AI agent that monitors crypto prices and alerts on thresholds.",
    no_args_is_help=True,
)
console = Console()

_SEVERITY_COLOR = {"info": "cyan", "warning": "yellow", "critical": "red bold"}


def _check_key() -> None:
    if _MISSING_KEY:
        console.print(
            Panel(
                "[red]ANTHROPIC_API_KEY not set.[/red]\n\n"
                "1. Copy [cyan].env.example[/cyan] -> [cyan].env[/cyan]\n"
                "2. Add your key from [link=https://console.anthropic.com]console.anthropic.com[/link]",
                title="[red]Configuration Error[/red]",
                border_style="red",
            )
        )
        raise typer.Exit(1)


# -- Agent runner --------------------------------------------------------------

async def _run_agent(task: str) -> None:
    from pricewatch.agent import agent

    console.print(
        Panel(
            f"[bold cyan]Centinela[/bold cyan] - AI Market Monitor Agent\n"
            f"[dim]Task:[/dim] {task[:140]}{'...' if len(task) > 140 else ''}",
            border_style="cyan",
            padding=(0, 1),
        )
    )

    with console.status("[bold green]Agent thinking...", spinner="dots2"):
        result = await agent.run(task)

    report = result.output

    # -- Report panel --
    console.print(
        Panel(
            report.summary,
            title="[bold blue]Market Report[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
    )

    if report.alerts:
        console.print("\n[bold red]Alerts triggered[/bold red]")
        for a in report.alerts:
            console.print(f"  [red]-[/red] {a}")

    if report.recommendations:
        console.print("\n[bold yellow]Recommendations[/bold yellow]")
        for r in report.recommendations:
            console.print(f"  [yellow]-[/yellow] {r}")

    if report.coins_analyzed:
        coins_str = "  ".join(c.upper() for c in report.coins_analyzed)
        console.print(f"\n[dim]Analyzed: {coins_str}[/dim]")

    usage = result.usage
    total = (usage.input_tokens or 0) + (usage.output_tokens or 0)
    console.print(
        f"[dim]Tokens: {usage.input_tokens} in / {usage.output_tokens} out"
        f" | Tool calls: {usage.tool_calls} | Total: {total}[/dim]\n"
    )

    # -- WhatsApp report --
    from pricewatch.notifier import whatsapp_configured, send_report
    if whatsapp_configured():
        with console.status("[bold green]Sending WhatsApp report..."):
            wa = send_report(report)
        if wa.get("status") == "sent":
            console.print(f"[green]WhatsApp sent[/green] [dim](SID: {wa['sid']})[/dim]")
        else:
            console.print(f"[red]WhatsApp error:[/red] {wa.get('message', wa)}")
    else:
        console.print("[dim]WhatsApp not configured (see .env)[/dim]")


# -- Commands ------------------------------------------------------------------

@app.command()
def run(
    task: str = typer.Argument(
        "Check my watchlist. Get current prices, analyze 7-day trends, "
        "verify threshold breaches, save any alerts, and give me a market report.",
        help="Natural language task for the agent",
    ),
) -> None:
    """Run the agent with a custom natural-language task."""
    _check_key()
    asyncio.run(_run_agent(task))


@app.command()
def scan() -> None:
    """Autonomous scan: check all watchlist coins for threshold breaches."""
    _check_key()
    task = (
        "Full watchlist scan. For every coin in the watchlist: "
        "(1) fetch current price, "
        "(2) check if threshold_low or threshold_high is breached -> save_alert if so, "
        "(3) run 7-day trend analysis. "
        "Return an executive market report."
    )
    asyncio.run(_run_agent(task))


@app.command()
def watch(
    coin: str = typer.Argument(..., help="Coin name or ID (e.g. bitcoin, ETH, solana)"),
    low: float = typer.Option(None, "--low", "-l", help="Alert when price drops BELOW this USD value"),
    high: float = typer.Option(None, "--high", "-h", help="Alert when price rises ABOVE this USD value"),
) -> None:
    """Add a coin to the watchlist with optional alert thresholds."""
    _check_key()
    parts = [f"Add '{coin}' to the watchlist."]
    if low:
        parts.append(f"Set a low alert at ${low:,.0f}.")
    if high:
        parts.append(f"Set a high alert at ${high:,.0f}.")
    parts.append("Fetch its current price and show me the result.")
    asyncio.run(_run_agent(" ".join(parts)))


@app.command()
def prices(
    coins: list[str] = typer.Argument(..., help="Coin IDs to check (e.g. bitcoin ethereum solana)"),
) -> None:
    """Quick price check + 7-day trend for a list of coins."""
    _check_key()
    coin_list = ", ".join(coins)
    asyncio.run(
        _run_agent(
            f"Fetch current prices and 7-day trends for: {coin_list}. "
            "Summarize in the report. Do NOT modify the watchlist."
        )
    )


@app.command()
def alerts(
    limit: int = typer.Option(15, "--limit", "-n", help="Number of recent alerts to show"),
) -> None:
    """Show recent saved alerts (no agent call needed)."""
    from pricewatch.storage import read_json

    saved: list = read_json("alerts.json")  # type: ignore[assignment]
    recent = saved[-limit:]

    if not recent:
        console.print("[dim]No alerts saved yet. Run 'scan' or 'watch' to start monitoring.[/dim]")
        return

    table = Table(
        title=f"Recent Alerts (last {len(recent)})",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=False,
    )
    table.add_column("Time", style="dim", width=19)
    table.add_column("Coin", style="cyan", width=12)
    table.add_column("Severity", width=10)
    table.add_column("Message")

    for a in reversed(recent):
        sev = a.get("severity", "info")
        color = _SEVERITY_COLOR.get(sev, "white")
        table.add_row(
            a["timestamp"][:19].replace("T", " "),
            a["coin_id"].upper(),
            f"[{color}]{sev}[/{color}]",
            a["message"],
        )

    console.print(table)


@app.command()
def watchlist() -> None:
    """Show the current watchlist (no agent call needed)."""
    from pricewatch.storage import read_json

    wl: list = read_json("watchlist.json")  # type: ignore[assignment]

    if not wl:
        console.print(
            "[dim]Watchlist is empty. Run[/dim] [cyan]centinela watch bitcoin --low 50000[/cyan] [dim]to start.[/dim]"
        )
        return

    table = Table(
        title="Watchlist",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Coin", style="cyan bold")
    table.add_column("Alias")
    table.add_column("Alert Low (USD)", justify="right", style="green")
    table.add_column("Alert High (USD)", justify="right", style="red")
    table.add_column("Added", style="dim")

    for w in wl:
        table.add_row(
            w["coin_id"].upper(),
            w.get("alias", ""),
            f"${w['threshold_low']:,.0f}" if w.get("threshold_low") else "-",
            f"${w['threshold_high']:,.0f}" if w.get("threshold_high") else "-",
            w.get("added_at", "")[:10],
        )

    console.print(table)


# -- Entry point ---------------------------------------------------------------

if __name__ == "__main__":
    app()
