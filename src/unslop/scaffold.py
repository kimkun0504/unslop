import json
import os
import shutil
import stat
import subprocess
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

from unslop import footprint
from unslop.findings import objects, table, text

PLACEHOLDER_FILES = (
    ".github/CODEOWNERS",
    "docs/decisions/0001-no-code-comments.md",
    "docs/decisions/0002-guardrails-change-only-by-humans.md",
    "docs/decisions/0003-review-rubric.md",
    "docs/decisions/template.md",
)
SKIPPED = frozenset(
    {"__pycache__", "node_modules", ".venv", ".pytest_cache", ".ruff_cache", ".gradle", "build", "target"}
)


class ScaffoldError(Exception):
    pass


def source_root() -> Path:
    packaged = Path(str(resources.files("unslop")))
    if (packaged / "templates").is_dir():
        return packaged
    checkout = packaged.parents[1]
    if (checkout / "templates").is_dir():
        return checkout
    message = "this unslop install has no templates"
    raise ScaffoldError(message)


def catalog() -> dict[str, object]:
    return table(json.loads((source_root() / "templates" / "catalog.json").read_text()))


def template_names() -> list[str]:
    return sorted(text(item.get("name")) for item in objects(catalog().get("templates")))


def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in SKIPPED}


def owner_handle() -> str:
    if handle := os.environ.get("UNSLOP_OWNER", ""):
        return handle
    if shutil.which("gh"):
        result = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return subprocess.run(
        ["git", "config", "--get", "github.user"], capture_output=True, text=True, check=False
    ).stdout.strip()


def owner_name(handle: str) -> str:
    configured = subprocess.run(["git", "config", "--get", "user.name"], capture_output=True, text=True, check=False)
    return os.environ.get("UNSLOP_OWNER_NAME") or configured.stdout.strip() or handle or "the repository owner"


def personalize(target: Path) -> list[str]:
    handle = owner_handle()
    replacements = {
        "UNSLOP_DATE": datetime.now(UTC).date().isoformat(),
        "UNSLOP_OWNER_NAME": owner_name(handle),
    }
    if handle:
        replacements["UNSLOP_OWNER_HANDLE"] = handle
    for name in PLACEHOLDER_FILES:
        path = target / name
        if not path.is_file():
            continue
        content = path.read_text()
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        _ = path.write_text(content)
    return [] if handle else ["no GitHub handle found; set UNSLOP_OWNER or edit .github/CODEOWNERS"]


def enable_plugin(target: Path, version: str) -> None:
    path = target / ".claude" / "settings.json"
    current = table(json.loads(path.read_text())) if path.is_file() else {}
    marketplaces = table(current.get("extraKnownMarketplaces"))
    marketplaces[footprint.MARKETPLACE] = {
        "source": {"source": "github", "repo": footprint.REPOSITORY, "ref": f"v{version}"}
    }
    plugins = table(current.get("enabledPlugins"))
    plugins[footprint.PLUGIN] = True
    current["extraKnownMarketplaces"] = marketplaces
    current["enabledPlugins"] = plugins
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(current, indent=2) + "\n")


def make_executable(folder: Path) -> None:
    for script in (path for path in folder.glob("*") if path.is_file()):
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def git(target: Path, *arguments: str) -> None:
    _ = subprocess.run(["git", "-C", str(target), *arguments], check=True, capture_output=True)


def new_project(template: str, target: Path, version: str) -> list[str]:
    if template not in template_names():
        message = f"unknown template {template}; choose one of {', '.join(template_names())}"
        raise ScaffoldError(message)
    if target.exists() and any(target.iterdir()):
        message = f"{target} exists and is not empty"
        raise ScaffoldError(message)
    root = source_root()
    _ = shutil.copytree(root / "common", target, dirs_exist_ok=True, ignore=ignore)
    _ = shutil.copytree(root / "templates" / template, target, dirs_exist_ok=True, ignore=ignore)
    for folder in ("scripts", "bin"):
        make_executable(target / folder)
    warnings = personalize(target)
    enable_plugin(target, version)
    git(target, "init", "-q", "-b", "main")
    git(target, "add", "-A")
    git(target, "commit", "-q", "-m", f"Scaffold from unslop {template} template")
    return warnings


def listing() -> str:
    lines: list[str] = []
    for item in objects(catalog().get("templates")):
        lines.append(f"{text(item.get('name'))}\t{text(item.get('title'))}\tadopt: {text(item.get('adopt'), 'none')}")
        gates = table(item.get("gates"))
        lines += [f"    {key}: {value}" for key, value in gates.items()]
        lines.append("")
    profiles = [text(item.get("name")) for item in objects(catalog().get("adopt"))]
    lines.append(f"profiles for existing repositories (unslop init --profile): {' '.join(profiles)}")
    return "\n".join(lines)
