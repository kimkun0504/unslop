import json
import re
import shutil
import stat
import subprocess
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import NotRequired, TypedDict

from unslop.findings import table
from unslop.project import OUT

RUFF = "uvx ruff@0.17.6"
VULTURE = "uvx vulture@2.16"
KNIP = "npx --yes knip@6.47.0"
UNUSED_PYTHON = (
    "git ls-files -co --exclude-standard -z '*.py' | xargs -0 -r"
    f" {VULTURE} --min-confidence 60 --ignore-decorators '@*' --ignore-names 'test_*,Test*,setUp*,tearDown*'"
    " > .unslop/out/vulture.txt; test -f .unslop/out/vulture.txt || : > .unslop/out/vulture.txt"
)
CONFIG = ".unslop/out/config"
GUARD = ".unslop/out/guard"
UP = "../../.."


class FormatRule(TypedDict):
    name: str
    glob: list[str]
    run: str


class Check(TypedDict):
    name: str
    format: str
    report: str
    run: str
    kind: NotRequired[str]


class Mutation(TypedDict):
    tool: str
    runner: str


class Tests(TypedDict):
    run: str
    coverage: NotRequired[str]
    src_roots: NotRequired[list[str]]


class Plan(TypedDict):
    stack: str
    setup: NotRequired[str]
    format: list[FormatRule]
    checks: list[Check]
    tests: NotRequired[Tests]
    mutation: NotRequired[Mutation]
    notes: list[str]


class DetectError(Exception):
    pass


def tracked(*patterns: str) -> list[str]:
    return subprocess.run(
        ["git", "ls-files", "--", *patterns], capture_output=True, text=True, check=False
    ).stdout.splitlines()


def write_config(name: str, content: str) -> str:
    target = OUT / "config" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(content)
    return f"{CONFIG}/{name}"


def install_data(profile: str) -> None:
    source = resources.files("unslop") / "data" / profile
    for sub in ("config", "guard"):
        folder = source / sub
        if not folder.is_dir():
            continue
        for item in (entry for entry in folder.iterdir() if entry.is_file()):
            target = OUT / sub / item.name
            target.parent.mkdir(parents=True, exist_ok=True)
            _ = target.write_bytes(item.read_bytes())
            if sub == "guard":
                target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def require(path: str, profile: str) -> None:
    if not Path(path).exists():
        message = f"{profile}: no {path} in {Path.cwd()}"
        raise DetectError(message)


def python(unslop: str) -> Plan:
    _ = unslop
    source = "src" if Path("src").is_dir() else "."
    coverage = f"--cov={source} --cov-config={CONFIG}/coveragerc --cov-report=xml:.unslop/out/coverage.xml"
    notes: list[str] = []
    if Path("uv.lock").is_file():
        tests, setup = f"uv run --with pytest-cov pytest -q {coverage}", "uv sync --locked"
        runner = "uv run --with mutmut==3.8.1 python"
    elif Path("poetry.lock").is_file():
        tests, setup = f"poetry run pytest -q {coverage}", "poetry install --no-interaction"
        runner = "poetry run python -m pip install -q mutmut==3.8.1 && poetry run python"
    else:
        pyproject = Path("pyproject.toml")
        dev = pyproject.is_file() and re.search(r"(?m)^dev *= *\[", pyproject.read_text()) is not None
        target = ".[dev]" if dev else "."
        tests = f".venv/bin/python -m pytest -q {coverage}"
        setup = f'uv venv --allow-existing .venv && uv pip install --python .venv -e "{target}" pytest pytest-cov'
        runner = "uv pip install -q --python .venv mutmut==3.8.1 && .venv/bin/python"
        notes.append("no uv or Poetry lockfile, so setup installs into a project .venv with uv")
    return {
        "stack": "python",
        "setup": setup,
        "format": [
            {"name": "ruff format", "glob": ["*.py", "*.pyi"], "run": f"{RUFF} format --stdin-filename {{path}} -"}
        ],
        "checks": [
            {
                "name": "ruff",
                "format": "sarif",
                "report": ".unslop/out/ruff.sarif",
                "run": f"{RUFF} check --config {CONFIG}/ruff.toml --exit-zero --output-format sarif"
                " --output-file .unslop/out/ruff.sarif .",
            },
            {
                "name": "basedpyright",
                "format": "pyright",
                "report": ".unslop/out/basedpyright.json",
                "run": f"uvx basedpyright@1.40.2 -p {CONFIG}/pyrightconfig.json --outputjson"
                " > .unslop/out/basedpyright.json",
            },
            {
                "name": "vulture",
                "kind": "dead-code",
                "format": "vulture",
                "report": ".unslop/out/vulture.txt",
                "run": UNUSED_PYTHON,
            },
        ],
        "tests": {"run": tests, "coverage": ".unslop/out/coverage.xml"},
        "mutation": {"tool": "mutmut", "runner": runner},
        "notes": notes,
    }


