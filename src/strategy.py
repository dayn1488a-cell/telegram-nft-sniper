"""Conservative, read-only purchase screening for the 400-Star starter budget.

This module never performs Telegram payments. It only ranks hypothetical candidates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Strategy:
    budget_stars: int = 400
    max_per_gift_stars: int = 200
    target_gifts: int = 2
    min_profit_percent: float = 15.0


@dataclass(frozen=True)
class Candidate:
    slug: str
    gift_type: str
    asking_price_stars: float
    conservative_market_price_stars: float
    resale_commission_permille: int


@dataclass(frozen=True)
class Evaluation:
    candidate: Candidate
    estimated_net_resale_stars: float
    estimated_profit_stars: float
    estimated_roi_percent: float


def evaluate(candidate: Candidate, strategy: Strategy = Strategy()) -> Evaluation | None:
    """Return a candidate only when it passes every hard budget/profit guard."""
    price = candidate.asking_price_stars
    market = candidate.conservative_market_price_stars
    commission = candidate.resale_commission_permille

    if not candidate.slug or price <= 0 or market <= 0:
        return None
    if commission <= 0 or commission > 1000:
        return None
    if price > strategy.max_per_gift_stars or price > strategy.budget_stars:
        return None

    # Telegram's config value is the share the seller RECEIVES, not the fee
    # deducted. E.g. 800 permille means seller receives 80% of resale price.
    net_resale = market * commission / 1000
    profit = net_resale - price
    roi = profit / price * 100
    if profit <= 0 or roi < strategy.min_profit_percent:
        return None

    return Evaluation(candidate, net_resale, profit, roi)


def choose_candidates(
    candidates: Iterable[Candidate],
    strategy: Strategy = Strategy(),
) -> list[Evaluation]:
    """Choose up to target_gifts within the total budget; never force bad buys."""
    evaluated = [e for c in candidates if (e := evaluate(c, strategy)) is not None]
    evaluated.sort(key=lambda e: (e.estimated_profit_stars, e.estimated_roi_percent), reverse=True)

    chosen: list[Evaluation] = []
    spent = 0.0
    for evaluation in evaluated:
        price = evaluation.candidate.asking_price_stars
        if len(chosen) >= strategy.target_gifts:
            break
        if spent + price > strategy.budget_stars:
            continue
        chosen.append(evaluation)
        spent += price
    return chosen
