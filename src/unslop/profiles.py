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
    elif Path("poetry.lock").is_file():
        tests, setup = f"poetry run pytest -q {coverage}", "poetry install --no-interaction"
    else:
        pyproject = Path("pyproject.toml")
        dev = pyproject.is_file() and re.search(r"(?m)^dev *= *\[", pyproject.read_text()) is not None
        target = ".[dev]" if dev else "."
        tests = f".venv/bin/python -m pytest -q {coverage}"
        setup = f'uv venv --allow-existing .venv && uv pip install --python .venv -e "{target}" pytest pytest-cov'
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
        ],
        "tests": {"run": tests, "coverage": ".unslop/out/coverage.xml"},
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
    return {
        "stack": "typescript",
        "setup": setup,
        "format": formatting,
        "checks": checks,
        "tests": tests,
        "notes": notes,
    }


def go(unslop: str) -> Plan:
    _ = unslop
    require("go.mod", "go")
    return {
        "stack": "go",
        "setup": "go mod download",
        "format": [{"name": "gofmt", "glob": ["*.go"], "run": "gofmt"}],
        "checks": [
            {
                "name": "golangci-lint",
                "format": "sarif",
                "report": ".unslop/out/golangci.sarif",
                "run": "go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.15.0 run"
                f" -c {CONFIG}/golangci.yml --output.sarif.path=.unslop/out/golangci.sarif"
                " --output.text.path=stderr ./...",
            }
        ],
        "tests": {
            "run": "go test -race -covermode=atomic -coverpkg=./... -coverprofile=.unslop/out/cover.out ./..."
            " && go run github.com/boumenot/gocover-cobertura@v1.5.0"
            " < .unslop/out/cover.out > .unslop/out/coverage.xml",
            "coverage": ".unslop/out/coverage.xml",
        },
        "notes": [],
    }


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


def terraform(unslop: str) -> Plan:
    _ = unslop
    if not tracked("*.tf"):
        message = f"terraform: no .tf files in {Path.cwd()}"
        raise DetectError(message)
    config = f'"$PWD/{CONFIG}/tflint.hcl"'
    plan: Plan = {
        "stack": "terraform",
        "setup": f"tflint --init --config {config}",
        "format": [{"name": "terraform fmt", "glob": ["*.tf", "*.tfvars", "*.tftest.hcl"], "run": "terraform fmt -"}],
        "checks": [
            {
                "name": "tflint",
                "format": "sarif",
                "report": ".unslop/out/tflint.sarif",
                "run": f"tflint --recursive --config {config} --format sarif --force > .unslop/out/tflint.sarif",
            },
            {
                "name": "checkov",
                "format": "sarif",
                "report": ".unslop/out/results_sarif.sarif",
                "run": "uvx --python 3.13 checkov==3.4.6 --directory . --framework terraform --skip-path .unslop"
                " --output sarif --output-file-path .unslop/out --soft-fail --quiet > /dev/null",
            },
        ],
        "notes": [],
    }
    if tracked("*.tftest.hcl"):
        plan["tests"] = {"run": "terraform init -backend=false -input=false > /dev/null && terraform test"}
    return plan


RUST_LINTS = " ".join(
    f"-W clippy::{lint}"
    for lint in (
        "pedantic",
        "nursery",
        "unwrap_used",
        "expect_used",
        "panic",
        "todo",
        "unimplemented",
        "dbg_macro",
        "print_stdout",
        "print_stderr",
        "allow_attributes_without_reason",
    )
)


def rust(unslop: str) -> Plan:
    _ = unslop
    require("Cargo.toml", "rust")
    found = re.search(r'(?m)^ *edition *= *"(\d+)"', Path("Cargo.toml").read_text())
    edition = found.group(1) if found else "2021"
    allowed = ("unwrap", "expect", "panic", "print", "dbg")
    _ = write_config("clippy.toml", "".join(f"allow-{name}-in-tests = true\n" for name in allowed))
    return {
        "stack": "rust",
        "setup": "rustup component add clippy rustfmt llvm-tools-preview"
        " && { command -v cargo-llvm-cov > /dev/null || cargo install cargo-llvm-cov@0.9.1 --locked; } && cargo fetch",
        "format": [{"name": "rustfmt", "glob": ["*.rs"], "run": f"rustfmt --edition {edition}"}],
        "checks": [
            {
                "name": "clippy",
                "format": "cargo",
                "report": ".unslop/out/clippy.json",
                "run": f"CLIPPY_CONF_DIR={CONFIG} cargo clippy --workspace --all-targets --message-format=json"
                f" -- {RUST_LINTS} > .unslop/out/clippy.json",
            }
        ],
        "tests": {
            "run": "cargo llvm-cov --workspace --cobertura --output-path .unslop/out/coverage.xml",
            "coverage": ".unslop/out/coverage.xml",
        },
        "notes": [],
    }


