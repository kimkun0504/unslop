import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

from unslop import gitops

SUPPRESSIONS = (
    r"\.(skip|only|todo|fixme)[.(A-Z]",
    r"(^|[^A-Za-z0-9_.])x(it|describe|test)\(",
    r"@ts-(ignore|expect-error|nocheck)",
    r"eslint-disable",
    r"prettier-ignore",
    r"biome-ignore",
    r"(istanbul|c8|v8) ignore",
    r"@Disabled",
    r"@Ignore([^A-Za-z]|$)",
    r"@Suppress(Warnings|FBWarnings)?\(",
    r"ktlint-disable",
    r"NOPMD",
    r"CHECKSTYLE:OFF",
    r"pytest\.(mark\.)?(skip|xfail)",
    r"unittest\.skip",
    r"noqa",
    r"type: *ignore",
    r"pyright: *ignore",
    r"pragma: *no cover",
    r"pragma: *no mutate",
    r"Stryker disable",
    r"atlas:nolint",
    r"squawk-ignore",
)
SUPPRESSION = re.compile("|".join(SUPPRESSIONS))
CODE = ("ts", "tsx", "js", "jsx", "mjs", "cjs", "mts", "cts", "py", "pyi", "kt", "kts", "java", "sql")
EXCLUDED = ("scripts/", "tools/guard/", ".unslop/", "eslint-rules/")
TESTS = (
    "*.test.*",
    "*.spec.*",
    "test_*.py",
    "*_test.py",
    "src/test/*",
    "*/src/test/*",
    "*/__snapshots__/*",
    "tests/*",
    "*/tests/*",
    "test/*",
    "*/test/*",
)
IMPORT_PREFIXES = (
    "import ",
    "from [^ ]+ import ",
    r"require[ (]",
)
IMPORT = re.compile(r"^[ \t]*$|^[ \t]*(" + "|".join(IMPORT_PREFIXES) + ")")


@dataclass(frozen=True, slots=True)
class Problem:
    kind: str
    detail: str


def is_code(path: str) -> bool:
    return path.rsplit(".", 1)[-1] in CODE and not path.startswith(EXCLUDED)


def is_test(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in TESTS)


def added_code_lines(since: str) -> list[str]:
    hits: list[str] = []
    current: str | None = None
    for line in gitops.git("diff", since, "-U0", "--no-color", "--no-ext-diff", "--").splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = target[2:] if target.startswith("b/") and is_code(target[2:]) else None
        elif current is not None and line.startswith("+"):
            hits.append(f"{current}: {line[1:]}")
    for path in gitops.untracked():
        if is_code(path) and Path(path).is_file():
            hits.extend(f"{path}: {line}" for line in Path(path).read_text(errors="replace").splitlines())
    return hits


def suppressions(since: str) -> list[Problem]:
    return [Problem("suppression", hit) for hit in added_code_lines(since) if SUPPRESSION.search(hit.split(": ", 1)[1])]


def appended_only(since: str, path: str) -> bool:
    before = gitops.show(since, path)
    end = 0 if before is None else len(before.splitlines())
    inserting = False
    for line in gitops.git("diff", "-U0", "--no-color", "--no-renames", since, "--", path).splitlines():
        hunk = gitops.HUNK.match(line)
        if hunk is not None:
            if hunk.group(2) != "0":
                return False
            inserting = int(hunk.group(1)) != end
        elif line.startswith(("+++ ", "--- ")):
            continue
        elif line.startswith("+") and inserting and not IMPORT.match(line[1:]):
            return False
    return True


def tampered_tests(since: str) -> list[Problem]:
    deleted = gitops.git("diff", "--name-only", "--no-renames", "--diff-filter=D", since, "--").splitlines()
    modified = gitops.git("diff", "--name-only", "--no-renames", "--diff-filter=M", since, "--").splitlines()
    problems = [Problem("test deleted", path) for path in deleted if is_test(path)]
    problems += [
        Problem("test modified", path) for path in modified if is_test(path) and not appended_only(since, path)
    ]
    return problems
