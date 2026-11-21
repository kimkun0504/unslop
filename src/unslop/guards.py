import json
import os
import tomllib
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import cast

from unslop import footprint, gitops, project

CONFIG_REVIEWED = "UNSLOP_CONFIG_REVIEWED"
IN_CI = "UNSLOP_CI"
type Document = dict[str, object]
PACKAGE_SECTIONS = (
    ("dependencies",),
    ("devDependencies",),
    ("peerDependencies",),
    ("optionalDependencies",),
    ("overrides",),
    ("resolutions",),
    ("pnpm", "overrides"),
    ("packageManager",),
    ("version",),
)
PYPROJECT_SECTIONS = (
    ("project", "dependencies"),
    ("project", "optional-dependencies"),
    ("project", "version"),
    ("dependency-groups",),
    ("tool", "poetry", "dependencies"),
    ("tool", "poetry", "group"),
    ("tool", "poetry", "dev-dependencies"),
    ("tool", "poetry", "version"),
    ("tool", "uv", "sources"),
    ("tool", "uv", "dev-dependencies"),
)


def reviewed() -> bool:
    return os.environ.get(CONFIG_REVIEWED) == "1"


def in_ci() -> bool:
    return os.environ.get(IN_CI) == "1"


def configuration(since: str) -> list[str]:
    problems: list[str] = []
    before = gitops.show(since, str(project.CONFIG))
    if before is not None and before.decode() != project.CONFIG.read_text():
        problems.append("unslop.toml changed")
    previous = gitops.show(since, str(project.BASELINE))
    if previous is not None:
        old = project.read_baseline(previous.decode())
        new = project.read_baseline()
        for name, keys in new.items():
            grown = [key for key, amount in keys.items() if amount > old.get(name, {}).get(key, 0)]
            problems += [f"baseline grew: {name} {key}" for key in grown]
    return problems


def changed(since: str) -> list[str]:
    modified = gitops.git("diff", "--name-only", "--no-renames", since, "--").splitlines()
    return sorted({*modified, *gitops.untracked()})


def always(path: str) -> bool:
    folders = tuple(f"{folder}/" for folder in footprint.ALWAYS_FOLDERS)
    return path in footprint.ALWAYS_FILES or path.startswith(folders)


def protected(since: str, folders: list[str]) -> list[str]:
    nested = [folder for folder in folders if folder != "."]
    return [
        path
        for path in changed(since)
        if path != str(project.CONFIG)
        and not path.startswith(".unslop/")
        and (always(path) or footprint.guarded(path, nested))
    ]


def without(document: Document, sections: tuple[tuple[str, ...], ...]) -> Document:
    copy = deepcopy(document)
    for section in sections:
        parent = copy
        for key in section[:-1]:
            child = parent.get(key)
            parent = cast("Document", child) if isinstance(child, dict) else {}
        _ = parent.pop(section[-1], None)
    return copy


def parse_package(content: str) -> Document:
    loaded: object = json.loads(content)
    return cast("Document", loaded) if isinstance(loaded, dict) else {}


def parse_pyproject(content: str) -> Document:
    return cast("Document", tomllib.loads(content))


PARSERS: dict[str, tuple[Callable[[str], Document], tuple[tuple[str, ...], ...]]] = {
    "package.json": (parse_package, PACKAGE_SECTIONS),
    "pyproject.toml": (parse_pyproject, PYPROJECT_SECTIONS),
}


def beyond_dependencies(since: str, path: str) -> bool:
    handler = PARSERS.get(Path(path).name)
    before = gitops.show(since, path)
    if handler is None or before is None or not Path(path).is_file():
        return False
    parse, sections = handler
    try:
        old, new = parse(before.decode()), parse(Path(path).read_text())
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return True
    return without(old, sections) != without(new, sections)


def dependencies(since: str, folders: list[str]) -> list[str]:
    nested = [folder for folder in folders if folder != "."]
    return [path for path in changed(since) if footprint.dependency(path, nested)]


def review(since: str, folders: list[str]) -> tuple[list[str], list[str]]:
    problems = configuration(since)
    notes: list[str] = []
    deps = dependencies(since, folders)
    problems += [f"{path} changed outside its dependency sections" for path in deps if beyond_dependencies(since, path)]
    if in_ci():
        problems += [f"guardrail file changed: {path}" for path in protected(since, folders)]
        problems += [f"dependencies changed: {path}" for path in deps if not beyond_dependencies(since, path)]
    elif deps:
        notes.append(f"dependency files changed ({', '.join(deps)}); the pull request needs the unslop-reviewed label")
    return ([] if reviewed() else problems), notes
