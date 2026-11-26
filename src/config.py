from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    phone: str | None
    session_string: str | None
    scan_interval_seconds: int
    request_pause_seconds: float
    max_pages_per_gift: int
    page_size: int
    max_alert_price_stars: int


def load_settings() -> Settings:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    if not api_id or not api_hash:
        raise RuntimeError(
            "Set TELEGRAM_API_ID and TELEGRAM_API_HASH in the environment. "
            "Create them at https://my.telegram.org/apps."
        )

    try:
        parsed_api_id = int(api_id)
        scan_interval = max(30, int(os.getenv("SCAN_INTERVAL_SECONDS", "60")))
        request_pause = max(1.0, float(os.getenv("REQUEST_PAUSE_SECONDS", "1.5")))
        max_pages = max(1, min(10, int(os.getenv("MAX_PAGES_PER_GIFT", "2"))))
        page_size = max(10, min(100, int(os.getenv("PAGE_SIZE", "50"))))
        max_alert_price = max(1, int(os.getenv("MAX_ALERT_PRICE_STARS", "400")))
    except ValueError as exc:
        raise RuntimeError("One of the numeric scanner settings is invalid.") from exc

    return Settings(
        api_id=parsed_api_id,
        api_hash=api_hash,
        phone=os.getenv("TELEGRAM_PHONE") or None,
        session_string=os.getenv("TELEGRAM_SESSION", "").strip() or None,
        scan_interval_seconds=scan_interval,
        request_pause_seconds=request_pause,
        max_pages_per_gift=max_pages,
        page_size=page_size,
        max_alert_price_stars=max_alert_price,
    )
