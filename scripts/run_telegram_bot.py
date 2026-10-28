from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from rich.console import Console
from rich.panel import Panel

from backend.config import settings
from backend.telegram.bot import TelegramBotService

console = Console()


async def run_bot_polling(token: str):
    """Runs long polling listener for the Telegram Bot."""
    bot = TelegramBotService(token=token)
    api_url = f"https://api.telegram.org/bot{token}"

    console.print(Panel(
        "[bold green]AI Football Probability Engine — Telegram Bot Active![/bold green]\n"
        "Bot token loaded; checking Telegram authentication...\n\n"
        "Go to your bot in Telegram and send:\n"
        "  • [bold yellow]/start[/bold yellow] or [bold yellow]/help[/bold yellow]\n"
        "  • [bold yellow]/predictions[/bold yellow]\n"
        "  • [bold yellow]/bankers[/bold yellow]\n"
        "  • [bold yellow]/2_odds[/bold yellow]\n"
        "  • [bold yellow]/5_odds[/bold yellow]\n"
        "  • [bold yellow]/15_odds[/bold yellow]\n"
        "  • [bold yellow]/performance[/bold yellow]\n\n"
        "[dim]Press Ctrl+C to stop the bot.[/dim]",
        title="Telegram Bot Live Poller",
        border_style="green",
    ))

    offset = 0
    timeout = 30

    async with httpx.AsyncClient(timeout=40.0) as client:
        # Verify bot identity
        try:
            me_resp = await client.get(f"{api_url}/getMe")
            me_data = me_resp.json()
            if me_data.get("ok"):
                username = me_data["result"].get("username", "UnknownBot")
                console.print(f"[bold cyan]Logged in as @{username}[/bold cyan]")
            else:
                console.print(f"[bold red]Token authentication failed:[/bold red] {me_data}")
                return
        except Exception as exc:
            console.print(f"[bold red]Connection error:[/bold red] {exc}")
            return

        while True:
            try:
                resp = await client.get(
                    f"{api_url}/getUpdates",
                    params={"offset": offset, "timeout": timeout},
                )
                if resp.status_code != 200:
                    await asyncio.sleep(2)
                    continue

                updates = resp.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    chat_id = chat.get("id")
                    text = message.get("text", "").strip()
                    username = chat.get("username", "user")

                    if not text or not chat_id:
                        continue

                    console.print(f"[dim]Received command [bold yellow]{text}[/bold yellow] from @{username}[/dim]")

                    # Process command using TelegramBotService
                    reply = await bot.handle_command(chat_id=chat_id, command=text)
                    await bot.send_message(chat_id=chat_id, text=reply)

            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"[yellow]Polling warning: {e}[/yellow]")
                await asyncio.sleep(3)


def main():
    parser = argparse.ArgumentParser(description="Run Telegram Bot Polling Service")
    parser.add_argument("--token", default="", help="Telegram Bot Token from @BotFather")
    parser.add_argument("--api-url", default="", help="Base URL of your hosted backend API (e.g. https://my-backend.railway.app)")
    parser.add_argument("--app-url", default="", help="URL of your hosted web frontend / Mini App (e.g. https://my-frontend.vercel.app)")
    args = parser.parse_args()

    if args.api_url:
        settings.api_base_url = args.api_url.rstrip("/")
    if args.app_url:
        settings.webapp_url = args.app_url.rstrip("/")

    token = args.token or settings.telegram_bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")

    if not token:
        console.print(Panel(
            "[bold yellow]No Telegram Bot Token provided![/bold yellow]\n\n"
            "To connect your bot:\n"
            "1. Open Telegram and search for [bold cyan]@BotFather[/bold cyan]\n"
            "2. Send [bold]/newbot[/bold] and follow instructions to get your API Token\n"
            "3. Either:\n"
            "   a) Add it to your [bold].env[/bold] file: [green]TELEGRAM_BOT_TOKEN=123456:ABC-DEF...[/green]\n"
            "   b) Or run with: [green]python scripts/run_telegram_bot.py --token <YOUR_TOKEN> --api-url <YOUR_HOSTED_BACKEND_URL>[/green]",
            title="Setup Telegram Bot",
            border_style="yellow",
        ))
        return

    console.print(f"[bold cyan]Connected to backend API:[/bold cyan] {settings.api_base_url}")
    if settings.webapp_url:
        console.print(f"[bold cyan]Web App Mini App URL:[/bold cyan] {settings.webapp_url}")

    try:
        asyncio.run(run_bot_polling(token))
    except KeyboardInterrupt:
        console.print("[dim]Bot stopped by user.[/dim]")


if __name__ == "__main__":
    main()
