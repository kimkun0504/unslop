import argparse
import fnmatch
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from unslop import (
    __version__,
    comments,
    diffcheck,
    doctor,
    events,
    footprint,
    gitops,
    guards,
    mutation,
    profiles,
    project,
    ratchet,
    scaffold,
    slop,
    stacks,
    upgrade,
)
from unslop.fetch import FetchError, fetch
from unslop.profiles import Check, DetectError, Plan
from unslop.project import Config, ConfigError, Stack
from unslop.ratchet import BrokenCheckError
from unslop.scaffold import ScaffoldError
from unslop.upgrade import UpgradeError

if TYPE_CHECKING:
    from collections.abc import Callable

TESTS_REVIEWED = ("UNSLOP_TESTS_REVIEWED", "CHECK_DIFF_ALLOW_TEST_CHANGES")
MIN_SECONDS = 240
MAX_SECONDS = 1700


class UsageError(Exception):
    pass


def self_command() -> str:
    return f"{shlex.quote(sys.executable)} -m unslop"


def enabled(*names: str) -> bool:
    return any(os.environ.get(name) == "1" for name in names)


def loaded() -> Config:
    config = project.load()
    if config.version != __version__:
        message = (
            f"unslop.toml pins version {config.version} but this is unslop {__version__}; "
            "update the pin in unslop.toml, .claude/settings.json and .github/workflows/unslop.yml together"
        )
        raise ConfigError(message)
    return config


def gates(since: str, config: Config) -> list[str]:
    failed: list[str] = []
    found = comments.check(since) if config.gates.comments == "forbid" else []
    if found:
        print("comments: comments are forbidden on lines you add; make the code say it instead")
        print("".join(f"  {violation.render()}\n" for violation in found), end="")
        failed.append("comments")
    suppressed = diffcheck.suppressions(since)
    if suppressed:
        print("suppressions: new skip or suppression found")
        print("\n".join(f"  {problem.detail}" for problem in suppressed))
        failed.append("suppressions")
    tampered = diffcheck.tampered_tests(since)
    if tampered and not enabled(*TESTS_REVIEWED):
        print("tests: existing tests were modified or deleted; a human must review (label tests-reviewed)")
        print("\n".join(f"  {problem.kind}: {problem.detail}" for problem in tampered))
        print("  new tests go in new files, or after the last line of an existing one with any new imports")
        failed.append("test-tampering")
    problems, notes = guards.review(since, [stack.path for stack in config.stacks])
    if problems:
        print("review: guardrail or dependency files changed; a human must review (label unslop-reviewed)")
        print("\n".join(f"  {problem}" for problem in problems))
        failed.append("needs-review")
    print("\n".join(f"note: {note}" for note in notes), end="\n" if notes else "")
    return failed


def lint(
    item: Check,
    stack: Stack,
    baseline: dict[str, dict[str, int]],
    touched: ratchet.Touched,
    scope: list[tuple[str, str]] | None,
) -> tuple[str, bool]:
    key = stack.key(item["name"])
    if scope is None:
        return f"lint:{key}", ratchet.ratchet(key, ratchet.collect(item, stack.path), baseline.get(key, {}), touched)
    files = [
        local
        for _, local in scope
        if any(fnmatch.fnmatchcase(Path(local).name, glob) for glob in item.get("files", []))
    ]
    if not files:
        print(f"{key}: no changed files to check")
        return f"lint:{key}", True
    found = ratchet.collect(ratchet.scoped(item, files), stack.path)
    within = {full for full, local in scope if local in files}
    return f"lint:{key}", ratchet.ratchet(key, found, baseline.get(key, {}), touched, within)


def scope_for(stack: Stack, config: Config, changed: list[str], *, fast: bool) -> list[tuple[str, str]] | None:
    limit = config.gates.fast_scope_files
    if not fast or (limit and len(gitops.git("ls-files", "--", ".").splitlines()) <= limit):
        return None
    return [(full, local) for full, local in ratchet.local_files(changed, stack.path) if Path(local).is_file()]


