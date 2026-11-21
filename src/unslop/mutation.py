import ast
import json
import os
import re
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from unslop import diffcheck, gitops
from unslop.findings import objects, table, text
from unslop.profiles import CONFIG, GUARD, Mutation
from unslop.project import OUT
from unslop.ratchet import Touched, local_files
from unslop.tools import node_version

SOURCES = {
    "stryker": ("ts", "tsx", "js", "jsx", "mts", "cts", "mjs", "cjs"),
    "mutmut": ("py",),
    "pit": ("java", "kt"),
}
UNKILLED = {
    "stryker": {"Survived", "NoCoverage"},
    "mutmut": {"survived", "no tests"},
    "pit": {"SURVIVED", "NO_COVERAGE"},
}
PIT = "1.30.2"
PIT_JUNIT5 = "1.2.3"
PACKAGE = re.compile(r"^\s*package\s+([\w.]+)", re.MULTILINE)
PIT_OUT = OUT / "pit"


class OutOfTimeError(RuntimeError):
    pass


@dataclass(slots=True)
class Budget:
    deadline: float = 0.0

    def remaining(self) -> float:
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise OutOfTimeError
        return left


BUDGET = Budget()


def timed(command: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print(f"$ {command}", flush=True)
    process = subprocess.Popen(
        ["bash", "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=BUDGET.remaining())
    except subprocess.TimeoutExpired as expired:
        os.killpg(process.pid, signal.SIGKILL)
        _ = process.communicate()
        raise OutOfTimeError from expired
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


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
        f"@stryker-mutator/core@{node_version('@stryker-mutator/core')}",
        f"@stryker-mutator/{runner}-runner@{node_version(f'@stryker-mutator/{runner}-runner')}",
        f"typescript@{installed_version('typescript')}",
        f"{runner}@{installed_version(runner)}",
    ]
    install = (
        f"npm install --silent --no-audit --no-fund --no-save --no-package-lock --prefix {tools} {' '.join(packages)}"
    )
    if timed(install).returncode != 0:
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
    result = timed(f"{tools}/node_modules/.bin/stryker run {settings}")
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
        return timed(f"{plan['runner']} {script} {arguments}", environment)

    try:
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


def class_name(path: str) -> str:
    found = PACKAGE.search(Path(path).read_text())
    stem = Path(path).stem
    return f"{found.group(1)}.{stem}" if found else stem


TOOLS_POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>unslop</groupId>
  <artifactId>pit-tools</artifactId>
  <version>1</version>
  <dependencies>
{dependencies}
  </dependencies>
</project>
"""


def maven_dependency(coordinate: str) -> str:
    group, artifact, version = coordinate.split(":")
    fields = f"<groupId>{group}</groupId><artifactId>{artifact}</artifactId><version>{version}</version>"
    return f"    <dependency>{fields}</dependency>"


def maven_classpath(build: str) -> str | None:
    deps = PIT_OUT / "deps.txt"
    command = (
        f"{build} -B -q -DskipTests test-compile dependency:build-classpath"
        f" -Dmdep.includeScope=test -Dmdep.outputFile={deps}"
    )
    if timed(command).returncode != 0 or not deps.is_file():
        return None
    entries = ["target/test-classes", "target/classes", *deps.read_text().strip().split(os.pathsep)]
    engine = next((entry for entry in entries if Path(entry).name.startswith("junit-platform-engine-")), None)
    wanted = [f"org.pitest:pitest-command-line:{PIT}", f"org.pitest:pitest-junit5-plugin:{PIT_JUNIT5}"]
    if engine is not None:
        version = Path(engine).name.removeprefix("junit-platform-engine-").removesuffix(".jar")
        wanted.append(f"org.junit.platform:junit-platform-launcher:{version}")
    tools = PIT_OUT / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    _ = (tools / "pom.xml").write_text(
        TOOLS_POM.format(dependencies="\n".join(maven_dependency(item) for item in wanted))
    )
    lib = PIT_OUT / "lib"
    copy = f"{build} -B -q -f {tools}/pom.xml dependency:copy-dependencies -DoutputDirectory={lib.resolve()}"
    if timed(copy).returncode != 0:
        return None
    present = {Path(entry).name for entry in entries}
    extra = [str(jar) for jar in sorted(lib.glob("*.jar")) if jar.name not in present]
    return os.pathsep.join([*entries, *extra])


def gradle_classpath(build: str) -> str | None:
    target = PIT_OUT / "classpath.txt"
    command = (
        f"{build} --quiet unslopPitClasspath --init-script {CONFIG}/pit.init.gradle"
        f" -PunslopPitVersion={PIT} -PunslopPitJunit5Version={PIT_JUNIT5}"
    )
    if timed(command).returncode != 0 or not target.is_file():
        return None
    return target.read_text().strip()


def pit(plan: Mutation, files: dict[str, frozenset[int] | None]) -> list[Survivor] | None:
    shutil.rmtree(PIT_OUT, ignore_errors=True)
    PIT_OUT.mkdir(parents=True)
    build = plan["runner"]
    classpath = gradle_classpath(build) if "gradle" in build else maven_classpath(build)
    if not classpath:
        print("mutation: could not build the classpath for PIT; only single-module builds are supported")
        return None
    classes = sorted({class_name(path) for path in files})
    packages = sorted({name.rsplit(".", 1)[0] + ".*" if "." in name else "*" for name in classes})
    sources = [folder for folder in ("src/main/java", "src/main/kotlin") if Path(folder).is_dir()]
    arguments = PIT_OUT / "arguments.txt"
    _ = arguments.write_text(f"-cp\n{classpath}\n")
    report = PIT_OUT / "report"
    command = (
        f"java @{arguments} org.pitest.mutationtest.commandline.MutationCoverageReport"
        f" --reportDir {report} --targetClasses {','.join(f'{name}*' for name in classes)}"
        f" --targetTests {','.join(packages)} --sourceDirs {','.join(sources)}"
        " --outputFormats XML --timestampedReports=false --verbose"
    )
    result = timed(command)
    found = report / "mutations.xml"
    if not found.is_file() or not found.read_text().strip():
        print(result.stdout[-3000:] + result.stderr[-3000:])
        print("mutation: PIT wrote no report")
        return None
    mutations = list(ET.parse(found).getroot().iter("mutation"))
    if mutations and all(mutation.get("status") == "NO_COVERAGE" for mutation in mutations):
        print(result.stdout[-6000:] + result.stderr[-3000:])
        junit = sorted({Path(entry).name for entry in classpath.split(os.pathsep) if "junit" in entry})
        print(f"JUnit on the classpath: {', '.join(junit)}")
        print("mutation: PIT ran no tests against the changed classes; check that it can find them")
        return None
    survivors: list[Survivor] = []
    for mutation in mutations:
        if mutation.get("status") not in UNKILLED["pit"]:
            continue
        owner = (mutation.findtext("mutatedClass") or "").split("$", 1)[0]
        folder = owner.rsplit(".", 1)[0].replace(".", "/") if "." in owner else ""
        source = mutation.findtext("sourceFile") or ""
        path = next((name for name in files if Path(name).as_posix().endswith(f"{folder}/{source}".lstrip("/"))), None)
        line = int(mutation.findtext("lineNumber") or 0)
        if path is not None and (files[path] is None or line in cast("frozenset[int]", files[path])):
            detail = f"{mutation.get('status')}: {mutation.findtext('description') or ''}"
            survivors.append(Survivor(path, line, detail))
    return survivors


RUNNERS = {"stryker": stryker, "mutmut": mutmut, "pit": pit}


def run(plan: Mutation, since: str, prefix: str, seconds: int = 900) -> bool:
    BUDGET.deadline = time.monotonic() + seconds
    try:
        return mutate(plan, since, prefix)
    except OutOfTimeError:
        message = f"mutation: stopped after {seconds}s with mutants left untested; a human can raise mutation_seconds"
        prefix_text = "::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else ""
        print(f"{prefix_text}{message}")
        return True


def mutate(plan: Mutation, since: str, prefix: str) -> bool:
    changed = gitops.changed_files(since)
    touched = gitops.added_lines(since)
    files = targets(plan["tool"], changed, prefix, touched)
    if not files:
        print("mutation: no changed source lines to mutate")
        return True
    survivors = RUNNERS[plan["tool"]](plan, files)
    if survivors is None:
        return False
    if survivors:
        print("mutation: these changed lines can be broken without any test failing; test what they do")
        print("\n".join(survivor.render() for survivor in survivors))
        return False
    print("mutation: every mutant on the changed lines is killed")
    return True
