import json
import os
import shlex
import shutil
from pathlib import Path
from typing import cast

from unslop import diffcheck, footprint, gitops
from unslop.findings import objects, table, text
from unslop.profiles import Check
from unslop.project import OUT, Gates
from unslop.ratchet import shell

JSCPD = "npx --yes jscpd@5.4.3"
SQLFLUFF = "uvx sqlfluff@4.5.0"
DUPLICATION_FORMATS = "typescript,tsx,javascript,jsx,python,java,kotlin"
DUPLICATION_IGNORED = (
    "**/node_modules/**",
    "**/.unslop/**",
    "**/dist/**",
    "**/build/**",
    "**/target/**",
    "**/.venv/**",
    "**/migrations/**",
    "**/*.test.*",
    "**/*.spec.*",
    "**/test_*.py",
    "**/*_test.py",
    "**/tests/**",
    "**/test/**",
    "**/src/test/**",
)


def counted(path: str) -> bool:
    lock = path.endswith((".lock", "-lock.json", "-lock.yaml", ".lockfile"))
    return not lock and not path.startswith(".unslop/") and footprint.SETTINGS.as_posix() != path


def diff_lines(since: str) -> int:
    total = 0
    for row in gitops.git("diff", "--numstat", "--no-renames", since, "--").splitlines():
        added, removed, path = row.split("\t", 2)
        if added != "-" and counted(path):
            total += int(added) + int(removed)
    for path in gitops.untracked():
        if counted(path) and diffcheck.is_code(path) and Path(path).is_file():
            total += len(Path(path).read_text(errors="replace").splitlines())
    return total


def warn(message: str) -> None:
    prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else ""
    print(f"{prefix}{message}")


def diff_size(since: str, gates: Gates) -> bool:
    size = diff_lines(since)
    if gates.diff_max_lines and size > gates.diff_max_lines:
        print(f"diff size: {size} changed lines, over the limit of {gates.diff_max_lines}; split the change")
        return False
    if gates.diff_warn_lines and size > gates.diff_warn_lines:
        warn(f"diff size: {size} changed lines; reviews get worse past {gates.diff_warn_lines}, consider splitting")
    return True


def fragment(entry: object) -> str:
    place = table(entry)
    start = table(place.get("startLoc")).get("line")
    end = table(place.get("endLoc")).get("line")
    return f"{text(place.get('name'))}:{start}-{end}"


def duplication(since: str) -> bool:
    if shutil.which("npx") is None:
        print("duplication: skipped, Node.js is not installed")
        return True
    folder = OUT / "jscpd"
    shutil.rmtree(folder, ignore_errors=True)
    command = (
        f"{JSCPD} --min-tokens 50 --reporters json --output {folder} --silent --no-tips"
        f" --format {DUPLICATION_FORMATS} --ignore {shlex.quote(','.join(DUPLICATION_IGNORED))}"
        f" --baseline-from-ref {since} ."
    )
    result = shell(command)
    report = folder / "jscpd-report.json"
    if not report.is_file():
        print(result.stdout[-2000:] + result.stderr[-2000:])
        print("duplication: jscpd wrote no report")
        return False
    loaded: object = json.loads(report.read_text())
    clones = [clone for clone in objects(table(loaded).get("duplicates")) if clone.get("isNew") is True]
    if not clones:
        print("duplication: no new copy-pasted code")
        return True
    print("duplication: this change adds copy-pasted code; extract the shared part instead")
    for clone in clones:
        lines = cast("int", clone.get("lines", 0))
        print(f"  {fragment(clone.get('firstFile'))} repeats {fragment(clone.get('secondFile'))} ({lines} lines)")
    return False


def sql_check(gates: Gates) -> Check | None:
    files = [path for path in gitops.tracked_and_untracked() if path.endswith(".sql") and Path(path).is_file()]
    if gates.sql_dialect == "off" or not files:
        return None
    listing = OUT / "sql-files.txt"
    listing.parent.mkdir(parents=True, exist_ok=True)
    _ = listing.write_text("\n".join(files) + "\n")
    dialect = "" if Path(".sqlfluff").is_file() else f" --dialect {gates.sql_dialect}"
    return {
        "name": "sqlfluff",
        "format": "sqlfluff",
        "report": ".unslop/out/sqlfluff.json",
        "run": f"tr '\\n' '\\0' < {listing} | xargs -0 -r {SQLFLUFF} lint{dialect} --format json --nofail"
        " > .unslop/out/sqlfluff.json",
    }