def package_json() -> dict[str, object]:
    require("package.json", "typescript")
    loaded: object = json.loads(Path("package.json").read_text())
    return table(loaded)


def dependencies(manifest: dict[str, object]) -> set[str]:
    names: set[str] = set()
    for key in ("dependencies", "devDependencies"):
        names.update(table(manifest.get(key)))
    return names


def typescript(unslop: str) -> Plan:
    _ = unslop
    deps = dependencies(package_json())
    if Path("pnpm-lock.yaml").is_file():
        run, setup = "pnpm exec", "corepack enable && pnpm install --frozen-lockfile"
    elif Path("yarn.lock").is_file():
        run, setup = "yarn", "corepack enable && yarn install --immutable"
    else:
        run, setup = "npx --no-install", "npm ci"
    base = "tsconfig.app.json" if Path("tsconfig.app.json").is_file() else "tsconfig.json"
    sources = "src" if Path("src").is_dir() else "."
    checks: list[Check] = []
    notes: list[str] = []
    if Path(base).is_file():
        options = {
            "noEmit": True,
            "strict": True,
            "allowUnreachableCode": False,
            "allowUnusedLabels": False,
            "exactOptionalPropertyTypes": True,
            "noFallthroughCasesInSwitch": True,
            "noImplicitOverride": True,
            "noImplicitReturns": True,
            "noPropertyAccessFromIndexSignature": True,
            "noUncheckedIndexedAccess": True,
            "noUnusedLocals": True,
            "noUnusedParameters": True,
            "skipLibCheck": True,
        }
        config = write_config(
            "tsconfig.json", json.dumps({"extends": f"{UP}/{base}", "compilerOptions": options}, indent=2)
        )
        checks.append(
            {
                "name": "tsc",
                "format": "tsc",
                "report": ".unslop/out/tsc.txt",
                "run": f"{run} tsc -p {config} --pretty false > .unslop/out/tsc.txt",
            }
        )
    if any(Path().glob("eslint.config.*")) or any(Path().glob(".eslintrc*")):
        checks.append(
            {
                "name": "eslint",
                "format": "eslint",
                "report": ".unslop/out/eslint.json",
                "run": f"{run} eslint . --format json --output-file .unslop/out/eslint.json",
            }
        )
    checks.append(
        {
            "name": "knip",
            "kind": "dead-code",
            "format": "knip",
            "report": ".unslop/out/knip.json",
            "run": f"{KNIP} --reporter json --no-exit-code --no-progress > .unslop/out/knip.json",
        }
    )
    formatting: list[FormatRule] = []
    if "prettier" in deps:
        formatting.append(
            {
                "name": "prettier",
                "glob": ["*.ts", "*.tsx", "*.js", "*.jsx", "*.mjs", "*.cjs", "*.mts", "*.cts"],
                "run": f"{run} prettier --stdin-filepath {{path}}",
            }
        )
    tests: Tests
    if "vitest" in deps and ({"@vitest/coverage-v8", "@vitest/coverage-istanbul"} & deps):
        tests = {
            "run": f"{run} vitest run --coverage.enabled --coverage.reporter=cobertura"
            f" --coverage.reportsDirectory=.unslop/out '--coverage.include={sources}/**'",
            "coverage": ".unslop/out/cobertura-coverage.xml",
        }
    elif "vitest" in deps:
        tests = {"run": f"{run} vitest run"}
        notes.append("add @vitest/coverage-v8 to turn on coverage of changed lines")
    elif "jest" in deps:
        tests = {
            "run": f"{run} jest --coverage --coverageReporters=cobertura --coverageDirectory=.unslop/out"
            f" '--collectCoverageFrom={sources}/**/*.{{ts,tsx,js,jsx}}'",
            "coverage": ".unslop/out/cobertura-coverage.xml",
        }
    else:
        tests = {"run": "npm test"}
        notes.append(
            "no vitest or jest found; coverage of changed lines is off until [commands] names a coverage report"
        )
    plan: Plan = {
        "stack": "typescript",
        "setup": setup,
        "format": formatting,
        "checks": checks,
        "tests": tests,
        "notes": notes,
    }
    runner = "vitest" if "vitest" in deps else "jest" if "jest" in deps else ""
    if runner:
        plan["mutation"] = {"tool": "stryker", "runner": runner}
    return plan


