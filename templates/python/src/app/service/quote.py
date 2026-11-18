from collections.abc import Iterable
from dataclasses import dataclass
from functools import reduce

from app.domain.discount import Tier, tier_for
from app.domain.money import ZERO, Money


@dataclass(frozen=True, slots=True)
class Quote:
    subtotal: Money
    tier: Tier
    total: Money


def quote(line_amounts: Iterable[str]) -> Quote:
    subtotal = reduce(Money.__add__, (Money.parse(raw) for raw in line_amounts), ZERO)
    tier = tier_for(subtotal)
    return Quote(subtotal=subtotal, tier=tier, total=subtotal.less_percent(tier.percent))
