import json
import os
import tomllib
from collections.abc import Generator
from contextlib import contextmanager
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
class Stack:
    profile: str
    path: str = "."
    commands: dict[str, str] = field(default_factory=dict[str, str])

    @property
    def label(self) -> str:
        return self.profile if self.path == "." else f"{self.path}:{self.profile}"

    def key(self, check: str) -> str:
        return check if self.path == "." else f"{self.path}:{check}"


@dataclass(slots=True)
class Config:
    stacks: list[Stack]
    version: str = __version__
    fast_check_seconds: int = DEFAULT_SECONDS

    @property
    def profiles(self) -> list[str]:
        return [stack.profile for stack in self.stacks]

    def render(self) -> str:
        lines = [f'version = "{self.version}"', f"fast_check_seconds = {self.fast_check_seconds}"]
        if len(self.stacks) == 1 and self.stacks[0].path == ".":
            only = self.stacks[0]
            lines.insert(1, f'profile = "{only.profile}"')
            if only.commands:
                lines += ["", "[commands]", *render_commands(only.commands)]
            return "\n".join(lines) + "\n"
        for stack in self.stacks:
            lines += ["", "[[stack]]", f'profile = "{stack.profile}"', f"path = {json.dumps(stack.path)}"]
            if stack.commands:
                lines += ["", "[stack.commands]", *render_commands(stack.commands)]
        return "\n".join(lines) + "\n"


def render_commands(commands: dict[str, str]) -> list[str]:
    return [f"{key} = {json.dumps(value)}" for key, value in sorted(commands.items())]


def fail(message: str) -> ConfigError:
    return ConfigError(f"{CONFIG}: {message}")


def read_commands(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        message = "commands must be a table"
        raise fail(message)
    typed = cast("dict[str, object]", raw)
    unknown = sorted(set(typed) - set(OVERRIDABLE))
    if unknown or not all(isinstance(value, str) for value in typed.values()):
        message = f"commands accepts string values for {', '.join(OVERRIDABLE)} only"
        raise fail(message)
    return cast("dict[str, str]", typed)


def read_stack(raw: object) -> Stack:
    if not isinstance(raw, dict):
        message = "each [[stack]] must be a table"
        raise fail(message)
    table = cast("dict[str, object]", raw)
    profile, path = table.get("profile"), table.get("path", ".")
    if not isinstance(profile, str) or not isinstance(path, str):
        message = "each [[stack]] needs a string `profile` and an optional string `path`"
        raise fail(message)
    clean = Path(path).as_posix()
    if Path(clean).is_absolute() or ".." in Path(clean).parts:
        message = f"stack path {path} must be a folder inside the repository"
        raise fail(message)
    return Stack(profile, clean, read_commands(table.get("commands", {})))


def read_stacks(raw: dict[str, object]) -> list[Stack]:
    listed = raw.get("stack")
    if listed is not None and "profile" in raw:
        message = "use either a top-level `profile` or [[stack]] tables, not both"
        raise fail(message)
    if listed is None:
        profile = raw.get("profile")
        if not isinstance(profile, str):
            message = "needs a string `profile` or [[stack]] tables"
            raise fail(message)
        return [Stack(profile, ".", read_commands(raw.get("commands", {})))]
    if not isinstance(listed, list) or not listed:
        message = "[[stack]] must list at least one stack"
        raise fail(message)
    stacks = [read_stack(item) for item in cast("list[object]", listed)]
    paths = [stack.path for stack in stacks]
    if len(set(paths)) != len(paths):
        message = "two stacks share a path; give each stack its own folder"
        raise fail(message)
    return stacks


def load(path: Path = CONFIG) -> Config:
    if not path.is_file():
        message = f"no {path} here; run `unslop init` first"
        raise ConfigError(message)
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        message = f"{path} is not valid TOML: {error}"
        raise ConfigError(message) from error
    version = raw.get("version")
    if not isinstance(version, str):
        message = "needs a string `version`"
        raise fail(message)
    seconds = raw.get("fast_check_seconds", DEFAULT_SECONDS)
    if not isinstance(seconds, int):
        message = "fast_check_seconds must be a whole number"
        raise fail(message)
    return Config(read_stacks(raw), version, seconds)


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


@contextmanager
def inside(folder: str) -> Generator[None]:
    previous = Path.cwd()
    os.chdir(folder)
    try:
        yield
    finally:
        os.chdir(previous)
