# Telegram NFT Gift Scanner

A read-only scanner for Telegram's official collectible-gift resale marketplace. It uses Telegram's MTProto API through Telethon and checks listings by gift type. It does not buy, sell, transfer, or otherwise spend Stars.

## Current scope

- Reads the official Telegram gift catalogue and resale listings.
- Requests Stars-only listings, sorted by ascending price.
- Logs listings at or below `MAX_ALERT_PRICE_STARS` as filter matches. This is only a price filter, not a claim that an item is profitable or underpriced.
- Uses conservative request pacing and handles Telegram flood-wait responses.
- Stores the Telegram login session locally under `data/`; never commit that folder or share the session file.

## Setup

1. Create Telegram API credentials at https://my.telegram.org/apps.
2. Copy `.env.example` to `.env` and set `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_PHONE`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Run from a private terminal: `python -m src.main`.
5. Enter the Telegram login code and, if enabled, 2-step verification password only in that private terminal. Do not send them to anyone or put them in GitHub/Railway variables as plain text in a public repo.

## Configuration

- `SCAN_INTERVAL_SECONDS`: delay between full scans (minimum 30 seconds; default 60).
- `REQUEST_PAUSE_SECONDS`: pause between gift-type/page requests (minimum 1 second; default 1.5).
- `MAX_PAGES_PER_GIFT`: pages checked per gift type (default 2, maximum 10).
- `PAGE_SIZE`: results per page (10–100; default 50).
- `MAX_ALERT_PRICE_STARS`: log filter threshold (default 400 Stars).

## Important limitations

- Telegram may apply rate limits or change API layers; `FLOOD_WAIT` pauses are respected, but repeated requests can still be restricted.
- The scanner checks only the configured number of pages per gift type, so it is not an exhaustive market snapshot.
- A low listing price does not guarantee resale demand, profit, or a successful resale. Fees, resale commission, listing restrictions, and price movement matter.
- The app currently has no automated buying or selling code. Keep it that way until a separate, explicit trading policy is agreed and tested.
- For reliable cloud operation, authentication/session persistence and Railway storage must be configured securely before deployment.

## Official Telegram API references

- https://core.telegram.org/api/gifts
- https://core.telegram.org/method/payments.getResaleStarGifts
