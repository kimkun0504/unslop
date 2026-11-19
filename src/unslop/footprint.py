import fnmatch
import json
import subprocess
from importlib import resources
from pathlib import Path
from typing import cast

from unslop import gitops

REPOSITORY = "kimkun0504/unslop"
MARKETPLACE = "unslop"
PLUGIN = f"unslop@{MARKETPLACE}"
SETTINGS = Path(".claude/settings.json")
WORKFLOW = Path(".github/workflows/unslop.yml")
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
ALWAYS = ("unslop.toml", ".unslop", ".claude", ".github", "CLAUDE.md", "AGENTS.md")
PROTECTED = (
    "CODEOWNERS",
    "package.json",
    "*/package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    ".npmrc",
    "tsconfig*.json",
    "*/tsconfig*.json",
    "eslint.config.*",
    ".eslintrc*",
    ".dependency-cruiser.*",
    "knip.*",
    "stryker.config.*",
    "vitest.config.*",
    "vite.config.*",
    "jest.config.*",
    ".prettierrc*",
    ".prettierignore",
    "playwright.config.*",
    "build.gradle",
    "build.gradle.kts",
    "*/build.gradle",
    "*/build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "gradle.properties",
    "gradlew",
    "gradlew.bat",
    "gradle/*",
    "pom.xml",
    "*/pom.xml",
    "mvnw",
    "go.mod",
    "*/go.mod",
    "go.sum",
    "*/go.sum",
    ".golangci.y*ml",
    "pyproject.toml",
    "*/pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "setup.cfg",
    "ruff.toml",
    ".python-version",
    "*.csproj",
    "*.sln",
    "*.slnx",
    "Directory.Build.props",
    "Directory.Packages.props",
    "Directory.Build.targets",
    "global.json",
    ".editorconfig",
    "packages.lock.json",
    "*/packages.lock.json",
    ".config/dotnet-tools.json",
    "composer.json",
    "composer.lock",
    "phpstan.neon",
    "phpstan.neon.dist",
    "phpunit.xml",
    "phpunit.xml.dist",
    ".node-version",
    ".nvmrc",
    "Package.swift",
    "Package.resolved",
    ".swift-version",
    ".swiftlint.yml",
    ".swift-format",
    "mix.exs",
    "mix.lock",
    ".credo.exs",
    ".formatter.exs",
    ".tool-versions",
    "Gemfile",
    "Gemfile.lock",
    ".ruby-version",
    ".rubocop.yml",
    ".rubocop_todo.yml",
    ".rspec",
    "Cargo.toml",
    "*/Cargo.toml",
    "Cargo.lock",
    "clippy.toml",
    "*/clippy.toml",
    "deny.toml",
    "rust-toolchain.toml",
    "rustfmt.toml",
    "versions.tf",
    "*/versions.tf",
    ".tflint.hcl",
    ".terraform.lock.hcl",
    "mise.toml",
    "renovate.json",
    "Dockerfile",
    "*/Dockerfile",
)


def protected_files() -> list[str]:
    return sorted(
        path for path in gitops.tracked_and_untracked() if any(fnmatch.fnmatchcase(path, p) for p in PROTECTED)
    )


def deny_rules() -> tuple[list[str], list[str]]:
    files = protected_files()
    edits = [
        f"Edit({name}/**)" if not Path(name).suffix and name.startswith(".") else f"Edit({name})" for name in ALWAYS
    ]
    edits += [f"Edit({path})" for path in files]
    writes = [f"./{name}" for name in ALWAYS] + [f"./{path}" for path in files]
    return edits, writes


def merged(existing: list[object], extra: list[str]) -> list[str]:
    values = [str(item) for item in existing]
    return values + [item for item in extra if item not in values]


def settings(version: str) -> dict[str, object]:
    current: dict[str, object] = {}
    if SETTINGS.is_file():
        loaded: object = json.loads(SETTINGS.read_text())
        current = cast("dict[str, object]", loaded) if isinstance(loaded, dict) else {}
    edits, writes = deny_rules()
    marketplaces = cast("dict[str, object]", current.get("extraKnownMarketplaces") or {})
    marketplaces[MARKETPLACE] = {"source": {"source": "github", "repo": REPOSITORY, "ref": f"v{version}"}}
    plugins = cast("dict[str, object]", current.get("enabledPlugins") or {})
    plugins[PLUGIN] = True
    permissions = cast("dict[str, object]", current.get("permissions") or {})
    permissions["deny"] = merged(cast("list[object]", permissions.get("deny") or []), edits)
    sandbox = cast("dict[str, object]", current.get("sandbox") or {})
    filesystem = cast("dict[str, object]", sandbox.get("filesystem") or {})
    filesystem["denyWrite"] = merged(cast("list[object]", filesystem.get("denyWrite") or []), writes)
    sandbox["filesystem"] = filesystem
    return {
        **current,
        "extraKnownMarketplaces": marketplaces,
        "enabledPlugins": plugins,
        "permissions": permissions,
        "sandbox": sandbox,
    }


def write_settings(version: str) -> None:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    _ = SETTINGS.write_text(json.dumps(settings(version), indent=2) + "\n")


def action_ref(version: str) -> str:
    tag = f"v{version}"
    result = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{REPOSITORY}", f"refs/tags/{tag}^{{}}", f"refs/tags/{tag}"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    shas = [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
    return shas[0] if result.returncode == 0 and shas else tag


def default_branch() -> str:
    head = gitops.git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD", check=False).strip()
    if head.startswith("origin/"):
        return head.removeprefix("origin/")
    return gitops.git("branch", "--show-current", check=False).strip() or "main"


SWIFT_IMAGE = "swift:6.4.2-noble"


def workflow(version: str, profile: str) -> str:
    ref = action_ref(version)
    container = [f"    container: {SWIFT_IMAGE}"] if profile == "swift" else []
    prepare = ["      - run: apt-get update -qq && apt-get install -y -qq git curl > /dev/null"] if container else []
    return "\n".join(
        [
            "name: unslop",
            "on:",
            "  pull_request:",
            "  push:",
            f"    branches: [{default_branch()}]",
            "permissions:",
            "  contents: read",
            "concurrency:",
            "  group: unslop-${{ github.ref }}",
            "  cancel-in-progress: true",
            "jobs:",
            "  unslop:",
            "    runs-on: ubuntu-24.04",
            "    timeout-minutes: 30",
            *container,
            "    steps:",
            *prepare,
            f"      - uses: {CHECKOUT}",
            "        with:",
            "          fetch-depth: 0",
            "          persist-credentials: false",
            f"      - uses: {REPOSITORY}@{ref}",
            "",
        ]
    )


def write_workflow(version: str, profile: str) -> None:
    WORKFLOW.parent.mkdir(parents=True, exist_ok=True)
    _ = WORKFLOW.write_text(workflow(version, profile))


def ruleset() -> str:
    return (resources.files("unslop") / "data" / "ruleset.json").read_text()
