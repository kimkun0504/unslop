import json
import os
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

from unslop.findings import objects, table, text

EXAMPLES = 3


def log_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local/state")
    return Path(base) / "unslop" / "events.jsonl"


def read(days: int, repository: str | None) -> list[dict[str, object]]:
    path = log_path()
    if not path.is_file():
        return []
    since = time.time() - days * 86400
    entries: list[dict[str, object]] = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            entry = table(json.loads(line))
        except json.JSONDecodeError:
            continue
        stamp = entry.get("time")
        if not isinstance(stamp, int | float) or stamp < since:
            continue
        if repository is None or entry.get("repo") == repository:
            entries.append(entry)
    return entries


def summary(days: int, repository: str | None) -> str:
    entries = read(days, repository)
    scope = "all repositories" if repository is None else repository
    if not entries:
        return f"no blocks in the last {days} days in {scope} (log: {log_path()})"
    rules = Counter(f"{text(entry.get('hook'))}: {text(entry.get('rule'))}" for entry in entries)
    examples: dict[str, list[str]] = defaultdict(list)
    for entry in reversed(entries):
        key = f"{text(entry.get('hook'))}: {text(entry.get('rule'))}"
        detail = text(entry.get("detail"))
        if detail and len(examples[key]) < EXAMPLES:
            stamp = entry.get("time")
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(stamp)) if isinstance(stamp, int | float) else "?"
            examples[key].append(f"    {when}  {detail[:160]}")
    sessions = len({text(entry.get("session")) for entry in entries})
    lines = [f"{len(entries)} blocks in {sessions} sessions over the last {days} days in {scope}", ""]
    for key, count in rules.most_common():
        lines.append(f"{count:>5}  {key}")
        lines += examples[key]
    lines += ["", "For each rule, decide whether the blocks caught real slop or got in the way."]
    return "\n".join(lines)


def label_summary(limit: int) -> str:
    gh = shutil.which("gh")
    if gh is None:
        return "label use: install the GitHub CLI (gh) to count review labels on merged pull requests"
    command = [gh, "pr", "list", "--state", "merged", "--limit", str(limit), "--json", "number,labels"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return f"label use: gh could not list pull requests: {result.stderr.strip()[:200]}"
    pulls = objects(json.loads(result.stdout or "[]"))
    if not pulls:
        return "label use: no merged pull requests yet"
    lines = [f"label use on the last {len(pulls)} merged pull requests:"]
    for label in ("unslop-reviewed", "tests-reviewed"):
        count = sum(1 for pull in pulls if label in {text(item.get("name")) for item in objects(pull.get("labels"))})
        lines.append(f"  {label}: {count} ({count * 100 // len(pulls)}%)")
    lines.append("  A label on most pull requests means reviews are becoming a formality.")
    return "\n".join(lines)
