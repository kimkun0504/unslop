import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from unslop import __version__, comments, diffcheck, footprint, gitops, profiles, project, ratchet, scaffold
from unslop.fetch import FetchError, fetch
from unslop.profiles import DetectError, Plan
from unslop.project import Config, ConfigError
from unslop.ratchet import BrokenCheckError
from unslop.scaffold import ScaffoldError

if TYPE_CHECKING:
    from collections.abc import Callable

TESTS_REVIEWED = ("UNSLOP_TESTS_REVIEWED", "CHECK_DIFF_ALLOW_TEST_CHANGES")
CONFIG_REVIEWED = "UNSLOP_CONFIG_REVIEWED"
MIN_SECONDS = 240
MAX_SECONDS = 1700


class UsageError(Exception):
    pass


def self_command() -> str:
    return f"{shlex.quote(sys.executable)} -m unslop"


def enabled(*names: str) -> bool:
    return any(os.environ.get(name) == "1" for name in names)


def resolve(config: Config) -> Plan:
    plan = profiles.plan(config.profile, self_command())
    for note in plan["notes"]:
        print(f"note: {note}", file=sys.stderr)
    if "setup" in config.commands:
        plan["setup"] = config.commands["setup"]
    if "tests" in config.commands:
        plan["tests"] = {"run": config.commands["tests"]}
    if "coverage" in config.commands and "tests" in plan:
        coverage = config.commands["coverage"]
        if coverage:
            plan["tests"]["coverage"] = coverage
        else:
            _ = plan["tests"].pop("coverage", None)
    return plan


def loaded() -> Config:
    project.prepare_out()
    config = project.load()
    if config.version != __version__:
        message = (
            f"unslop.toml pins version {config.version} but this is unslop {__version__}; "
            "update the pin in unslop.toml, .claude/settings.json and .github/workflows/unslop.yml together"
        )
        raise ConfigError(message)
    return config


def guard_config(since: str) -> list[str]:
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


def gates(since: str) -> bool:
    ok = True
    found = comments.check(since)
    if found:
        print("comments: comments are forbidden on lines you add; make the code say it instead")
        print("".join(f"  {violation.render()}\n" for violation in found), end="")
        ok = False
    suppressed = diffcheck.suppressions(since)
    if suppressed:
        print("suppressions: new skip or suppression found")
        print("\n".join(f"  {problem.detail}" for problem in suppressed))
        ok = False
    tampered = diffcheck.tampered_tests(since)
    if tampered and not enabled(*TESTS_REVIEWED):
        print("tests: existing tests were modified or deleted; a human must review (label tests-reviewed)")
        print("\n".join(f"  {problem.kind}: {problem.detail}" for problem in tampered))
        print("  new tests go in new files, or after the last line of an existing one with any new imports")
        ok = False
    guarded = guard_config(since)
    if guarded and not enabled(CONFIG_REVIEWED):
        print("unslop: the guardrail configuration changed; a human must review (label unslop-reviewed)")
        print("\n".join(f"  {problem}" for problem in guarded))
        ok = False
    return ok


def run_check(base: str) -> int:
    config = loaded()
    since = gitops.diff_base(base)
    if not gates(since):
        return 1
    plan = resolve(config)
    baseline = project.read_baseline()
    results = [ratchet.formatted(rule, since) for rule in plan["format"]]
    touched = gitops.added_lines(since)
    for item in plan["checks"]:
        found = ratchet.collect(item)
        results.append(ratchet.ratchet(item["name"], found, baseline.get(item["name"], {}), touched))
    if "tests" in plan:
        results.append(ratchet.tested(plan["tests"], since))
    if all(results):
        print("unslop: all checks pass")
        return 0
    return 1


def run_setup() -> int:
    plan = resolve(loaded())
    setup = plan.get("setup", "")
    if not setup:
        return 0
    print(f"$ {setup}", flush=True)
    return subprocess.run(["bash", "-c", setup], check=False).returncode


def record_baseline() -> int:
    plan = resolve(loaded())
    baseline: dict[str, dict[str, int]] = {}
    for item in plan["checks"]:
        found = ratchet.collect(item)
        baseline[item["name"]] = ratchet.counts(found)
        print(f"{item['name']}: recorded {len(found)} findings")
    project.write_baseline(baseline)
    print(f"wrote {project.BASELINE}")
    return 0


def choose_profile(requested: str | None) -> str:
    if requested:
        return requested
    guesses = profiles.guess()
    if len(guesses) == 1:
        return guesses[0]
    found = ", ".join(guesses) if guesses else "none"
    message = f"pass --profile; detected: {found}; available: {', '.join(sorted(profiles.PROFILES))}"
    raise UsageError(message)


def budget(elapsed: float) -> int:
    return max(MIN_SECONDS, min(MAX_SECONDS, int(elapsed) * 2 + 60))


