import pytest

from app.domain.discount import Tier
from app.domain.money import Money
from app.service.quote import quote


@pytest.mark.parametrize(
    ("lines", "tier", "total"),
    [
        ([], Tier.STANDARD, Money(0)),
        (["99.99"], Tier.STANDARD, Money(9999)),
        (["60", "40"], Tier.SILVER, Money(9500)),
        (["500"], Tier.GOLD, Money(45000)),
        (["499.99"], Tier.SILVER, Money(47499)),
    ],
)
def test_quote_applies_the_tier_for_the_subtotal(
    lines: list[str], tier: Tier, total: Money
) -> None:
    result = quote(lines)
    assert (result.tier, result.total) == (tier, total)
