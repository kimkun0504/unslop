import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.money import InvalidAmountError, Money

MAX_CENTS = 10**13


@pytest.mark.parametrize(
    ("raw", "cents"),
    [("0", 0), ("12", 1200), ("12.50", 1250), (" 7.05 ", 705)],
)
def test_parse_accepts_canonical_amounts(raw: str, cents: int) -> None:
    assert Money.parse(raw) == Money(cents)


@pytest.mark.parametrize("raw", ["", "-1", "1.5", "01", "1.005", "abc", "1,00"])
def test_parse_rejects_malformed_amounts(raw: str) -> None:
    with pytest.raises(InvalidAmountError):
        _ = Money.parse(raw)


def test_negative_money_cannot_exist() -> None:
    with pytest.raises(InvalidAmountError, match="'-1'"):
        _ = Money(-1)


@given(st.integers(min_value=0, max_value=MAX_CENTS))
def test_render_then_parse_round_trips(cents: int) -> None:
    assert Money.parse(Money(cents).render()) == Money(cents)


@given(st.integers(min_value=0, max_value=MAX_CENTS), st.integers(min_value=0, max_value=100))
def test_discount_never_increases_or_goes_negative(cents: int, percent: int) -> None:
    discounted = Money(cents).less_percent(percent)
    assert Money(0) <= discounted <= Money(cents)
