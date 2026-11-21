import fnmatch
import json
import re
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
ALWAYS_FILES = (
    "unslop.toml",
    "CLAUDE.md",
    "AGENTS.md",
    ".mcp.json",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/CLAUDE.md",
)
ALWAYS_FOLDERS = (
    ".unslop",
    ".github",
    ".claude/rules",
    ".claude/skills",
    ".claude/commands",
    ".claude/agents",
    ".claude/output-styles",
    ".claude/workflows",
    ".claude/hooks",
)
PROTECTED = (
    "CODEOWNERS",
    ".npmrc",
    "tsconfig*.json",
    "*/tsconfig*.json",
    "eslint.config.*",
    ".eslintrc*",
    ".dependency-cruiser.*",
    "knip.*",
    ".jscpd.json",
    "stryker.config.*",
    "vitest.config.*",
    "vite.config.*",
    "jest.config.*",
    ".prettierrc*",
    ".prettierignore",
    "playwright.config.*",
    "tailwind.config.*",
    "postcss.config.*",
    "gradle.properties",
    "gradlew",
    "gradlew.bat",
    "gradle/wrapper/*",
    "mvnw",
    ".mvn/*",
    "detekt.yml",
    "config/detekt/*",
    "setup.cfg",
    "ruff.toml",
    ".ruff.toml",
    "pyrightconfig.json",
    "mypy.ini",
    "pytest.ini",
    "tox.ini",
    ".coveragerc",
    ".importlinter",
    ".python-version",
    ".node-version",
    ".nvmrc",
    ".java-version",
    ".sdkmanrc",
    ".sqlfluff",
    ".editorconfig",
    ".tool-versions",
    "mise.toml",
    "renovate.json",
    "Dockerfile",
    "*/Dockerfile",
)
DEPENDENCIES = (
    "package.json",
    "*/package.json",
    "package-lock.json",
    "*/package-lock.json",
    "yarn.lock",
    "*/yarn.lock",
    "pnpm-lock.yaml",
    "*/pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "*/pyproject.toml",
    "uv.lock",
    "*/uv.lock",
    "poetry.lock",
    "*/poetry.lock",
    "requirements*.txt",
    "*/requirements*.txt",
    "build.gradle",
    "build.gradle.kts",
    "*/build.gradle",
    "*/build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "gradle/*.versions.toml",
    "gradle.lockfile",
    "*/gradle.lockfile",
    "pom.xml",
    "*/pom.xml",
)


def matches(path: str, folders: list[str], patterns: tuple[str, ...]) -> bool:
    relative = [path] + [path.removeprefix(f"{folder}/") for folder in folders if path.startswith(f"{folder}/")]
    return any(fnmatch.fnmatchcase(candidate, pattern) for candidate in relative for pattern in patterns)


def guarded(path: str, folders: list[str]) -> bool:
    return matches(path, folders, PROTECTED)


def dependency(path: str, folders: list[str]) -> bool:
    return matches(path, folders, DEPENDENCIES)


def protected_files(folders: list[str]) -> list[str]:
    nested = [folder for folder in folders if folder != "."]
    return sorted(path for path in gitops.tracked_and_untracked() if guarded(path, nested))


def deny_rules(folders: list[str]) -> tuple[list[str], list[str]]:
    files = protected_files(folders)
    edits = [f"Edit({name})" for name in ALWAYS_FILES] + [f"Edit({name}/**)" for name in ALWAYS_FOLDERS]
    edits += [f"Edit({path})" for path in files]
    writes = [f"./{name}" for name in (*ALWAYS_FILES, *ALWAYS_FOLDERS)] + [f"./{path}" for path in files]
    return edits, writes


RETIRED = frozenset({"Edit(.claude/**)", "./.claude"})
RULE = re.compile(r"^(?:Edit\((?P<edit>[^)]+)\)|\./(?P<write>.+))$")


def retired(rule: str) -> bool:
    found = RULE.match(rule)
    path = "" if found is None else found["edit"] or found["write"] or ""
    return rule in RETIRED or (bool(path) and dependency(path, []))


def merged(existing: list[object], extra: list[str]) -> list[str]:
    values = [str(item) for item in existing if not retired(str(item))]
    return values + [item for item in extra if item not in values]


def settings(version: str, folders: list[str]) -> dict[str, object]:
    current: dict[str, object] = {}
    if SETTINGS.is_file():
        loaded: object = json.loads(SETTINGS.read_text())
        current = cast("dict[str, object]", loaded) if isinstance(loaded, dict) else {}
    edits, writes = deny_rules(folders)
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


def write_settings(version: str, folders: list[str]) -> None:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    _ = SETTINGS.write_text(json.dumps(settings(version, folders), indent=2) + "\n")


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


def workflow(version: str) -> str:
    ref = action_ref(version)
    return "\n".join(
        [
            "name: unslop",
            "on:",
            "  pull_request:",
            "    types: [opened, synchronize, reopened, labeled, unlabeled]",
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
            "    steps:",
            f"      - uses: {CHECKOUT}",
            "        with:",
            "          fetch-depth: 0",
            "          persist-credentials: false",
            f"      - uses: {REPOSITORY}@{ref}",
            "",
        ]
    )


def write_workflow(version: str) -> None:
    WORKFLOW.parent.mkdir(parents=True, exist_ok=True)
    _ = WORKFLOW.write_text(workflow(version))


def ruleset() -> str:
    return (resources.files("unslop") / "data" / "ruleset.json").read_text()
