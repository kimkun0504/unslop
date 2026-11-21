import ast
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from unslop import diffcheck, gitops
from unslop.findings import objects, table, text
from unslop.profiles import GUARD, Mutation
from unslop.project import OUT
from unslop.ratchet import Touched, local_files, shell

STRYKER = "10.1.1"
SOURCES = {"stryker": ("ts", "tsx", "js", "jsx", "mts", "cts", "mjs", "cjs"), "mutmut": ("py",)}
UNKILLED = {"stryker": {"Survived", "NoCoverage"}, "mutmut": {"survived", "no tests"}}
RESULT = re.compile(r"^\s*(?P<name>\S+): (?P<status>.+?)\s*$")
FUNCTION = re.compile(r"\.x(?:_(?P<function>[^.ǁ]+)|ǁ(?P<cls>[^ǁ]+)ǁ(?P<method>[^.]+?))__mutmut_\d+$")
HUNK = re.compile(r"^@@ -(\d+)")


@dataclass(frozen=True, slots=True)
class Survivor:
    path: str
    line: int
    detail: str

    def render(self) -> str:
        return f"  {self.path}:{self.line}: {self.detail}"


def ranges(rows: frozenset[int] | None, length: int) -> list[tuple[int, int]]:
    numbers = sorted(rows) if rows is not None else list(range(1, length + 1))
    spans: list[tuple[int, int]] = []
    for number in numbers:
        if spans and number == spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], number)
        else:
            spans.append((number, number))
    return spans


def targets(tool: str, changed: list[str], prefix: str, touched: Touched) -> dict[str, frozenset[int] | None]:
    chosen: dict[str, frozenset[int] | None] = {}
    for full, local in local_files(changed, prefix):
        if local.rsplit(".", 1)[-1] in SOURCES[tool] and not diffcheck.is_test(local) and full in touched:
            chosen[local] = touched[full]
    return chosen


def installed_version(package: str) -> str:
    manifest = Path("node_modules") / package / "package.json"
    loaded: object = json.loads(manifest.read_text()) if manifest.is_file() else {}
    return text(table(loaded).get("version"), "latest")


def stryker(plan: Mutation, files: dict[str, frozenset[int] | None]) -> list[Survivor] | None:
    tools = OUT / "tools"
    runner = plan["runner"]
    packages = [
        f"@stryker-mutator/core@{STRYKER}",
        f"@stryker-mutator/{runner}-runner@{STRYKER}",
        f"typescript@{installed_version('typescript')}",
        f"{runner}@{installed_version(runner)}",
    ]
    install = (
        f"npm install --silent --no-audit --no-fund --no-save --no-package-lock --prefix {tools} {' '.join(packages)}"
    )
    if shell(install).returncode != 0:
        print("mutation: could not install Stryker")
        return None
    mutate = [
        f"{path}:{start}-{end}"
        for path, rows in files.items()
        for start, end in ranges(rows, len(Path(path).read_text().splitlines()))
    ]
    report = OUT / "mutation.json"
    report.unlink(missing_ok=True)
    config = {
        "testRunner": runner,
        "coverageAnalysis": "perTest",
        "reporters": ["json", "clear-text"],
        "jsonReporter": {"fileName": report.as_posix()},
        "tempDirName": (OUT / "stryker-tmp").as_posix(),
        "cleanTempDir": "always",
        "ignorePatterns": [".unslop"],
        "mutate": mutate,
    }
    settings = OUT / "stryker.json"
    _ = settings.write_text(json.dumps(config, indent=2))
    result = shell(f"{tools}/node_modules/.bin/stryker run {settings}")
    if not report.is_file():
        print(result.stdout[-3000:] + result.stderr[-3000:])
        print("mutation: Stryker wrote no report")
        return None
    loaded: object = json.loads(report.read_text())
    survivors: list[Survivor] = []
    for path, entry in table(table(loaded).get("files")).items():
        for mutant in objects(table(entry).get("mutants")):
            if text(mutant.get("status")) in UNKILLED["stryker"]:
                line = table(table(mutant.get("location")).get("start")).get("line")
                change = f"{text(mutant.get('mutatorName'))} -> {text(mutant.get('replacement'))}"
                detail = f"{text(mutant.get('status'))}: {change}"
                survivors.append(Survivor(path, line if isinstance(line, int) else 0, detail))
    return survivors