def check_stack(
    stack: Stack, config: Config, since: str, touched: ratchet.Touched, *, fast: bool
) -> list[tuple[str, bool]]:
    baseline = project.read_baseline()
    changed = gitops.changed_files(since)
    results: list[tuple[str, bool]] = []
    with project.inside(stack.path):
        project.prepare_out()
        plan = stacks.resolve(stack, self_command())
        files = ratchet.local_files(changed, stack.path)
        results += [(f"format:{rule['name']}", ratchet.formatted(rule, since, files)) for rule in plan["format"]]
        scope = scope_for(stack, config, changed, fast=fast)
        if scope is not None:
            print(f"{stack.label}: large stack, so the fast check lints only the {len(scope)} changed files")
        for item in plan["checks"]:
            dead = item.get("kind") == "dead-code"
            if dead and (not config.gates.dead_code or scope is not None):
                continue
            results.append(lint(item, stack, baseline, touched, scope if "scoped" in item else None))
        if fast:
            return results
        if "tests" in plan:
            passed = ratchet.run_tests(plan["tests"], since, stack.path, config.gates.coverage)
            results.append((f"tests:{stack.label}", passed))
        if config.gates.mutation and "mutation" in plan and all(passed for _, passed in results):
            passed = mutation.run(plan["mutation"], since, stack.path, config.gates.mutation_seconds)
            results.append((f"mutation:{stack.label}", passed))
    return results


def repository_checks(config: Config, since: str, touched: ratchet.Touched) -> list[tuple[str, bool]]:
    results = [("diff-size", slop.diff_size(since, config.gates))]
    if config.gates.duplication:
        results.append(("duplication", slop.duplication(since)))
    sql = slop.sql_check(config.gates)
    if sql is not None:
        recorded = project.read_baseline().get("sqlfluff", {})
        results.append(("lint:sqlfluff", ratchet.ratchet("sqlfluff", ratchet.collect(sql), recorded, touched)))
    return results


def record_result(failed: list[str]) -> None:
    project.prepare_out()
    _ = (project.OUT / "result.json").write_text(json.dumps({"failed": failed}) + "\n")


def run_check(base: str | None, *, fast: bool = False) -> int:
    config = loaded()
    since = gitops.diff_base(base)
    failed = gates(since, config)
    if failed:
        record_result(failed)
        return 1
    touched = gitops.added_lines(since)
    project.prepare_out()
    results = repository_checks(config, since, touched)
    for stack in config.stacks:
        if len(config.stacks) > 1:
            print(f"== {stack.label}", flush=True)
        results += check_stack(stack, config, since, touched, fast=fast)
    failed = [name for name, passed in results if not passed]
    record_result(failed)
    if failed:
        return 1
    print("unslop: all fast checks pass; tests and coverage run in CI" if fast else "unslop: all checks pass")
    return 0


def run_setup() -> int:
    for stack in loaded().stacks:
        with project.inside(stack.path):
            project.prepare_out()
            setup = stacks.resolve(stack, self_command()).get("setup", "")
            if not setup:
                continue
            print(f"$ {setup}" if stack.path == "." else f"$ (in {stack.path}) {setup}", flush=True)
            code = subprocess.run(["bash", "-c", setup], check=False).returncode
        if code != 0:
            return code
    return 0


def record_baseline(*, missing_only: bool = False) -> int:
    config = loaded()
    baseline = project.read_baseline() if missing_only else {}
    planned: list[tuple[str, str, Check]] = []
    for stack in config.stacks:
        with project.inside(stack.path):
            project.prepare_out()
            plan = stacks.resolve(stack, self_command())
            planned += [(stack.path, stack.key(item["name"]), item) for item in plan["checks"]]
    project.prepare_out()
    sql = slop.sql_check(config.gates)
    if sql is not None:
        planned.append((".", "sqlfluff", sql))
    for path, key, item in planned:
        if missing_only and key in baseline:
            continue
        with project.inside(path):
            found = ratchet.collect(item, path)
        baseline[key] = ratchet.counts(found)
        print(f"{key}: recorded {len(found)} findings")
    project.write_baseline(baseline)
    print(f"wrote {project.BASELINE}")
    return 0


def choose_stacks(requested: list[str]) -> list[Stack]:
    chosen = [stacks.parse(argument) for argument in requested]
    if not chosen:
        return stacks.discover()
    paths = [stack.path for stack in chosen]
    if len(set(paths)) != len(paths):
        message = "two --stack options name the same folder; give each stack its own folder"
        raise UsageError(message)
    return chosen


def budget(elapsed: float) -> int:
    return max(MIN_SECONDS, min(MAX_SECONDS, int(elapsed) * 2 + 60))


def run_init(requested: list[str], skip_setup: bool) -> int:
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
    config = Config(choose_stacks(requested))
    for stack in config.stacks:
        with project.inside(stack.path):
            _ = profiles.plan(stack.profile, self_command())
    project.save(config)
    footprint.write_settings(config.version, [stack.path for stack in config.stacks])
    footprint.write_workflow(config.version)
    print(f"set up unslop {config.version} for {', '.join(stack.label for stack in config.stacks)}")
    if not skip_setup and run_setup() != 0:
        print("setup failed: override the setup command in unslop.toml, then run `unslop setup` and `unslop baseline`")
        return 1
    _ = record_baseline()
    started = time.monotonic()
    if run_check(None) != 0:
        print("check fails against the new baseline; usually the tests command in unslop.toml needs adjusting")
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


