import fnmatch
import json
import shlex
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

from unslop import findings, gitops
from unslop.findings import Finding
from unslop.profiles import Check, FormatRule, Tests

GUARD_PATHS = (".unslop/*", "tools/guard/*", "scripts/*")


class BrokenCheckError(Exception):
    def __init__(self, name: str, problem: str) -> None:
        super().__init__(f"{name}: {problem}; fix the command instead of trusting an empty result")


def shell(command: str) -> subprocess.CompletedProcess[str]:
    print(f"$ {command}", flush=True)
    return subprocess.run(["bash", "-c", command], capture_output=True, text=True, check=False)


def collect(check: Check, prefix: str = ".") -> list[Finding]:
    report = Path(check["report"])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    result = shell(check["run"])
    if not report.is_file():
        _ = sys.stderr.write(result.stdout + result.stderr)
        raise BrokenCheckError(check["name"], f"the command wrote no report to {report}")
    content = findings.TERMINAL_CODES.sub("", report.read_text())
    if not content.strip() and result.returncode != 0 and result.stderr.strip():
        _ = sys.stderr.write(result.stderr[-4000:])
        raise BrokenCheckError(
            check["name"], f"the command failed with exit code {result.returncode} and an empty report"
        )
    try:
        found = list(findings.PARSERS[check["format"]](content))
    except (json.JSONDecodeError, ValueError) as error:
        _ = sys.stderr.write(result.stderr[-4000:])
        raise BrokenCheckError(check["name"], f"{report} is not valid JSON") from error
    return [within(prefix, finding) for finding in found]


def within(prefix: str, finding: Finding) -> Finding:
    if prefix == "." or Path(finding.path).is_absolute():
        return finding
    return replace(finding, path=f"{prefix}/{finding.path}")


def scoped(check: Check, files: list[str]) -> Check:
    spaced = " ".join(shlex.quote(path) for path in files)
    joined = shlex.quote(",".join(files))
    command = check.get("scoped", check["run"]).replace("{files_csv}", joined).replace("{files}", spaced)
    return {**check, "run": command}


def local_files(changed: list[str], prefix: str) -> list[tuple[str, str]]:
    if prefix == ".":
        return [(path, path) for path in changed]
    lead = f"{prefix}/"
    return [(path, path.removeprefix(lead)) for path in changed if path.startswith(lead)]


def counts(found: list[Finding]) -> dict[str, int]:
    return dict(sorted(Counter(f"{finding.path}::{finding.rule}" for finding in found).items()))


def on_touched_line(finding: Finding, touched: "Touched") -> bool:
    if finding.path not in touched:
        return False
    rows = touched[finding.path]
    return rows is None or finding.line in rows


type Touched = dict[str, frozenset[int] | None]


def report_growth(name: str, key: str, found: list[Finding], allowed: int, touched: Touched) -> None:
    path, rule = key.split("::", 1)
    matching = [finding for finding in found if finding.path == path and finding.rule == rule]
    print(f"{name}: {path} has {len(matching)} [{rule}] findings; the baseline allows {allowed}")
    fresh = [finding for finding in matching if on_touched_line(finding, touched)]
    if not fresh:
        print("\n".join(finding.render() for finding in matching))
        return
    print("  on lines this change touches:")
    print("\n".join("  " + finding.render() for finding in fresh))
    rest = [finding for finding in matching if finding not in fresh]
    if rest:
        print("  elsewhere in the file:")
        print("\n".join("  " + finding.render() for finding in rest))


def ratchet(
    name: str,
    found: list[Finding],
    recorded: dict[str, int],
    touched: dict[str, frozenset[int] | None],
    scope: set[str] | None = None,
) -> bool:
    if scope is not None:
        recorded = {key: amount for key, amount in recorded.items() if key.split("::", 1)[0] in scope}
    current = counts(found)
    grown = [key for key, amount in current.items() if amount > recorded.get(key, 0)]
    shrunk = sum(amount - current.get(key, 0) for key, amount in recorded.items() if current.get(key, 0) < amount)
    for key in grown:
        report_growth(name, key, found, recorded.get(key, 0), touched)
    if shrunk:
        print(f"{name}: {shrunk} recorded findings are fixed; a human can lock that in with `unslop baseline`")
    if not grown:
        print(f"{name}: no new findings ({len(found)} in the baseline remain)")
    return not grown


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern) for pattern in patterns)


def reformat(rule: FormatRule, path: str, content: bytes) -> bytes | None:
    command = rule["run"].replace("{path}", shlex.quote(path))
    result = subprocess.run(["bash", "-c", command], input=content, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def formatted(rule: FormatRule, since: str, files: list[tuple[str, str]]) -> bool:
    regressions: list[str] = []
    candidates = [(full, local) for full, local in files if not matches(local, list(GUARD_PATHS))]
    for full, path in ((full, local) for full, local in candidates if matches(local, rule["glob"])):
        content = Path(path).read_bytes()
        if reformat(rule, path, content) in {content, None}:
            continue
        before = gitops.show(since, full)
        if before is None:
            regressions.append(f"  {full}: new file is not formatted")
        elif reformat(rule, path, before) == before:
            regressions.append(f"  {full}: was formatted before this change and is not now")
    if regressions:
        print(f"{rule['name']}: run the formatter on these files")
        print("\n".join(regressions))
    return not regressions


def coverage_command(
    tests: Tests, reports: list[str], since: str, prefix: str = ".", threshold: int = 100
) -> list[str]:
    roots = sorted(
        {
            root
            for pattern in tests.get("src_roots", [])
            for root in (path.as_posix() for path in Path().glob(pattern))
            if Path(root).is_dir()
        }
    )
    lead = "" if prefix == "." else f"{prefix}/"
    excluded = [*GUARD_PATHS, *([f"{lead}.unslop/*"] if lead else [])]
    command = [sys.executable, "-m", "diff_cover.diff_cover_tool", *(lead + report for report in reports)]
    command += [
        "--compare-branch",
        since,
        "--fail-under",
        str(threshold),
        "--include-untracked",
        "--exclude",
        *excluded,
    ]
    return command + (["--src-roots", *(lead + root for root in roots)] if roots else [])


def run_tests(tests: Tests, since: str, prefix: str, threshold: int = 100) -> bool:
    result = shell(tests["run"])
    _ = sys.stdout.write(result.stdout[-4000:])
    if result.returncode != 0:
        _ = sys.stderr.write(result.stderr[-4000:])
        print("tests: failed")
        return False
    pattern = tests.get("coverage", "")
    if not pattern or threshold == 0:
        return True
    reports = sorted(path.as_posix() for path in Path().glob(pattern) if path.is_file())
    if not reports:
        print(f"coverage: the tests wrote no report matching {pattern}")
        return False
    command = coverage_command(tests, reports, since, prefix, threshold)
    print(f"$ diff-cover {shlex.join(command[3:])}", flush=True)
    folder = gitops.toplevel() if prefix != "." else Path.cwd()
    covered = subprocess.run(command, cwd=folder, check=False)
    if covered.returncode != 0:
        print(f"coverage: at least {threshold}% of changed lines must be covered by a test")
    return covered.returncode == 0
