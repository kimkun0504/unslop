from enum import Enum

from app.domain.money import Money


class Tier(Enum):
    STANDARD = 0
    SILVER = 5
    GOLD = 10

    @property
    def percent(self) -> int:
        return self.value


SILVER_FROM = Money(10_000)
GOLD_FROM = Money(50_000)


def tier_for(subtotal: Money) -> Tier:
    if subtotal >= GOLD_FROM:
        return Tier.GOLD
    if subtotal >= SILVER_FROM:
        return Tier.SILVER
    return Tier.STANDARD
