# Telegram NFT Gift Scanner

A read-only scanner for Telegram's official collectible-gift resale marketplace. It uses Telegram's MTProto API through Telethon. It does not buy, sell, transfer, or otherwise spend Stars.

## Agreed starter-budget policy

The screening policy is configured for a 400-Star starting balance:

- Target: at least 2 collectible gifts.
- Maximum purchase price per gift: 200 Stars.
- Maximum total budget: 400 Stars.
- A candidate must show at least 15% estimated ROI after Telegram's current resale commission.
- If fewer than 2 candidates pass, the scanner keeps the unused Stars; it must never buy a weak listing just to reach the target.

The policy lives in `src/strategy.py`. It is a screening/paper-trading component only. It does not submit Telegram payments.

## Market screening method

- Fetches the cheapest Stars listings with bounded pagination.
- Separately fetches a sample sorted by most recently changed resale price.
- Uses the median asking price from that recent sample as a rough reference, and requires at least five observations.
- Reads Telegram's current resale commission from app configuration; the value is the seller's payout share (for example, 800 permille means 80% of the resale price is paid to the seller).
- Fails closed: if the commission or reference sample is unavailable, no profit candidate is produced.

**Important:** this is a listing-based estimate, not completed-sale data. It cannot prove that a gift will sell at the reference price, or that a profit will be realized. Before any real purchase feature is considered, the estimator must be validated against observed price history, liquidity, fees, and actual resale outcomes.

## Current scope

- Reads the official Telegram gift catalogue and resale listings.
- Requests Stars-only listings.
- Logs low-price listings as filter matches; a low price alone is not a profit signal.
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
- The scanner checks only the configured number of cheapest pages per gift type plus one recent-price sample; it is not an exhaustive market snapshot.
- A low listing price does not guarantee resale demand, profit, or a successful resale. Fees, resale commission, listing restrictions, and price movement matter.
- Automated purchases and sales are deliberately disabled. The agreed budget limits are not permission for the code to bypass profitability checks or spend Stars during this read-only stage.
- For reliable cloud operation, authentication/session persistence and Railway storage must be configured securely before deployment.

## Official Telegram API references

- https://core.telegram.org/api/gifts
- https://core.telegram.org/method/payments.getResaleStarGifts
- https://core.telegram.org/constructor/starGiftUnique
- https://core.telegram.org/api/config
