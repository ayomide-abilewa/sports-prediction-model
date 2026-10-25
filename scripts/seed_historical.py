from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

from backend.db.init_db import seed_initial_data
from backend.ingestion.scheduler import IngestionScheduler

console = Console()


async def run_seed(leagues: list[str], seasons: list[str]):
    """Seeds historical data for specified leagues and seasons."""
    console.print("[bold cyan]Step 1: Initializing database and base references...[/bold cyan]")
    await seed_initial_data()

    scheduler = IngestionScheduler()
    table = Table(title="Historical Data Ingestion Results", show_lines=True)
    table.add_column("League", style="cyan")
    table.add_column("Season", style="magenta")
    table.add_column("Status", style="bold")
    table.add_column("Processed", justify="right")
    table.add_column("New Matches", justify="right", style="green")
    table.add_column("Updated", justify="right", style="yellow")
    table.add_column("Duration", justify="right")

    for league in leagues:
        for season in seasons:
            console.print(f"[dim]Ingesting {league} (season {season})...[/dim]")
            res = await scheduler.ingest_league_season(league, season)

            status_style = "green" if res.status == "success" else ("yellow" if res.status == "partial" else "red")
            dur_str = f"{res.duration_seconds:.1f}s" if res.duration_seconds else "-"

            table.add_row(
                league,
                season,
                f"[{status_style}]{res.status}[/{status_style}]",
                str(res.records_processed),
                str(res.records_new),
                str(res.records_updated),
                dur_str,
            )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Seed historical match data")
    parser.add_argument(
        "--leagues",
        nargs="+",
        default=["ENG-Premier League", "ESP-La Liga", "GER-Bundesliga", "ITA-Serie A"],
        help="List of league codes to seed",
    )
    parser.add_argument(
        "--seasons",
        nargs="+",
        default=["2425", "2324"],
        help="List of seasons to seed (e.g. 2425 2324)",
    )
    args = parser.parse_args()

    asyncio.run(run_seed(args.leagues, args.seasons))


if __name__ == "__main__":
    main()
