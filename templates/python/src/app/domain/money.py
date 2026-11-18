import re
from dataclasses import dataclass
from typing import Self

AMOUNT = re.compile(r"(?P<units>0|[1-9][0-9]{0,11})(?:\.(?P<cents>[0-9]{2}))?")
CENTS_PER_UNIT = 100


class InvalidAmountError(ValueError):
    def __init__(self, raw: str) -> None:
        super().__init__(f"expected a non-negative amount like 12 or 12.50, got {raw!r}")


@dataclass(frozen=True, slots=True, order=True)
class Money:
    cents: int

    def __post_init__(self) -> None:
        if self.cents < 0:
            raise InvalidAmountError(str(self.cents))

    @classmethod
    def parse(cls, raw: str) -> Self:
        match = AMOUNT.fullmatch(raw.strip())
        if match is None:
            raise InvalidAmountError(raw)
        units = int(match["units"])
        cents = int(match["cents"] or "0")
        return cls(units * CENTS_PER_UNIT + cents)

    def __add__(self, other: Self) -> Self:
        return type(self)(self.cents + other.cents)

    def less_percent(self, percent: int) -> Self:
        return type(self)(self.cents * (100 - percent) // 100)

    def render(self) -> str:
        units, cents = divmod(self.cents, CENTS_PER_UNIT)
        return f"{units}.{cents:02d}"


ZERO = Money(0)
