import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from unslop import __version__, footprint, gitops, project, upgrade
from unslop.findings import objects, table, text
from unslop.project import Config, ConfigError

Level = Literal["ok", "warn", "fail"]
MACHINE_HOOKS = Path("/usr/local/lib/claude-guard")
TOOLS: dict[str, tuple[str, ...]] = {
    "python": ("uv",),
    "typescript": ("node", "npx"),
    "go": ("go",),
    "jvm": ("java",),
    "terraform": ("terraform", "tflint"),
    "rust": ("cargo", "rustup"),
    "dotnet": ("dotnet",),
    "php": ("php", "composer"),
    "ruby": ("ruby", "bundle"),
    "elixir": ("mix",),
    "swift": ("swift",),
}


@dataclass(frozen=True, slots=True)
class Result:
    level: Level
    message: str

    def render(self) -> str:
        return f"{self.level:<4} {self.message}"


def ok(message: str) -> Result:
    return Result("ok", message)


def warn(message: str) -> Result:
    return Result("warn", message)


def failed(message: str) -> Result:
    return Result("fail", message)


def basics() -> list[Result]:
    found = [ok(f"{tool} on PATH") for tool in ("git", "uv", "jq") if shutil.which(tool)]
    missing = [tool for tool in ("git", "uv", "jq") if not shutil.which(tool)]
    hints = {"uv": "https://docs.astral.sh/uv", "jq": "brew install jq or apt install jq", "git": "install git"}
    return found + [failed(f"{tool} is missing; the hooks need it ({hints[tool]})") for tool in missing]


def configuration() -> tuple[Config | None, list[Result]]:
    try:
        config = project.load()
    except ConfigError as error:
        return None, [failed(str(error))]
    stacks = ", ".join(stack.label for stack in config.stacks)
    return config, [ok(f"unslop.toml checks {stacks}")]


def pins(config: Config, online: bool) -> list[Result]:
    results: list[Result] = []
    if config.version == __version__:
        results.append(ok(f"unslop.toml pins {config.version}, the version running"))
    else:
        results.append(
            failed(f"unslop.toml pins {config.version} but this is unslop {__version__}; run `unslop upgrade` with one")
        )
    marketplace = upgrade.marketplace_ref()
    if marketplace is None:
        results.append(failed(f"{footprint.SETTINGS} does not turn the unslop plugin on; run `unslop upgrade`"))
    elif marketplace != f"v{config.version}":
        results.append(failed(f"the plugin is pinned to {marketplace} but unslop.toml says v{config.version}"))
    else:
        results.append(ok(f"the plugin is pinned to {marketplace}"))
    action = upgrade.workflow_ref()
    if action is None:
        results.append(failed(f"{footprint.WORKFLOW} does not run the unslop action"))
    elif online and action not in {f"v{config.version}", footprint.action_ref(config.version)}:
        results.append(warn(f"the CI action is pinned to {action}, not v{config.version}; run `unslop upgrade`"))
    else:
        results.append(ok("the CI action matches the pinned version"))
    return results


def toolchains(config: Config) -> list[Result]:
    results: list[Result] = []
    for stack in config.stacks:
        missing = [tool for tool in TOOLS.get(stack.profile, ()) if not shutil.which(tool)]
        if missing:
            results.append(failed(f"{stack.label}: {', '.join(missing)} not on PATH, so its checks cannot run here"))
        else:
            results.append(ok(f"{stack.label}: toolchain found"))
        if not Path(stack.path).is_dir():
            results.append(failed(f"{stack.label}: folder {stack.path} does not exist"))
    return results


def baseline() -> list[Result]:
    if not project.BASELINE.is_file():
        return [failed(f"no {project.BASELINE}; a human runs `unslop baseline`")]
    if project.BASELINE.as_posix() not in gitops.git("ls-files", str(project.BASELINE), check=False):
        return [warn(f"{project.BASELINE} is not committed yet")]
    return [ok(f"{project.BASELINE} is committed")]


def plugin_installs() -> list[str]:
    registry = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not registry.is_file():
        return []
    try:
        loaded: object = json.loads(registry.read_text())
    except json.JSONDecodeError:
        return []
    entries = objects(table(table(loaded).get("plugins")).get(footprint.PLUGIN))
    return [text(entry.get("version")) for entry in entries]


def plugin(config: Config) -> list[Result]:
    versions = plugin_installs()
    if not versions:
        return [warn("the unslop plugin is not installed for you yet; open Claude Code here and trust the folder")]
    if config.version not in versions:
        return [warn(f"the installed plugin is {', '.join(versions)}; run /plugin update unslop@unslop in Claude Code")]
    return [ok(f"the unslop plugin {config.version} is installed")]


def machine() -> list[Result]:
    if (MACHINE_HOOKS / "stop-gate.sh").is_file():
        return [ok("the machine layer is installed; the hooks cannot be switched off")]
    return [ok("the machine layer is not installed (optional)")]


def ruleset() -> list[Result]:
    if not shutil.which("gh"):
        return [warn("gh is not installed, so the GitHub ruleset was not checked")]
    name = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if not name:
        return [warn("this repository is not on GitHub or gh is not logged in, so the ruleset was not checked")]
    listed = subprocess.run(
        ["gh", "api", f"repos/{name}/rules/branches/{footprint.default_branch()}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        return [warn(f"could not read the branch rules for {name}")]
    rules = objects(json.loads(listed.stdout or "[]"))
    required = [
        text(check.get("context"))
        for rule in rules
        if rule.get("type") == "required_status_checks"
        for check in objects(table(rule.get("parameters")).get("required_status_checks"))
    ]
    if "unslop" in required:
        return [ok("the default branch requires the unslop check")]
    return [warn("the default branch does not require the unslop check; run `unslop ruleset --apply`")]


def diagnose(online: bool) -> list[Result]:
    results = basics()
    config, loaded = configuration()
    results += loaded
    if config is None:
        return results
    results += pins(config, online) + toolchains(config) + baseline() + plugin(config) + machine()
    return results + (ruleset() if online else [])
