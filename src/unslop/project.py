import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from unslop import __version__

CONFIG = Path("unslop.toml")
BASELINE = Path(".unslop/baseline.json")
OUT = Path(".unslop/out")
DEFAULT_SECONDS = 240
OVERRIDABLE = ("setup", "tests", "coverage")


class ConfigError(Exception):
    pass


@dataclass(slots=True)
class Config:
    profile: str
    version: str = __version__
    fast_check_seconds: int = DEFAULT_SECONDS
    commands: dict[str, str] = field(default_factory=dict[str, str])

    def render(self) -> str:
        lines = [
            f'version = "{self.version}"',
            f'profile = "{self.profile}"',
            f"fast_check_seconds = {self.fast_check_seconds}",
        ]
        if self.commands:
            lines += ["", "[commands]"]
            lines += [f"{key} = {json.dumps(value)}" for key, value in sorted(self.commands.items())]
        return "\n".join(lines) + "\n"


def load(path: Path = CONFIG) -> Config:
    if not path.is_file():
        message = f"no {path} here; run `unslop init` first"
        raise ConfigError(message)
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        message = f"{path} is not valid TOML: {error}"
        raise ConfigError(message) from error
    profile, version = raw.get("profile"), raw.get("version")
    if not isinstance(profile, str) or not isinstance(version, str):
        message = f"{path} needs string `version` and `profile` keys"
        raise ConfigError(message)
    seconds = raw.get("fast_check_seconds", DEFAULT_SECONDS)
    if not isinstance(seconds, int):
        message = f"{path}: fast_check_seconds must be a whole number"
        raise ConfigError(message)
    commands = raw.get("commands", {})
    if not isinstance(commands, dict):
        message = f"{path}: [commands] must be a table"
        raise ConfigError(message)
    typed = cast("dict[str, object]", commands)
    unknown = sorted(set(typed) - set(OVERRIDABLE))
    if unknown or not all(isinstance(value, str) for value in typed.values()):
        message = f"{path}: [commands] accepts string values for {', '.join(OVERRIDABLE)} only"
        raise ConfigError(message)
    return Config(profile, version, seconds, cast("dict[str, str]", typed))


def save(config: Config, path: Path = CONFIG) -> None:
    _ = path.write_text(config.render())


def read_baseline(content: str | None = None) -> dict[str, dict[str, int]]:
    text = content if content is not None else (BASELINE.read_text() if BASELINE.is_file() else "{}")
    return cast("dict[str, dict[str, int]]", json.loads(text))


def write_baseline(baseline: dict[str, dict[str, int]]) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    _ = BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")


def prepare_out() -> Path:
    for sub in ("config", "guard"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    _ = (OUT / ".gitignore").write_text("*\n")
    return OUT
