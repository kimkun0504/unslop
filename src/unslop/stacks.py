import sys
from pathlib import Path

from unslop import gitops, profiles, project
from unslop.profiles import DetectError, Plan
from unslop.project import Stack

SKIPPED_FOLDERS = frozenset(
    {
        "node_modules",
        "vendor",
        "dist",
        "build",
        "target",
        "docs",
        "doc",
        "examples",
        "example",
        "samples",
        "tests",
        "test",
        "spec",
        "venv",
        "scripts",
    }
)


def resolve(stack: Stack, unslop: str) -> Plan:
    plan = profiles.plan(stack.profile, unslop)
    for note in plan["notes"]:
        print(f"note: {stack.label}: {note}", file=sys.stderr)
    commands = stack.commands
    if "setup" in commands:
        plan["setup"] = commands["setup"]
    if "tests" in commands:
        plan["tests"] = {"run": commands["tests"]}
    if "coverage" in commands and "tests" in plan:
        if commands["coverage"]:
            plan["tests"]["coverage"] = commands["coverage"]
        else:
            _ = plan["tests"].pop("coverage", None)
    return plan


def parse(argument: str) -> Stack:
    profile, _, path = argument.partition(":")
    if profile not in profiles.PROFILES:
        message = f"unknown profile {profile}; choose one of {', '.join(sorted(profiles.PROFILES))}"
        raise DetectError(message)
    folder = Path(path or ".").as_posix()
    if not Path(folder).is_dir():
        message = f"{folder} is not a folder in this repository"
        raise DetectError(message)
    return Stack(profile, folder)


def candidate_folders() -> list[str]:
    tracked = {name.split("/", 1)[0] for name in gitops.git("ls-files").splitlines() if "/" in name}
    return sorted(
        name
        for name in tracked
        if Path(name).is_dir() and not name.startswith(".") and name.lower() not in SKIPPED_FOLDERS
    )


def discover() -> list[Stack]:
    found = profiles.guess()
    if len(found) > 1:
        message = (
            f"the repository root looks like {', '.join(found)}; choose with --stack PROFILE[:FOLDER], once per stack"
        )
        raise DetectError(message)
    stacks = [Stack(found[0], ".")] if found else []
    root = found[0] if found else None
    for folder in candidate_folders():
        with project.inside(folder):
            nested = [profile for profile in profiles.guess() if profile != root]
        if len(nested) == 1:
            stacks.append(Stack(nested[0], folder))
        elif nested:
            print(f"note: {folder} looks like {', '.join(nested)}; add it with --stack if you want it checked")
    if not stacks:
        message = (
            f"no known stack found; choose with --stack PROFILE[:FOLDER] from {', '.join(sorted(profiles.PROFILES))}"
        )
        raise DetectError(message)
    return stacks
