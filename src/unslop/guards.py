import json
import os
import re
import tomllib
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import cast

from unslop import diffcheck, footprint, gitops, project

CONFIG_REVIEWED = "UNSLOP_CONFIG_REVIEWED"
TESTS_REVIEWED = "UNSLOP_TESTS_REVIEWED"
IN_CI = "UNSLOP_CI"
EVENT = "UNSLOP_EVENT_ACTION"
PUSH_BEFORE = "UNSLOP_PUSH_BEFORE"
PUSH_AFTER = "UNSLOP_PUSH_AFTER"
LABELS = {CONFIG_REVIEWED: "unslop-reviewed", TESTS_REVIEWED: "tests-reviewed"}
LOCKFILES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock", "poetry.lock", "gradle.lockfile")
REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*)$")
NUMBER = re.compile(r"(\d+)(?:\.(\d+))?")
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


STALE: set[str] = set()


def reviewed(variable: str = CONFIG_REVIEWED) -> bool:
    return os.environ.get(variable) == "1" and LABELS[variable] not in STALE


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


def major(spec: str) -> str | None:
    found = NUMBER.search(spec)
    if found is None:
        return None
    return f"0.{found.group(2) or 0}" if found.group(1) == "0" else found.group(1)


def requirement(line: str) -> tuple[str, str] | None:
    found = REQUIREMENT.match(line)
    if found is None:
        return None
    return found.group(1).lower().replace("_", "-"), found.group(3).strip()


def requirements(items: object) -> dict[str, str]:
    listed = cast("list[object]", items) if isinstance(items, list) else []
    pairs = [requirement(item) for item in listed if isinstance(item, str)]
    return dict(pair for pair in pairs if pair is not None)


def section(document: Document, *keys: str) -> object:
    current: object = document
    for key in keys:
        current = tables(current).get(key)
    return current


def tables(value: object) -> dict[str, object]:
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def package_specs(document: Document) -> dict[str, str]:
    specs: dict[str, str] = {}
    for name in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        specs.update({key: str(value) for key, value in tables(document.get(name)).items()})
    return specs


def pyproject_specs(document: Document) -> dict[str, str]:
    specs = requirements(section(document, "project", "dependencies"))
    for group in tables(section(document, "project", "optional-dependencies")).values():
        specs.update(requirements(group))
    for group in tables(document.get("dependency-groups")).values():
        specs.update(requirements(group))
    poetry = [
        section(document, "tool", "poetry", "dependencies"),
        section(document, "tool", "poetry", "dev-dependencies"),
    ]
    poetry += [
        tables(group).get("dependencies") for group in tables(section(document, "tool", "poetry", "group")).values()
    ]
    for block in poetry:
        specs.update({key.lower(): json.dumps(value, sort_keys=True) for key, value in tables(block).items()})
    return specs


def catalog_specs(document: Document) -> dict[str, str]:
    specs: dict[str, str] = {}
    for name in ("versions", "libraries", "plugins", "bundles"):
        specs.update(
            {f"{name}.{key}": json.dumps(value, sort_keys=True) for key, value in tables(document.get(name)).items()}
        )
    return specs


def compare(old: dict[str, str], new: dict[str, str]) -> list[str]:
    risky = [f"adds {name} {new[name]}".rstrip() for name in sorted(set(new) - set(old))]
    for name in sorted(set(old) & set(new)):
        before, after = old[name], new[name]
        if before != after and (major(before) is None or major(before) != major(after)):
            risky.append(f"moves {name} from {before} to {after}")
    return risky


def text_requirements(content: str) -> tuple[dict[str, str], list[str]]:
    specs: dict[str, str] = {}
    options: list[str] = []
    for line in content.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped.startswith("-"):
            options.append(stripped)
        elif stripped and (pair := requirement(stripped)) is not None:
            specs[pair[0]] = pair[1]
    return specs, options


def package_risks(old: str, new: str) -> list[str]:
    old_doc, new_doc = parse_package(old), parse_package(new)
    found = compare(package_specs(old_doc), package_specs(new_doc))
    overrides = [("overrides",), ("resolutions",), ("pnpm", "overrides")]
    if any(section(old_doc, *key) != section(new_doc, *key) for key in overrides):
        found.append("changes overrides or resolutions")
    return found