TOOLCHAIN_FILES = {
    "node": ("typescript", (".node-version", ".nvmrc")),
    "java": ("jvm", (".java-version", ".sdkmanrc")),
}


def run_toolchains(prefix: str) -> int:
    config = project.load()
    print(f"profiles= {' '.join(sorted(set(config.profiles)))} ")
    for tool, (profile, names) in TOOLCHAIN_FILES.items():
        candidates = [
            Path(prefix) / stack.path / name for stack in config.stacks if stack.profile == profile for name in names
        ]
        found = next((path for path in candidates if path.is_file()), None)
        print(f"{tool}_file={Path(os.path.normpath(found)).as_posix() if found else ''}")
    return 0


def run_upgrade() -> int:
    changes = upgrade.upgrade(__version__)
    if not changes:
        print(f"already on unslop {__version__}")
        return 0
    print("\n".join(changes))
    print("recording a baseline for checks this version adds", flush=True)
    _ = record_baseline(missing_only=True)
    print("next: commit on a branch and open a pull request with the unslop-reviewed label")
    return 0


def run_doctor(online: bool) -> int:
    results = doctor.diagnose(online)
    print("\n".join(result.render() for result in results))
    return 1 if any(result.level == "fail" for result in results) else 0


def run_stats(days: int, *, everywhere: bool) -> int:
    print(events.summary(days, None if everywhere else str(gitops.toplevel())))
    return 0


def run_plan() -> int:
    plans: dict[str, Plan] = {}
    for stack in loaded().stacks:
        with project.inside(stack.path):
            project.prepare_out()
            plans[stack.label] = stacks.resolve(stack, self_command())
    print(json.dumps(plans, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="unslop", description="Make AI slop fail the build.")
    _ = root.add_argument("--version", action="version", version=f"unslop {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="add unslop to this repository and record the baseline")
    _ = init.add_argument(
        "--stack",
        action="append",
        default=[],
        metavar="PROFILE[:FOLDER]",
        help="a stack to check, such as python or typescript:web; repeat for each one. Detected when left out",
    )
    _ = init.add_argument("--profile", dest="stack", action="append", help=argparse.SUPPRESS)
    _ = init.add_argument("--skip-setup", action="store_true", help="skip installing dependencies")
    check = commands.add_parser("check", help="run every gate against the changes since the base branch")
    _ = check.add_argument("--base", default=None, help="branch to compare against; the default branch when left out")
    _ = check.add_argument("--fast", action="store_true", help="skip tests, coverage and mutation, as Claude does")
    stats = commands.add_parser("stats", help="count how often each guardrail blocked Claude")
    _ = stats.add_argument("--days", type=int, default=14)
    _ = stats.add_argument("--all", action="store_true", help="every repository, not only this one")
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
    _ = commands.add_parser("upgrade", help="move unslop.toml, the plugin and the CI action to this unslop version")
    health = commands.add_parser("doctor", help="explain what is missing for unslop to work here")
    _ = health.add_argument("--offline", action="store_true", help="skip the checks that need GitHub")
    chains = commands.add_parser("toolchains", help="print the toolchains CI needs, for the GitHub Action")
    _ = chains.add_argument("--prefix", default=".")
    return root


def dispatch(arguments: argparse.Namespace) -> int:
    handlers: dict[str, Callable[[], int]] = {
        "init": lambda: run_init(arguments.stack, arguments.skip_setup),
        "check": lambda: run_check(arguments.base, fast=arguments.fast),
        "stats": lambda: run_stats(arguments.days, everywhere=arguments.all),
        "setup": run_setup,
        "baseline": record_baseline,
        "ruleset": lambda: run_ruleset(arguments.apply),
        "fetch": lambda: run_fetch(arguments.tool),
        "plan": run_plan,
        "new": lambda: run_new(arguments.template, arguments.directory),
        "list": run_list,
        "toolchains": lambda: run_toolchains(arguments.prefix),
        "upgrade": run_upgrade,
        "doctor": lambda: run_doctor(not arguments.offline),
    }
    return handlers[arguments.command]()


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command not in {"init", "fetch", "ruleset", "new", "list", "toolchains"}:
            os.chdir(gitops.toplevel())
        return dispatch(arguments)
    except (
        ConfigError,
        DetectError,
        BrokenCheckError,
        FetchError,
        gitops.GitError,
        ScaffoldError,
        UpgradeError,
        UsageError,
    ) as failure:
        print(f"unslop: {failure}", file=sys.stderr)
        return 2 if isinstance(failure, UsageError) else 1
    except KeyboardInterrupt:
        return 130
