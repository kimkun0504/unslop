import json
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import cli, footprint, project, ratchet, stacks
from unslop.findings import Finding
from unslop.profiles import DetectError
from unslop.project import Config, ConfigError, Stack


def test_several_stacks_round_trip(repo: Path) -> None:
    config = Config([Stack("python"), Stack("typescript", "web", {"tests": "pnpm test"})])
    project.save(config)
    text = (repo / "unslop.toml").read_text()
    assert text.count("[[stack]]") == 2
    assert "[stack.commands]" in text
    assert project.load() == config


def test_single_root_stack_keeps_the_short_form(repo: Path) -> None:
    project.save(Config([Stack("go")]))
    assert 'profile = "go"' in (repo / "unslop.toml").read_text()
    assert "[[stack]]" not in (repo / "unslop.toml").read_text()


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        ('version = "1"\nprofile = "go"\n[[stack]]\nprofile = "go"\n', "not both"),
        ('version = "1"\nstack = []\n', "at least one"),
        ('version = "1"\n[[stack]]\npath = "web"\n', "string `profile`"),
        ('version = "1"\n[[stack]]\nprofile = "go"\npath = "../x"\n', "inside the repository"),
        ('version = "1"\n[[stack]]\nprofile = "go"\n[[stack]]\nprofile = "rust"\n', "share a path"),
        ('version = "1"\nstack = ["go"]\n', "must be a table"),
    ],
)
def test_stack_errors(repo: Path, content: str, problem: str) -> None:
    write(repo / "unslop.toml", content)
    with pytest.raises(ConfigError, match=problem):
        _ = project.load()


def test_discover_finds_a_front_end_beside_the_root(repo: Path) -> None:
    write(repo / "pyproject.toml", "[project]\n")
    write(repo / "web/package.json", "{}")
    write(repo / "infra/main.tf", "")
    write(repo / "tools/pyproject.toml", "[project]\n")
    write(repo / "examples/package.json", "{}")
    write(repo / "node_modules/x/package.json", "{}")
    commit(repo, "root")
    found = stacks.discover()
    assert [(stack.profile, stack.path) for stack in found] == [
        ("python", "."),
        ("terraform", "infra"),
        ("typescript", "web"),
    ]


def test_discover_without_a_root_stack(repo: Path) -> None:
    write(repo / "api/go.mod", "module x\n")
    write(repo / "app/Package.swift", "")
    commit(repo, "root")
    assert [stack.label for stack in stacks.discover()] == ["api:go", "app:swift"]


def test_discover_reports_nothing_found(repo: Path) -> None:
    write(repo / "README.md", "hi\n")
    commit(repo, "root")
    with pytest.raises(DetectError, match="no known stack"):
        _ = stacks.discover()


def test_explicit_stacks(repo: Path) -> None:
    write(repo / "web/package.json", "{}")
    assert stacks.parse("typescript:web") == Stack("typescript", "web")
    assert stacks.parse("go") == Stack("go", ".")
    with pytest.raises(DetectError, match="unknown profile"):
        _ = stacks.parse("cobol")
    with pytest.raises(DetectError, match="not a folder"):
        _ = stacks.parse("go:missing")
    with pytest.raises(cli.UsageError, match="same folder"):
        _ = cli.choose_stacks(["go", "rust:."])


def test_findings_and_files_are_mapped_to_the_repository(repo: Path) -> None:
    finding = Finding("src/a.ts", "no-any", 3, "m")
    assert ratchet.within("web", finding).path == "web/src/a.ts"
    assert ratchet.within(".", finding).path == "src/a.ts"
    assert ratchet.within("web", Finding("/abs/a.ts", "r", 1, "m")).path == "/abs/a.ts"
    changed = ["api.py", "web/src/a.ts", "website/x.ts"]
    assert ratchet.local_files(changed, "web") == [("web/src/a.ts", "src/a.ts")]
    assert ratchet.local_files(changed, ".") == [(path, path) for path in changed]


def test_baseline_keys_carry_the_folder() -> None:
    assert Stack("python").key("ruff") == "ruff"
    assert Stack("typescript", "web").key("eslint") == "web:eslint"


def test_plan_lists_every_stack(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "uv.lock", "")
    write(repo / "web/package.json", "{}")
    project.save(Config([Stack("python"), Stack("typescript", "web")]))
    commit(repo, "root")
    assert cli.main(["plan"]) == 0
    plans = json.loads(capsys.readouterr().out)
    assert list(plans) == ["python", "web:typescript"]
    assert (repo / "web/.unslop/out/.gitignore").is_file()


def test_workflow_uses_a_container_when_any_stack_is_swift(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(footprint, "action_ref", lambda version: version)
    write(repo / "a.txt", "a\n")
    commit(repo, "root")
    assert "container:" in footprint.workflow("1", ["python", "swift"])
    assert "container:" not in footprint.workflow("1", ["python", "typescript"])


def test_settings_protect_build_files_inside_stack_folders(repo: Path) -> None:
    for name in ("web/package-lock.json", "web/eslint.config.js", "web/src/app.ts", "fixtures/package-lock.json"):
        write(repo / name, "x\n")
    commit(repo, "root")
    footprint.write_settings("1.0.0", [".", "web"])
    deny = json.loads((repo / ".claude/settings.json").read_text())["permissions"]["deny"]
    assert "Edit(web/package-lock.json)" in deny
    assert "Edit(web/eslint.config.js)" in deny
    assert "Edit(web/src/app.ts)" not in deny
    assert "Edit(fixtures/package-lock.json)" not in deny


def test_settings_leave_claude_worktrees_editable(repo: Path) -> None:
    write(repo / "a.txt", "a\n")
    commit(repo, "root")
    footprint.write_settings("1.0.0", ["."])
    deny = json.loads((repo / ".claude/settings.json").read_text())["permissions"]["deny"]
    assert "Edit(.claude/**)" not in deny
    assert {"Edit(.claude/settings.json)", "Edit(.claude/skills/**)", "Edit(.mcp.json)"} <= set(deny)
