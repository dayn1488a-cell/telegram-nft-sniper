import asyncio
import os
from getpass import getpass

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession


async def main() -> None:
    load_dotenv()
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    phone = os.getenv("TELEGRAM_PHONE", "").strip()

    if not api_id or not api_hash or not phone:
        raise RuntimeError(
            "Set TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_PHONE in your local .env first."
        )

    client = TelegramClient(StringSession(), int(api_id), api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = getpass("Telegram login code (input hidden): ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = getpass("Telegram 2-step verification password (input hidden): ")
                await client.sign_in(password=password)

        print("\nTELEGRAM_SESSION (SECRET — do not send it to anyone):")
        print(client.session.save())
        print(
            "\nCopy this value directly into Railway's TELEGRAM_SESSION variable. "
            "Do not commit it to GitHub or paste it into chats."
        )
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
