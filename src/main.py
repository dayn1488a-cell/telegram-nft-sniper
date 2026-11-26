import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.sessions import StringSession

from .config import load_settings
from .scanner import GiftScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("gift-sniper")


async def run() -> None:
    settings = load_settings()

    if settings.session_string:
        session = StringSession(settings.session_string)
        log.info("Using protected TELEGRAM_SESSION environment variable")
    else:
        Path("data").mkdir(parents=True, exist_ok=True)
        session = "data/telegram_scanner"
        log.info("Using local session file in ./data (keep it private)")

    client = TelegramClient(session, settings.api_id, settings.api_hash)
    await client.connect()

    try:
        if not await client.is_user_authorized():
            if settings.session_string:
                raise RuntimeError(
                    "TELEGRAM_SESSION is invalid or expired. Generate a new one "
                    "with python -m src.auth_setup in a private local terminal."
                )
            if not settings.phone:
                raise RuntimeError(
                    "Set TELEGRAM_PHONE for first local sign-in, or create a "
                    "StringSession with python -m src.auth_setup."
                )
            await client.send_code_request(settings.phone)
            code = input("Enter the Telegram login code in this private terminal: ").strip()
            try:
                await client.sign_in(settings.phone, code)
            except SessionPasswordNeededError:
                password = input(
                    "Enter your Telegram 2-step verification password in this private terminal: "
                )
                await client.sign_in(password=password)

        log.info("Connected. Read-only mode is active; no purchases or sales are implemented.")
        scanner = GiftScanner(client, settings)
        while True:
            try:
                await scanner.scan_once()
            except FloodWaitError as exc:
                wait_seconds = max(30, int(getattr(exc, "seconds", 0)) + 5)
                log.warning("Telegram rate limit reached; pausing scanner for %d seconds", wait_seconds)
                await asyncio.sleep(wait_seconds)
                continue
            log.info("Next scan in at least %d seconds", settings.scan_interval_seconds)
            await asyncio.sleep(settings.scan_interval_seconds)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run())
