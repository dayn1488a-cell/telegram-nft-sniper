import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from .config import load_settings
from .scanner import GiftScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("gift-sniper")


async def run() -> None:
    settings = load_settings()
    client = TelegramClient("data/telegram_scanner", settings.api_id, settings.api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        if not settings.phone:
            raise RuntimeError("Set TELEGRAM_PHONE for the first sign-in, then complete the code prompt in a secure terminal.")
        await client.send_code_request(settings.phone)
        code = input("Enter the Telegram login code in this private terminal: ").strip()
        try:
            await client.sign_in(settings.phone, code)
        except SessionPasswordNeededError:
            password = input("Enter your Telegram 2-step verification password in this private terminal: ")
            await client.sign_in(password=password)

    log.info("Connected. Read-only mode is active; no purchases or sales are implemented.")
    scanner = GiftScanner(client, settings)
    try:
        while True:
            await scanner.scan_once()
            log.info("Next scan in at least %d seconds", settings.scan_interval_seconds)
            await asyncio.sleep(settings.scan_interval_seconds)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run())