def run_init(requested: str | None, skip_setup: bool) -> int:
    os.chdir(gitops.toplevel())
    if project.CONFIG.exists():
        message = "unslop.toml already exists; this repository is already set up"
        raise UsageError(message)
    if footprint.WORKFLOW.exists():
        message = f"{footprint.WORKFLOW} already exists; remove or rename it first"
        raise UsageError(message)
    if not gitops.clean():
        message = "commit or stash your changes first, so the unslop change is reviewable on its own"
        raise UsageError(message)
    config = Config(choose_profile(requested))
    profiles.plan(config.profile, self_command())
    project.save(config)
    footprint.write_settings(config.version)
    footprint.write_workflow(config.version, config.profile)
    print(f"set up unslop {config.version} with the {config.profile} profile")
    if not skip_setup and run_setup() != 0:
        print("setup failed: fix [commands] setup in unslop.toml, then run `unslop setup` and `unslop baseline`")
        return 1
    _ = record_baseline()
    started = time.monotonic()
    if run_check("origin/main") != 0:
        print("check fails against the new baseline; usually [commands] tests in unslop.toml needs adjusting")
        return 1
    elapsed = time.monotonic() - started
    config.fast_check_seconds = budget(elapsed)
    project.save(config)
    print(f"the check passes in {elapsed:.0f}s; Claude gets {config.fast_check_seconds}s at the end of each turn")
    print("next: review `git status`, commit on a branch and open a pull request")
    print("then protect the default branch: unslop ruleset --apply")
    return 0


def run_ruleset(apply: bool) -> int:
    local = Path(".github/rulesets/main.json")
    content = local.read_text() if local.is_file() else footprint.ruleset()
    if not apply:
        print(content, end="")
        return 0
    name = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if not name:
        message = "gh could not find this repository on GitHub; push it first and log in with `gh auth login`"
        raise UsageError(message)
    command = ["gh", "api", "-X", "POST", f"repos/{name}/rulesets", "--input", "-"]
    return subprocess.run(command, input=content, text=True, check=False).returncode


def run_fetch(tool: str) -> int:
    print(fetch(tool))
    return 0


def run_new(template: str, directory: str) -> int:
    target = Path(directory)
    for warning in scaffold.new_project(template, target, __version__):
        print(f"warning: {warning}", file=sys.stderr)
    print(f"created {target} from the {template} template")
    print(f"next: cd {target} && scripts/setup && scripts/verify")
    print("then push to GitHub and protect main: unslop ruleset --apply")
    return 0


def run_list() -> int:
    print(scaffold.listing())
    return 0


def run_plan() -> int:
    print(json.dumps(resolve(loaded()), indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="unslop", description="Make AI slop fail the build.")
    _ = root.add_argument("--version", action="version", version=f"unslop {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="add unslop to this repository and record the baseline")
    _ = init.add_argument("--profile", choices=sorted(profiles.PROFILES))
    _ = init.add_argument("--skip-setup", action="store_true", help="skip installing dependencies")
    check = commands.add_parser("check", help="run every gate against the changes since the base branch")
    _ = check.add_argument("--base", default="origin/main")
    _ = commands.add_parser("setup", help="install the project's dependencies")
    _ = commands.add_parser("baseline", help="record current findings as the baseline (humans only)")
    rules = commands.add_parser("ruleset", help="print or apply the GitHub branch ruleset")
    _ = rules.add_argument("--apply", action="store_true")
    tool = commands.add_parser("fetch", help="download a pinned tool and print its path")
    _ = tool.add_argument("tool")
    _ = commands.add_parser("plan", help="print the commands each gate runs")
    new = commands.add_parser("new", help="start a new project from a template")
    _ = new.add_argument("template")
    _ = new.add_argument("directory")
    _ = commands.add_parser("list", help="show templates, their gates and profiles for existing repositories")
    return root


def dispatch(arguments: argparse.Namespace) -> int:
    handlers: dict[str, Callable[[], int]] = {
        "init": lambda: run_init(arguments.profile, arguments.skip_setup),
        "check": lambda: run_check(arguments.base),
        "setup": run_setup,
        "baseline": record_baseline,
        "ruleset": lambda: run_ruleset(arguments.apply),
        "fetch": lambda: run_fetch(arguments.tool),
        "plan": run_plan,
        "new": lambda: run_new(arguments.template, arguments.directory),
        "list": run_list,
    }
    return handlers[arguments.command]()


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command not in {"init", "fetch", "ruleset", "new", "list"}:
            os.chdir(gitops.toplevel())
        return dispatch(arguments)
    except (
        ConfigError,
        DetectError,
        BrokenCheckError,
        FetchError,
        gitops.GitError,
        ScaffoldError,
        UsageError,
    ) as failure:
        print(f"unslop: {failure}", file=sys.stderr)
        return 2 if isinstance(failure, UsageError) else 1
    except KeyboardInterrupt:
        return 130
