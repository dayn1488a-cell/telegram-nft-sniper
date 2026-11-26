# Telegram NFT Gift Scanner

A read-only scanner for Telegram's official collectible-gift resale marketplace. It uses Telegram's MTProto API through Telethon. It does not buy, sell, transfer, or otherwise spend Stars.

## Agreed starter-budget policy

The screening policy is configured for a 400-Star starting balance:

- Target: at least 2 collectible gifts.
- Maximum purchase price per gift: 200 Stars.
- Maximum total budget: 400 Stars.
- A candidate must show at least 15% estimated ROI after Telegram's current resale payout share.
- If fewer than 2 candidates pass, the scanner keeps the unused Stars; it must never buy a weak listing just to reach the target.

The policy lives in `src/strategy.py`. It is a screening/paper-trading component only. It does not submit Telegram payments.

## Market screening method

- Fetches the cheapest Stars listings with bounded pagination.
- Separately fetches a sample sorted by most recently changed resale price.
- Uses the median asking price from that recent sample as a rough reference, and requires at least five observations.
- Reads Telegram's current resale payout share from app configuration; for example, 800 permille means the seller receives 80% of the resale price.
- Fails closed: if the payout share or reference sample is unavailable, no profit candidate is produced.

**Important:** this is a listing-based estimate, not completed-sale data. It cannot prove that a gift will sell at the reference price, or that a profit will be realized. Before any real purchase feature is considered, the estimator must be validated against observed price history, liquidity, fees, and actual resale outcomes.

## Local setup and authentication

1. Create Telegram API credentials at https://my.telegram.org/apps.
2. Copy `.env.example` to `.env` and set `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_PHONE`.
3. Install dependencies: `pip install -r requirements.txt`.
4. To create a cloud-compatible session, run `python -m src.auth_setup` in a private local terminal. Enter the Telegram code and 2-step password only into that terminal. The script prints a `TELEGRAM_SESSION` value.
5. Copy that value directly into Railway's protected `TELEGRAM_SESSION` environment variable. Never send it in chat, commit it to GitHub, or put it in a public file.
6. Run locally with `python -m src.main`, or deploy the scanner after setting the required Railway variables.

The session string grants access to the Telegram account. Treat it like a password. If it leaks, terminate the session from Telegram's active sessions.

## Configuration

- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`: credentials from my.telegram.org.
- `TELEGRAM_PHONE`: account phone used only for local authentication.
- `TELEGRAM_SESSION`: protected StringSession for cloud use; never commit.
- `SCAN_INTERVAL_SECONDS`: delay between full scans (minimum 30 seconds; default 60).
- `REQUEST_PAUSE_SECONDS`: pause between gift-type/page requests (minimum 1 second; default 1.5).
- `MAX_PAGES_PER_GIFT`: cheapest pages checked per gift type (default 2, maximum 10).
- `PAGE_SIZE`: results per page (10–100; default 50).
- `MAX_ALERT_PRICE_STARS`: log filter threshold (default 400 Stars).

## Important limitations

- Telegram may apply rate limits or change API layers; `FLOOD_WAIT` pauses are respected, but repeated requests can still be restricted.
- The scanner checks only the configured number of cheapest pages per gift type plus one recent-price sample; it is not an exhaustive market snapshot.
- A low listing price does not guarantee resale demand, profit, or a successful resale. Fees, resale payout share, listing restrictions, and price movement matter.
- Automated purchases and sales are deliberately disabled. The agreed budget limits are not permission for the code to bypass profitability checks or spend Stars during this read-only stage.
- For reliable cloud operation, `TELEGRAM_SESSION` must be stored as a protected Railway variable. No session file or login code belongs in GitHub.

## Official Telegram API references

- https://core.telegram.org/api/gifts
- https://core.telegram.org/method/payments.getResaleStarGifts
- https://core.telegram.org/constructor/starGiftUnique
- https://core.telegram.org/api/config
