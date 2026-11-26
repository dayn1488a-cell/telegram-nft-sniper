import asyncio
import logging
from typing import Any

from telethon import functions, types
from telethon.errors import FloodWaitError

log = logging.getLogger(__name__)


def _price_in_stars(gift: Any) -> float | None:
    """Return the lowest Stars-denominated resale amount, if present."""
    amounts = getattr(gift, "resell_amount", None) or []
    values: list[float] = []
    for amount in amounts:
        # Telegram StarsAmount stores whole Stars and an optional nanos part.
        whole = getattr(amount, "amount", None)
        if whole is None:
            continue
        nanos = getattr(amount, "nanos", 0) or 0
        values.append(float(whole) + float(nanos) / 1_000_000_000)
    return min(values) if values else None


class GiftScanner:
    def __init__(self, client, settings):
        self.client = client
        self.settings = settings

    async def _request(self, request):
        try:
            return await self.client(request)
        except FloodWaitError as exc:
            wait_seconds = int(getattr(exc, "seconds", 0)) + 2
            log.warning("Telegram rate limit: pausing for %s seconds", wait_seconds)
            await asyncio.sleep(wait_seconds)
            return await self.client(request)

    async def get_gift_types(self) -> list[Any]:
        result = await self._request(functions.payments.GetStarGiftsRequest(hash=0))
        gifts = getattr(result, "gifts", []) or []
        # Only regular gift types have an id usable as getResaleStarGifts.gift_id.
        return [gift for gift in gifts if isinstance(gift, types.StarGift)]

    async def scan_gift_type(self, gift_type: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        offset = ""
        gift_id = int(gift_type.id)

        for _ in range(self.settings.max_pages_per_gift):
            result = await self._request(
                functions.payments.GetResaleStarGiftsRequest(
                    sort_by_price=True,
                    stars_only=True,
                    gift_id=gift_id,
                    attributes=[],
                    offset=offset,
                    limit=self.settings.page_size,
                )
            )
            for item in getattr(result, "gifts", []) or []:
                price = _price_in_stars(item)
                if price is None:
                    continue
                found.append({
                    "gift_type": getattr(gift_type, "title", str(gift_id)),
                    "gift_id": gift_id,
                    "title": getattr(item, "title", "Unknown gift"),
                    "number": getattr(item, "num", None),
                    "price_stars": price,
                    "slug": getattr(item, "slug", ""),
                    "url": f"https://t.me/nft/{getattr(item, 'slug', '')}" if getattr(item, "slug", None) else None,
                })

            next_offset = getattr(result, "next_offset", None)
            if not next_offset or next_offset == offset:
                break
            offset = next_offset
            await asyncio.sleep(self.settings.request_pause_seconds)

        return found

    async def scan_once(self) -> list[dict[str, Any]]:
        gift_types = await self.get_gift_types()
        log.info("Checking resale listings for %d gift types", len(gift_types))
        all_listings: list[dict[str, Any]] = []

        for index, gift_type in enumerate(gift_types, start=1):
            try:
                listings = await self.scan_gift_type(gift_type)
                all_listings.extend(listings)
                for listing in listings:
                    if listing["price_stars"] <= self.settings.max_alert_price_stars:
                        log.warning(
                            "PRICE FILTER MATCH: %s #%s — %.2f Stars — %s",
                            listing["gift_type"], listing["number"],
                            listing["price_stars"], listing["url"] or listing["slug"],
                        )
            except FloodWaitError:
                raise
            except Exception:
                log.exception("Could not scan gift type %s (%s)", getattr(gift_type, "title", "?"), getattr(gift_type, "id", "?"))
            if index < len(gift_types):
                await asyncio.sleep(self.settings.request_pause_seconds)

        log.info("Scan complete: %d listings checked", len(all_listings))
        return all_listings