def dotnet(unslop: str) -> Plan:
    _ = unslop
    candidates = sorted([*Path().glob("*.slnx"), *Path().glob("*.sln")]) or sorted(Path().glob("*.csproj"))
    if not candidates:
        message = f"dotnet: no solution or project file at the root of {Path.cwd()}"
        raise DetectError(message)
    target = candidates[0].name
    build = (
        f"dotnet build {target} --no-incremental -clp:NoSummary -v:q -p:AnalysisMode=All"
        " -p:EnforceCodeStyleInBuild=true"
        " -p:Nullable=enable -p:TreatWarningsAsErrors=false -p:WarningsAsErrors= -p:GenerateDocumentationFile=false"
    )
    return {
        "stack": "dotnet",
        "setup": f"dotnet restore {target}",
        "format": [],
        "checks": [
            {
                "name": "analyzers",
                "format": "msbuild",
                "report": ".unslop/out/build.txt",
                "run": f"{build} > .unslop/out/build.txt",
            }
        ],
        "tests": {
            "run": f'rm -rf .unslop/out/tests && dotnet test {target} --collect:"XPlat Code Coverage"'
            " --results-directory .unslop/out/tests",
            "coverage": ".unslop/out/tests/**/coverage.cobertura.xml",
        },
        "notes": [],
    }


def php(unslop: str) -> Plan:
    require("composer.json", "php")
    folders = [name for name in ("src", "app", "lib") if Path(name).is_dir()]
    if not folders:
        message = "php: no src, app or lib folder to analyse"
        raise DetectError(message)
    neon = ["parameters:", "  level: max", "  tmpDir: ../phpstan", "  paths:"]
    neon += [f"    - {UP}/{name}" for name in folders]
    neon += ["  bootstrapFiles:", f"    - {UP}/vendor/autoload.php"]
    config = write_config("phpstan.neon", "\n".join(neon) + "\n")
    plan: Plan = {
        "stack": "php",
        "setup": "composer install --no-interaction --no-progress",
        "format": [],
        "checks": [
            {
                "name": "phpstan",
                "format": "phpstan",
                "report": ".unslop/out/phpstan.json",
                "run": f'php "$({unslop} fetch phpstan)" analyse -c {config} --error-format=json --no-progress'
                " --memory-limit=1G > .unslop/out/phpstan.json",
            }
        ],
        "notes": [],
    }
    manifest: object = json.loads(Path("composer.json").read_text())
    phpunit = "phpunit/phpunit" in table(table(manifest).get("require-dev"))
    configured = Path("phpunit.xml").is_file() or Path("phpunit.xml.dist").is_file()
    if configured or phpunit or Path("vendor/bin/phpunit").is_file():
        suite = "" if configured else next((f" {name}" for name in ("tests", "test") if Path(name).is_dir()), "")
        filters = "".join(f" --coverage-filter {name}" for name in folders)
        plan["tests"] = {
            "run": f"vendor/bin/phpunit{filters} --coverage-clover .unslop/out/clover.xml{suite}",
            "coverage": ".unslop/out/clover.xml",
        }
    return plan


def in_lock(gem: str) -> bool:
    lock = Path("Gemfile.lock")
    return lock.is_file() and f"\n    {gem} (" in lock.read_text()


def ruby(unslop: str) -> Plan:
    _ = unslop
    require("Gemfile", "ruby")
    if in_lock("rubocop"):
        rubocop, setup = "bundle exec rubocop", "bundle install"
        plugins = [name for name in ("rubocop-performance", "rubocop-rspec") if in_lock(name)]
    else:
        gems = ".unslop/out/gems"
        rubocop = f"env -u BUNDLE_GEMFILE -u RUBYOPT GEM_HOME={gems} GEM_PATH={gems} {gems}/bin/rubocop"
        setup = (
            f"bundle install && gem install --no-document --install-dir {gems}"
            " rubocop:1.92.3 rubocop-performance:1.27.0 rubocop-rspec:3.10.2"
        )
        plugins = ["rubocop-performance", *(["rubocop-rspec"] if Path("spec").is_dir() else [])]
    lines = [f"inherit_from: {UP}/.rubocop.yml"] if Path(".rubocop.yml").is_file() else []
    if plugins:
        lines += ["plugins:", *(f"  - {name}" for name in plugins)]
    lines += ["AllCops:", "  NewCops: enable", "  SuggestExtensions: false", "  Exclude:"]
    lines += [f"    - {pattern}" for pattern in (".unslop/**/*", "vendor/**/*", "node_modules/**/*", "db/schema.rb")]
    for cop in ("Style/FrozenStringLiteralComment", "Style/Documentation"):
        lines += [f"{cop}:", "  Enabled: false"]
    config = write_config("rubocop.yml", "\n".join(lines) + "\n")
    coverage = f'rm -f .unslop/out/ruby-coverage-*.xml && RUBYOPT="-r./{GUARD}/ruby_coverage.rb"'
    runner = "bundle exec rspec" if Path("spec").is_dir() else "bundle exec rake test"
    return {
        "stack": "ruby",
        "setup": setup,
        "format": [
            {
                "name": "rubocop layout",
                "glob": ["*.rb", "*.rake", "Gemfile", "Rakefile"],
                "run": f"{rubocop} --config {config} --only Layout --autocorrect --stdin {{path}} --stderr"
                " --fail-level fatal --format quiet",
            }
        ],
        "checks": [
            {
                "name": "rubocop",
                "format": "rubocop",
                "report": ".unslop/out/rubocop.json",
                "run": f"{rubocop} --config {config} --format json --out .unslop/out/rubocop.json",
            }
        ],
        "tests": {"run": f"{coverage} {runner}", "coverage": ".unslop/out/ruby-coverage-*.xml"},
        "notes": [],
    }


