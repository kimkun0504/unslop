import re
import subprocess
from pathlib import Path

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
MARKER = "unslop.toml"


class GitError(Exception):
    pass


def git(*arguments: str, check: bool = True) -> str:
    result = subprocess.run(["git", *arguments], capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        message = f"git {' '.join(arguments)}: {result.stderr.strip()}"
        raise GitError(message)
    return result.stdout


def resolves(ref: str) -> bool:
    return subprocess.run(["git", "rev-parse", "--verify", "-q", ref], capture_output=True, check=False).returncode == 0


def has_origin() -> bool:
    return subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, check=False).returncode == 0


def diff_base(ref: str = "origin/main") -> str:
    if resolves(ref):
        merge = git("merge-base", "HEAD", ref, check=False).strip()
        if not merge:
            message = f"no merge base with {ref}; use a full clone (fetch-depth: 0)"
            raise GitError(message)
        return merge
    if ref != "origin/main" or has_origin():
        message = f"cannot resolve {ref}; use a full clone (fetch-depth: 0)"
        raise GitError(message)
    if Path(MARKER).is_file():
        adopted = git("log", "--diff-filter=A", "--format=%H", "-1", "--", MARKER, check=False).strip()
        return adopted or git("rev-parse", "HEAD").strip()
    roots = git("rev-list", "--max-parents=0", "HEAD", check=False).split()
    return roots[-1] if roots else EMPTY_TREE


def untracked() -> list[str]:
    return git("ls-files", "--others", "--exclude-standard").splitlines()


def tracked_and_untracked() -> list[str]:
    return git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()


def changed_files(since: str) -> list[str]:
    tracked = git("diff", "--name-only", "--diff-filter=ACMR", since, "--").splitlines()
    return sorted({path for path in tracked + untracked() if Path(path).is_file()})


def added_lines(since: str) -> dict[str, frozenset[int] | None]:
    added: dict[str, set[int]] = {}
    current: set[int] | None = None
    for line in git("diff", "-U0", "-M", "--no-color", "--no-ext-diff", since, "--").splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = added.setdefault(target[2:], set()) if target.startswith("b/") else None
            continue
        hunk = HUNK.match(line)
        if hunk is not None and current is not None:
            start = int(hunk.group(3))
            length = 1 if hunk.group(4) is None else int(hunk.group(4))
            current.update(range(start, start + length))
    touched: dict[str, frozenset[int] | None] = {path: frozenset(rows) for path, rows in added.items()}
    for path in untracked():
        touched[path] = None
    return touched


def show(since: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{since}:{path}"], capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def clean() -> bool:
    return not git("status", "--porcelain").strip()


def toplevel() -> Path:
    return Path(git("rev-parse", "--show-toplevel").strip())
