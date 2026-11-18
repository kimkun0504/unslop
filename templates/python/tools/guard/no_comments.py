import re
import sys
import tokenize
from pathlib import Path

HEADER = re.compile(r"^#!|^# -\*- coding[:=]")
HEADER_LINES = 2


def is_allowed(tok: tokenize.TokenInfo) -> bool:
    line = tok.start[0]
    return line <= HEADER_LINES and HEADER.match(tok.string) is not None


def violations(path: Path) -> list[str]:
    with path.open("rb") as handle:
        return [
            f"{path}:{tok.start[0]}:{tok.start[1]}: comments are forbidden (ADR-0001)"
            for tok in tokenize.tokenize(handle.readline)
            if tok.type == tokenize.COMMENT and not is_allowed(tok)
        ]


def main(argv: list[str]) -> int:
    found = [v for arg in argv if arg.endswith(".py") for v in violations(Path(arg))]
    _ = sys.stdout.write("".join(f"{v}\n" for v in found))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
