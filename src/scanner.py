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
        """Read Telegram's current resale commission; fail closed if unavailable."""
        try:
            config = await self._request(functions.help.GetConfigRequest())
            value = getattr(config, "stars_stargift_resale_commission_permille", None)
            if value is None or not 0 <= int(value) < 1000:
                return None
            return int(value)
        except Exception:
            log.exception("Could not read Telegram resale commission; profit screening disabled")
            return None

    async def get_gift_types(self) -> list[Any]:
        result = await self._request(functions.payments.GetStarGiftsRequest(hash=0))
        gifts = getattr(result, "gifts", []) or []
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

        return found

    def _screen_for_profit(
        self, listings: list[dict[str, Any]], commission_permille: int | None
    ) -> None:
        if commission_permille is None:
            log.warning("Profit screening skipped: Telegram commission is unavailable")
            return

        by_type: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for listing in listings:
            by_type[listing["gift_id"]].append(listing)

        candidates: list[Candidate] = []
        for same_type in by_type.values():
            # Median of the observed official-market asks is only a rough proxy,
            # not a completed-sale price. Use it conservatively and keep paper-only.
            reference_price = median(x["price_stars"] for x in same_type)
            for listing in same_type:
                candidates.append(Candidate(
                    slug=listing["slug"],
                    gift_type=listing["gift_type"],
                    asking_price_stars=listing["price_stars"],
                    conservative_market_price_stars=reference_price,
                    resale_commission_permille=commission_permille,
                ))

        selected = choose_candidates(candidates, self.strategy)
        if not selected:
            log.info("No listings passed the 400-Star / two-gift profit screen")
            return

        for item in selected:
            log.warning(
                "PAPER BUY CANDIDATE (NO PURCHASE): %s — ask %.2f Stars; "
                "estimated net resale %.2f; estimated profit %.2f Stars (ROI %.1f%%); %s",
                item.candidate.gift_type,
                item.candidate.asking_price_stars,
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