def jvm(unslop: str) -> Plan:
    gradle = Path("gradlew").is_file() or any(Path().glob("build.gradle*")) or any(Path().glob("settings.gradle*"))
    if gradle:
        build = "./gradlew" if Path("gradlew").is_file() else "gradle"
        tests = f"{build} test --init-script {CONFIG}/jacoco.init.gradle"
        coverage = "**/build/reports/jacoco/test/jacocoTestReport.xml"
    elif Path("pom.xml").is_file():
        build = "./mvnw" if Path("mvnw").is_file() else "mvn"
        jacoco = "org.jacoco:jacoco-maven-plugin:0.8.14"
        tests = f"{build} -B -q {jacoco}:prepare-agent test {jacoco}:report"
        coverage = "**/target/site/jacoco/jacoco.xml"
    else:
        message = f"jvm: no Gradle or Maven build in {Path.cwd()}"
        raise DetectError(message)
    checks: list[Check] = []
    if tracked("*.kt"):
        checks.append(
            {
                "name": "detekt",
                "format": "sarif",
                "report": ".unslop/out/detekt.sarif",
                "run": f'java -jar "$({unslop} fetch detekt)" --input . --excludes "**/build/**,**/.unslop/**"'
                " --build-upon-default-config --all-rules --report sarif:.unslop/out/detekt.sarif > /dev/null",
            }
        )
    if tracked("*.kt", "*.kts"):
        checks.append(
            {
                "name": "kotlin-guard",
                "format": "lines",
                "report": ".unslop/out/kotlin-guard.txt",
                "run": 'git ls-files -co --exclude-standard -z "*.kt" "*.kts" | xargs -0 -r uv run --quiet --no-project'
                " --python 3.13 --with tree-sitter==0.26.1 --with tree-sitter-kotlin==1.1.0 python"
                f" {GUARD}/kotlin_guard.py > .unslop/out/kotlin-guard.txt",
            }
        )
    if tracked("*.java"):
        checks.append(
            {
                "name": "pmd",
                "format": "sarif",
                "report": ".unslop/out/pmd.sarif",
                "run": f'"$({unslop} fetch pmd)" check --dir . --rulesets {CONFIG}/pmd.xml --format sarif'
                " --report-file .unslop/out/pmd.sarif --no-fail-on-violation --no-fail-on-error --no-progress",
            }
        )
    roots = ["src/main/java", "src/main/kotlin", "*/src/main/java", "*/src/main/kotlin"]
    return {
        "stack": "jvm",
        "format": [],
        "checks": checks,
        "tests": {"run": tests, "coverage": coverage, "src_roots": roots},
        "notes": [],
    }


PROFILES: dict[str, Callable[[str], Plan]] = {
    "jvm": jvm,
    "python": python,
    "typescript": typescript,
}
MARKERS: dict[str, tuple[str, ...]] = {
    "typescript": ("package.json",),
    "python": ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "uv.lock", "poetry.lock"),
    "jvm": ("pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradlew"),
}


def guess() -> list[str]:
    return [name for name, markers in MARKERS.items() if any(any(Path().glob(marker)) for marker in markers)]


def plan(profile: str, unslop: str) -> Plan:
    if profile not in PROFILES:
        message = f"unknown profile {profile}; choose one of {', '.join(sorted(PROFILES))}"
        raise DetectError(message)
    shutil.rmtree(OUT / "config", ignore_errors=True)
    install_data(profile)
    return PROFILES[profile](unslop)
