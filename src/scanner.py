import asyncio
import logging
from collections import defaultdict
from statistics import median
from typing import Any

from telethon import functions, types
from telethon.errors import FloodWaitError

from .strategy import Candidate, Strategy, choose_candidates

log = logging.getLogger(__name__)


def _price_in_stars(gift: Any) -> float | None:
    """Return the lowest Stars-denominated resale amount, if present."""
    amounts = getattr(gift, "resell_amount", None) or []
    values: list[float] = []
    for amount in amounts:
        whole = getattr(amount, "amount", None)
        if whole is None:
            continue
        nanos = getattr(amount, "nanos", 0) or 0
        values.append(float(whole) + float(nanos) / 1_000_000_000)
    return min(values) if values else None


def _json_value(value: Any) -> Any:
    """Convert Telegram's JSONValue TL constructors into native Python values."""
    if value is None:
        return None
    if isinstance(value, types.JsonNull):
        return None
    if isinstance(value, types.JsonNumber):
        return value.value
    if isinstance(value, types.JsonString):
        return value.value
    if isinstance(value, types.JsonBool):
        return value.value
    if isinstance(value, types.JsonArray):
        return [_json_value(item) for item in value.value]
    if isinstance(value, types.JsonObject):
        return {
            item.key: _json_value(item.value)
            for item in value.value
        }
    return None


class GiftScanner:
    def __init__(self, client, settings):
        self.client = client
        self.settings = settings
        self.strategy = Strategy()

    async def _request(self, request):
        try:
            return await self.client(request)
        except FloodWaitError as exc:
            wait_seconds = int(getattr(exc, "seconds", 0)) + 2
            log.warning("Telegram rate limit: pausing for %s seconds", wait_seconds)
            await asyncio.sleep(wait_seconds)
            return await self.client(request)

    async def _resale_commission_permille(self) -> int | None:
        """Read the current resale commission from Telegram's app configuration."""
        try:
            response = await self._request(functions.help.GetAppConfigRequest(hash=0))
            config = _json_value(getattr(response, "config", None))
            value = config.get("stars_stargift_resale_commission_permille") if isinstance(config, dict) else None
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            commission = int(value)
            if not 0 <= commission < 1000:
                return None
            return commission
        except Exception:
            log.exception("Could not read Telegram resale commission; profit screening disabled")
            return None

    async def get_gift_types(self) -> list[Any]:
        result = await self._request(functions.payments.GetStarGiftsRequest(hash=0))
        gifts = getattr(result, "gifts", []) or []
        # Avoid relying on Telethon's abstract TL base-class export: Telegram
        # catalogue entries are concrete constructors with id/title fields.
        return [
            gift for gift in gifts
            if getattr(gift, "id", None) is not None
            and getattr(gift, "title", None)
        ]

    async def _fetch_page(self, gift_id: int, *, sort_by_price: bool, offset: str = ""):
        return await self._request(
            functions.payments.GetResaleStarGiftsRequest(
                sort_by_price=sort_by_price,
                stars_only=True,
                gift_id=gift_id,
                attributes=[],
                offset=offset,
                limit=self.settings.page_size,
            )
        )

    async def scan_gift_type(self, gift_type: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        gift_id = int(gift_type.id)
        offset = ""

        # Fetch cheapest listings first, with bounded pagination.
        for _ in range(self.settings.max_pages_per_gift):
            result = await self._fetch_page(gift_id, sort_by_price=True, offset=offset)
            for item in getattr(result, "gifts", []) or []:
                price = _price_in_stars(item)
                if price is None:
                    continue
                slug = getattr(item, "slug", "")
                found.append({
                    "gift_type": getattr(gift_type, "title", str(gift_id)),
                    "gift_id": gift_id,
                    "title": getattr(item, "title", "Unknown gift"),
                    "number": getattr(item, "num", None),
                    "price_stars": price,
                    "slug": slug,
                    "url": f"https://t.me/nft/{slug}" if slug else None,
                })

            next_offset = getattr(result, "next_offset", None)
            if not next_offset or next_offset == offset:
                break
            offset = next_offset
            await asyncio.sleep(self.settings.request_pause_seconds)

        # Fetch a separate recent-price sample. Telegram documents that omitting
        # sort_by_price sorts by most recently changed resale price.
        recent = await self._fetch_page(gift_id, sort_by_price=False)
        recent_prices = [
            price for item in (getattr(recent, "gifts", []) or [])
            if (price := _price_in_stars(item)) is not None
        ]
        if len(recent_prices) >= 5:
            reference_price = median(recent_prices)
            for listing in found:
                listing["market_reference_stars"] = reference_price
                listing["reference_sample_size"] = len(recent_prices)
        else:
            for listing in found:
                listing["market_reference_stars"] = None
                listing["reference_sample_size"] = len(recent_prices)

        return found

    def _screen_for_profit(
        self, listings: list[dict[str, Any]], commission_permille: int | None
    ) -> None:
        if commission_permille is None:
            log.warning("Profit screening skipped: Telegram commission is unavailable")
            return

        candidates: list[Candidate] = []
        for listing in listings:
            reference = listing.get("market_reference_stars")
            if reference is None or listing.get("reference_sample_size", 0) < 5:
                continue
            candidates.append(Candidate(
                slug=listing["slug"],
                gift_type=listing["gift_type"],
                asking_price_stars=listing["price_stars"],
                conservative_market_price_stars=reference,
                resale_commission_permille=commission_permille,
            ))

        selected = choose_candidates(candidates, self.strategy)
        if not selected:
            log.info("No listings passed the 400-Star / two-gift profit screen")
            return

        for item in selected:
            log.warning(
                "PAPER BUY CANDIDATE (NO PURCHASE): %s — ask %.2f Stars; "
                "recent listing median %.2f; estimated net resale %.2f; "
                "estimated profit %.2f Stars (ROI %.1f%%); %s",
                item.candidate.gift_type,
                item.candidate.asking_price_stars,
                item.candidate.conservative_market_price_stars,
                item.estimated_net_resale_stars,
                item.estimated_profit_stars,
                item.estimated_roi_percent,
                "https://t.me/nft/" + item.candidate.slug,
            )

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
                        log.info(
                            "PRICE FILTER MATCH: %s #%s — %.2f Stars — %s",
                            listing["gift_type"], listing["number"],
                            listing["price_stars"], listing["url"] or listing["slug"],
                        )
            except FloodWaitError:
                raise
            except Exception:
                log.exception(
                    "Could not scan gift type %s (%s)",
                    getattr(gift_type, "title", "?"), getattr(gift_type, "id", "?")
                )
            if index < len(gift_types):
                await asyncio.sleep(self.settings.request_pause_seconds)

        commission = await self._resale_commission_permille()
        self._screen_for_profit(all_listings, commission)
        log.info("Scan complete: %d listings checked", len(all_listings))
        return all_listings