def elixir(unslop: str) -> Plan:
    _ = unslop
    require("mix.exs", "elixir")
    checks: list[Check] = [
        {
            "name": "compiler",
            "format": "elixir",
            "report": ".unslop/out/compile.txt",
            "run": "MIX_ENV=test mix compile --force --all-warnings > .unslop/out/compile.txt 2>&1",
        }
    ]
    notes: list[str] = []
    lock = Path("mix.lock")
    if lock.is_file() and '"credo"' in lock.read_text():
        checks.append(
            {
                "name": "credo",
                "format": "credo",
                "report": ".unslop/out/credo.json",
                "run": "mix credo --strict --all --format json > .unslop/out/credo.json",
            }
        )
    else:
        notes.append("credo is not in mix.lock; only compiler warnings are ratcheted")
    return {
        "stack": "elixir",
        "setup": "mix local.hex --force --if-missing && mix local.rebar --force --if-missing && mix deps.get"
        " && MIX_ENV=test mix deps.compile",
        "format": [{"name": "mix format", "glob": ["*.ex", "*.exs"], "run": "mix format --stdin-filename {path} -"}],
        "checks": checks,
        "tests": {"run": f"{GUARD}/elixir_test", "coverage": ".unslop/out/coverage.xml"},
        "notes": notes,
    }


SWIFTLINT_RULES = (
    "force_unwrapping",
    "implicitly_unwrapped_optional",
    "fatal_error_message",
    "discouraged_optional_boolean",
    "unowned_variable_capture",
    "weak_delegate",
    "empty_count",
    "first_where",
    "contains_over_first_not_nil",
    "unused_declaration",
    "unused_import",
    "discouraged_assert",
    "discouraged_none_name",
    "private_swiftui_state",
    "unhandled_throwing_task",
    "legacy_objc_type",
    "redundant_type_annotation",
)


def swift(unslop: str) -> Plan:
    require("Package.swift", "swift")
    lines = [f"parent_config: {UP}/.swiftlint.yml"] if Path(".swiftlint.yml").is_file() else []
    lines += ["excluded:", f"  - {UP}/.build", f"  - {UP}/.unslop", "opt_in_rules:"]
    lines += [f"  - {rule}" for rule in SWIFTLINT_RULES]
    config = write_config("swiftlint.yml", "\n".join(lines) + "\n")
    formatting: list[FormatRule] = []
    notes: list[str] = []
    if Path(".swift-format").is_file():
        formatting.append({"name": "swift format", "glob": ["*.swift"], "run": "swift format --assume-filename {path}"})
    else:
        notes.append("no .swift-format in the repository, so formatting is left to the project")
    return {
        "stack": "swift",
        "setup": "swift build --build-tests",
        "format": formatting,
        "checks": [
            {
                "name": "swiftlint",
                "format": "sarif",
                "report": ".unslop/out/swiftlint.sarif",
                "run": f'"$({unslop} fetch swiftlint)" lint --config {config} --reporter sarif --quiet'
                " > .unslop/out/swiftlint.sarif",
            },
            {
                "name": "compiler",
                "format": "compiler",
                "report": ".unslop/out/build.txt",
                "run": "swift build --build-tests --scratch-path .unslop/out/build"
                " -Xswiftc -strict-concurrency=complete"
                " > .unslop/out/build.txt 2>&1",
            },
        ],
        "tests": {"run": f"{GUARD}/swift_coverage", "coverage": ".unslop/out/coverage.lcov"},
        "notes": notes,
    }


PROFILES: dict[str, Callable[[str], Plan]] = {
    "dotnet": dotnet,
    "elixir": elixir,
    "go": go,
    "jvm": jvm,
    "php": php,
    "python": python,
    "ruby": ruby,
    "rust": rust,
    "swift": swift,
    "terraform": terraform,
    "typescript": typescript,
}
MARKERS: dict[str, tuple[str, ...]] = {
    "typescript": ("package.json",),
    "python": ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "uv.lock", "poetry.lock"),
    "go": ("go.mod",),
    "rust": ("Cargo.toml",),
    "jvm": ("pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradlew"),
    "dotnet": ("*.sln", "*.slnx", "*.csproj"),
    "php": ("composer.json",),
    "ruby": ("Gemfile",),
    "elixir": ("mix.exs",),
    "swift": ("Package.swift",),
    "terraform": ("*.tf",),
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
