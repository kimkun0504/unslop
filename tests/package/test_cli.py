import json
import os
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import __version__, cli, project, scaffold
from unslop.project import Config, Stack


def test_new_scaffolds_a_template_with_the_plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNSLOP_OWNER", "octocat")
    monkeypatch.setenv("UNSLOP_OWNER_NAME", "Mona Lisa")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t")
    target = tmp_path / "app"
    assert cli.main(["new", "python", str(target)]) == 0
    settings = json.loads((target / ".claude/settings.json").read_text())
    assert settings["enabledPlugins"] == {"unslop@unslop": True}
    assert settings["extraKnownMarketplaces"]["unslop"]["source"]["ref"] == f"v{__version__}"
    assert "@octocat" in (target / ".github/CODEOWNERS").read_text()
    assert os.access(target / "scripts/fast-check", os.X_OK)
    assert cli.main(["new", "python", str(target)]) == 1
    assert cli.main(["new", "cobol", str(tmp_path / "other")]) == 1


def test_list_names_templates_and_profiles(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list"]) == 0
    output = capsys.readouterr().out
    assert "ts-react" in output
    assert "unslop init --stack" in output
    assert "typescript" in scaffold.listing()


def test_commands_outside_a_configured_repository_explain_themselves(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo / "a.txt", "a\n")
    commit(repo, "root")
    assert cli.main(["check"]) == 1
    assert "run `unslop init` first" in capsys.readouterr().err


def test_init_refuses_a_dirty_tree_or_an_existing_setup(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "pyproject.toml", "[project]\n")
    commit(repo, "root")
    write(repo / "dirty.py", "x = 1\n")
    assert cli.main(["init"]) == 2
    assert "commit or stash" in capsys.readouterr().err
    (repo / "dirty.py").unlink()
    project.save(Config([Stack("python")]))
    commit(repo, "configured")
    assert cli.main(["init"]) == 2
    assert "already exists" in capsys.readouterr().err


def test_init_needs_a_profile_when_detection_is_ambiguous(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "pyproject.toml", "[project]\n")
    write(repo / "package.json", "{}")
    commit(repo, "root")
    assert cli.main(["init"]) == 1
    assert "looks like typescript, python" in capsys.readouterr().err


def test_plan_applies_command_overrides(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "uv.lock", "")
    project.save(Config([Stack("python", ".", {"setup": "make deps", "tests": "make test", "coverage": ""})]))
    commit(repo, "root")
    assert cli.main(["plan"]) == 0
    plan = json.loads(capsys.readouterr().out)["python"]
    assert plan["setup"] == "make deps"
    assert plan["tests"] == {"run": "make test"}


def test_ruleset_prints_the_repository_ruleset_when_there_is_one(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["ruleset"]) == 0
    assert '"context": "unslop"' in capsys.readouterr().out
    write(repo / ".github/rulesets/main.json", '{"name": "template"}\n')
    assert cli.main(["ruleset"]) == 0
    assert "template" in capsys.readouterr().out


def test_budget_is_bounded() -> None:
    assert cli.budget(1) == cli.MIN_SECONDS
    assert cli.budget(200) == 460
    assert cli.budget(5000) == cli.MAX_SECONDS


def test_gates_report_every_problem(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "tests/test_a.py", "def test_a():\n    assert 1\n")
    write(repo / "src/a.py", "x = 1\n")
    commit(repo, "root")
    since = cli.gitops.git("rev-parse", "HEAD").strip()
    write(repo / "src/a.py", "x = 1  # explain\ny = 2  # noqa\n")
    write(repo / "tests/test_a.py", "def test_a():\n    assert 2\n")
    assert cli.gates(since, Config([Stack("python")])) == ["comments", "suppressions", "test-tampering"]
    output = capsys.readouterr().out
    assert "comments are forbidden" in output
    assert "new skip or suppression" in output
    assert "existing tests were modified" in output


def test_reviewed_test_changes_pass_with_the_label(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(repo / "tests/test_a.py", "def test_a():\n    assert 1\n")
    commit(repo, "root")
    since = cli.gitops.git("rev-parse", "HEAD").strip()
    write(repo / "tests/test_a.py", "def test_a():\n    assert 2\n")
    monkeypatch.setenv("UNSLOP_TESTS_REVIEWED", "1")
    assert cli.gates(since, Config([Stack("python")])) == []
