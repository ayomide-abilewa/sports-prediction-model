from __future__ import annotations

import os
import sys
from pathlib import Path

# 1. Windows UTF-8 console output setup
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 2. Auto-forward to virtual environment if invoked with global system Python
project_root = Path(__file__).resolve().parent.parent
venv_python = project_root / ".venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    venv_python = project_root / ".venv" / "bin" / "python"

if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
    import subprocess
    sys.exit(subprocess.call([str(venv_python)] + sys.argv))

# Add project root to sys.path
sys.path.insert(0, str(project_root))

import argparse
import asyncio
import re

# Optional rich formatting with graceful plain-text fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
except ImportError:
    class DummyConsole:
        def print(self, msg, *args, **kwargs):
            if hasattr(msg, "renderable"):
                msg = str(msg.renderable)
            clean = re.sub(r"\[/?(?:bold|dim|green|yellow|red|cyan|magenta|blue|white)[^\]]*\]", "", str(msg))
            print(clean)
    class DummyPanel:
        def __init__(self, renderable, title="", border_style=""):
            self.renderable = f"=== {title} ===\n{renderable}" if title else str(renderable)
        def __str__(self):
            return self.renderable
    console = DummyConsole()
    Panel = DummyPanel

import httpx
from backend.config import settings
from backend.telegram.bot import TelegramBotService


async def run_bot_polling(token: str):
    """Runs long polling listener for the Telegram Bot."""
    bot = TelegramBotService(token=token)
    api_url = f"https://api.telegram.org/bot{token}"

    timeout = 30
    offset = 0

    async with httpx.AsyncClient(timeout=40.0) as client:
        # Verify bot identity
        try:
            me_resp = await client.get(f"{api_url}/getMe")
            me_data = me_resp.json()
            if me_data.get("ok"):
                username = me_data["result"].get("username", "UnknownBot")
                first_name = me_data["result"].get("first_name", "Telegram Bot")
                console.print(Panel(
                    f"[bold green]AI Football Probability Engine — Telegram Bot Online![/bold green]\n\n"
                    f"🤖 Logged in as: [bold cyan]@{username}[/bold cyan] ({first_name})\n"
                    f"🔗 API Backend: [bold yellow]{settings.api_base_url}[/bold yellow]\n\n"
                    f"Your bot is now actively listening for messages in Telegram!\n"
                    f"Open Telegram, search for [bold cyan]@{username}[/bold cyan], and send:\n"
                    f"  • [bold yellow]/start[/bold yellow] (opens the interactive menu)\n"
                    f"  • [bold yellow]/today[/bold yellow] or tap [bold]Today's fixtures[/bold]\n"
                    f"  • [bold yellow]/predictions[/bold yellow] (Surest Pick & Best Prop)\n"
                    f"  • [bold yellow]/2_odds[/bold yellow] (Interactive 2x Banker Builder)\n"
                    f"  • [bold yellow]/5_odds[/bold yellow] (Interactive 5x Core Builder)\n"
                    f"  • [bold yellow]/100_odds[/bold yellow] (Interactive 100x Mega Builder)\n"
                    f"  • [bold yellow]/audit[/bold yellow] (Recent Picks Post-Game Review)\n\n"
                    f"[dim]Press Ctrl+C to stop the bot.[/dim]",
                    title="Telegram Bot Live Poller",
                    border_style="green",
                ))
            else:
                console.print(f"[bold red]Token authentication failed:[/bold red] {me_data}")
                return
        except Exception as exc:
            console.print(f"[bold red]Connection error to Telegram API:[/bold red] {exc}")
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

                    # 1. Handle Inline Button Clicks (Callback Queries)
                    callback_query = update.get("callback_query")
                    if callback_query:
                        cq_id = callback_query.get("id")
                        cq_data = callback_query.get("data", "")
                        cq_msg = callback_query.get("message", {})
                        cq_chat = cq_msg.get("chat", {})
                        cq_chat_id = cq_chat.get("id")
                        cq_user = callback_query.get("from", {}).get("username", "user")

                        # Acknowledge callback immediately
                        try:
                            await client.post(f"{api_url}/answerCallbackQuery", json={"callback_query_id": cq_id})
                        except Exception:
                            pass

                        if cq_chat_id and cq_data:
                            console.print(f"[dim]Button clicked [bold cyan]{cq_data}[/bold cyan] by @{cq_user}[/dim]")
                            reply, markup = await bot.handle_callback(chat_id=cq_chat_id, data=cq_data)
                            if reply:
                                await bot.send_message(chat_id=cq_chat_id, text=reply, reply_markup=markup)
                        continue

                    # 2. Handle Text Messages and Keyboard Commands
                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    chat_id = chat.get("id")
                    text = message.get("text", "").strip()
                    username = chat.get("username", "user")

                    if not text or not chat_id:
                        continue

                    console.print(f"[dim]Received command [bold yellow]{text}[/bold yellow] from @{username}[/dim]")

                    reply, markup = await bot.handle_command(chat_id=chat_id, command=text)
                    if reply:
                        await bot.send_message(chat_id=chat_id, text=reply, reply_markup=markup)

            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"[yellow]Polling notice: {e}[/yellow]")
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

    console.print(f"[dim]Connecting bot to backend: {settings.api_base_url}...[/dim]")

    try:
        asyncio.run(run_bot_polling(token))
    except KeyboardInterrupt:
        console.print("[dim]Bot stopped by user.[/dim]")


if __name__ == "__main__":
    main()