def source_roots(files: dict[str, frozenset[int] | None]) -> list[str]:
    if Path("src").is_dir():
        return ["src"]
    return sorted({Path(path).parts[0] for path in files if len(Path(path).parts) > 1} or {"."})


def definition(path: Path, match: re.Match[str]) -> int | None:
    tree = ast.parse(path.read_text())
    function, owner, method = match["function"], match["cls"], match["method"]
    for node in tree.body:
        if function and isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function:
            return node.lineno
        if owner and isinstance(node, ast.ClassDef) and node.name == owner:
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and child.name == method:
                    return child.lineno
    return None


def changed_line(diff: str) -> int:
    offset = 0
    for line in diff.splitlines():
        hunk = HUNK.match(line)
        if hunk is not None:
            offset = int(hunk.group(1))
            continue
        if line.startswith("-") and not line.startswith("---"):
            return offset
        if offset and line.startswith(" "):
            offset += 1
    return offset


def locate(name: str, files: dict[str, frozenset[int] | None], roots: list[str]) -> tuple[str, re.Match[str]] | None:
    match = FUNCTION.search(name)
    if match is None:
        return None
    module = name[: match.start()].replace(".", "/") + ".py"
    for path in files:
        if any(Path(root, module).as_posix() == Path(path).as_posix() for root in roots) or path == module:
            return path, match
    return None


def mutmut(plan: Mutation, files: dict[str, frozenset[int] | None]) -> list[Survivor] | None:
    if Path("mutants").exists():
        print("mutation: a mutants/ folder already exists; remove it so mutmut starts clean")
        return None
    roots = source_roots(files)
    settings = {"source_paths": roots, "only_mutate": sorted(files)}
    environment = {**os.environ, "UNSLOP_MUTMUT": json.dumps(settings)}
    script = f"{GUARD}/mutmut_run.py"

    def mutmut_command(arguments: str) -> subprocess.CompletedProcess[str]:
        command = f"{plan['runner']} {script} {arguments}"
        return subprocess.run(["bash", "-c", command], capture_output=True, text=True, env=environment, check=False)

    try:
        print(f"$ mutmut run (only {', '.join(sorted(files))})", flush=True)
        ran = mutmut_command("run")
        if ran.returncode != 0:
            print(ran.stdout[-3000:] + ran.stderr[-3000:])
            print("mutation: mutmut failed")
            return None
        survivors: list[Survivor] = []
        for row in mutmut_command("results").stdout.splitlines():
            found = RESULT.match(row)
            if found is None or found["status"] not in UNKILLED["mutmut"]:
                continue
            located = locate(found["name"], files, roots)
            if located is None:
                continue
            path, match = located
            start = definition(Path(path), match)
            if start is None:
                continue
            diff = mutmut_command(f"show {found['name']}").stdout
            line = start + changed_line(diff) - 1
            rows = files[path]
            if rows is None or line in rows:
                edits = [row.strip() for row in diff.splitlines() if row.startswith(("+", "-"))]
                shown = " / ".join(row for row in edits if not row.startswith(("+++", "---")))
                survivors.append(Survivor(path, line, f"{found['status']}: {shown[:200]}"))
        return survivors
    finally:
        shutil.rmtree("mutants", ignore_errors=True)


def run(plan: Mutation, since: str, prefix: str) -> bool:
    changed = gitops.changed_files(since)
    touched = gitops.added_lines(since)
    files = targets(plan["tool"], changed, prefix, touched)
    if not files:
        print("mutation: no changed source lines to mutate")
        return True
    survivors = stryker(plan, files) if plan["tool"] == "stryker" else mutmut(plan, files)
    if survivors is None:
        return False
    if survivors:
        print("mutation: these changed lines can be broken without any test failing; test what they do")
        print("\n".join(survivor.render() for survivor in survivors))
        return False
    print("mutation: every mutant on the changed lines is killed")
    return True
