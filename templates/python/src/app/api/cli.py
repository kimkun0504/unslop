import sys
from collections.abc import Sequence
from typing import TextIO

from app.domain.money import InvalidAmountError
from app.service.quote import quote

EXIT_OK = 0
EXIT_USAGE = 2


def main(argv: Sequence[str], out: TextIO, err: TextIO) -> int:
    if not argv:
        _ = err.write("usage: app AMOUNT [AMOUNT ...]\n")
        return EXIT_USAGE
    try:
        result = quote(argv)
    except InvalidAmountError as error:
        _ = err.write(f"{error}\n")
        return EXIT_USAGE
    subtotal, total = result.subtotal.render(), result.total.render()
    _ = out.write(f"subtotal={subtotal} tier={result.tier.name} total={total}\n")
    return EXIT_OK


def run() -> int:
    return main(sys.argv[1:], sys.stdout, sys.stderr)