def pyproject_risks(old: str, new: str) -> list[str]:
    old_doc, new_doc = parse_pyproject(old), parse_pyproject(new)
    found = compare(pyproject_specs(old_doc), pyproject_specs(new_doc))
    if section(old_doc, "tool", "uv", "sources") != section(new_doc, "tool", "uv", "sources"):
        found.append("changes [tool.uv.sources]")
    return found


def catalog_risks(old: str, new: str) -> list[str]:
    return compare(catalog_specs(parse_pyproject(old)), catalog_specs(parse_pyproject(new)))


def requirement_risks(old: str, new: str) -> list[str]:
    (old_specs, old_options), (new_specs, new_options) = text_requirements(old), text_requirements(new)
    found = compare(old_specs, new_specs)
    if old_options != new_options:
        found.append("changes installer options")
    return found


def assessor(name: str) -> Callable[[str, str], list[str]] | None:
    if name == "package.json":
        return package_risks
    if name == "pyproject.toml":
        return pyproject_risks
    if name.endswith(".versions.toml"):
        return catalog_risks
    if name.startswith("requirements") and name.endswith(".txt"):
        return requirement_risks
    return None


def risks(since: str, path: str) -> list[str]:
    name = Path(path).name
    before = gitops.show(since, path)
    if name in LOCKFILES or not Path(path).is_file():
        return []
    if before is None:
        return [f"{path} is new"]
    assess = assessor(name)
    if assess is None:
        return [f"{path} changed; build files can change more than dependencies"]
    try:
        found = assess(before.decode(errors="replace"), Path(path).read_text(errors="replace"))
    except (json.JSONDecodeError, tomllib.TOMLDecodeError):
        return [f"{path} could not be parsed"]
    return [f"{path}: {item}" for item in found]


def pushed() -> list[str] | None:
    before, after = os.environ.get(PUSH_BEFORE, ""), os.environ.get(PUSH_AFTER, "")
    if os.environ.get(EVENT) != "synchronize" or not after:
        return []
    if not before or not gitops.resolves(f"{before}^{{commit}}"):
        return None
    return gitops.git("diff", "--name-only", "--no-renames", before, after, "--").splitlines()


def mark_stale(since: str, folders: list[str]) -> None:
    STALE.clear()
    latest = pushed()
    nested = [folder for folder in folders if folder != "."]
    paths = changed(since) if latest is None else latest
    guarded = [
        path for path in paths if always(path) or footprint.guarded(path, nested) or footprint.dependency(path, nested)
    ]
    if os.environ.get(CONFIG_REVIEWED) == "1" and guarded:
        STALE.add(LABELS[CONFIG_REVIEWED])
    if os.environ.get(TESTS_REVIEWED) == "1" and any(diffcheck.is_test(path) for path in paths):
        STALE.add(LABELS[TESTS_REVIEWED])
    if STALE:
        project.prepare_out()
        _ = (project.OUT / "stale-labels.txt").write_text("".join(f"{label}\n" for label in sorted(STALE)))
        for label in sorted(STALE):
            print(f"review: new commits changed what {label} approved; the label is removed, review and add it again")


def summarise(lines: list[str]) -> None:
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target or not lines:
        return
    with Path(target).open("a") as summary:
        _ = summary.write("### What unslop-reviewed approves\n\n" + "".join(f"- {line}\n" for line in lines) + "\n")


def review(since: str, folders: list[str]) -> tuple[list[str], list[str]]:
    problems = configuration(since)
    notes: list[str] = []
    deps = dependencies(since, folders)
    problems += [f"{path} changed outside its dependency sections" for path in deps if beyond_dependencies(since, path)]
    risky = [item for path in deps if not beyond_dependencies(since, path) for item in risks(since, path)]
    routine = [path for path in deps if not beyond_dependencies(since, path) and not risks(since, path)]
    if in_ci():
        problems += [f"guardrail file changed: {path}" for path in protected(since, folders)]
        problems += [f"dependency review: {item}" for item in risky]
    elif risky:
        notes.append(f"dependency changes need the unslop-reviewed label on the pull request: {'; '.join(risky)}")
    if routine:
        notes.append(f"routine dependency updates in {', '.join(routine)} need no label")
    summarise(problems)
    return ([] if reviewed() else problems), notes
