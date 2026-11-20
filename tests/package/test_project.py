import json
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import __version__, cli, footprint, gitops, project
from unslop.project import Config, ConfigError, Stack


def test_config_round_trips(repo: Path) -> None:
    config = Config([Stack("python", ".", {"tests": 'pytest -q -k "fast"'})], "1.2.3", 300)
    project.save(config)
    assert project.load() == config


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        ('profile = "python"\n', "string `version`"),
        ('version = "1"\n', "string `profile` or"),
        ('version = "1"\nprofile = "python"\nfast_check_seconds = "x"\n', "whole number"),
        ('version = "1"\nprofile = "python"\ncommands = 3\n', "must be a table"),
        ('version = "1"\nprofile = "python"\n[commands]\nlint = "x"\n', "accepts string values"),
        ("version = \n", "not valid TOML"),
    ],
)
def test_config_errors(repo: Path, content: str, problem: str) -> None:
    write(repo / "unslop.toml", content)
    with pytest.raises(ConfigError, match=problem):
        _ = project.load()


def test_missing_config_points_at_init(repo: Path) -> None:
    with pytest.raises(ConfigError, match="unslop init"):
        _ = project.load()


def test_version_mismatch_is_refused(repo: Path) -> None:
    project.save(Config([Stack("python")], "0.0.1"))
    with pytest.raises(ConfigError, match=r"pins version 0\.0\.1"):
        _ = cli.loaded()


def test_out_folder_ignores_itself(repo: Path) -> None:
    out = project.prepare_out()
    write(out / "report.json", "{}")
    assert gitops.untracked() == []


def test_diff_base_is_the_adoption_commit_without_a_remote(repo: Path) -> None:
    write(repo / "app.py", "x = 1\n")
    commit(repo, "legacy")
    write(repo / "unslop.toml", 'version = "1"\nprofile = "python"\n')
    commit(repo, "adopt")
    adopted = gitops.git("rev-parse", "HEAD").strip()
    write(repo / "app.py", "x = 2\n")
    commit(repo, "work")
    assert gitops.diff_base() == adopted


def test_diff_base_is_the_root_commit_for_templates(repo: Path) -> None:
    write(repo / "app.py", "x = 1\n")
    commit(repo, "root")
    root = gitops.git("rev-parse", "HEAD").strip()
    write(repo / "app.py", "x = 2\n")
    commit(repo, "work")
    assert gitops.diff_base() == root


def test_a_repository_without_a_remote_falls_back_to_its_history(repo: Path) -> None:
    write(repo / "app.py", "x = 1\n")
    commit(repo, "root")
    root = gitops.git("rev-parse", "HEAD").strip()
    assert gitops.diff_base("origin/develop") == root


def test_guard_config_flags_config_change_and_baseline_growth(repo: Path) -> None:
    project.save(Config([Stack("python")]))
    project.write_baseline({"ruff": {"a.py::E1": 1}})
    commit(repo, "adopt")
    since = gitops.git("rev-parse", "HEAD").strip()
    assert cli.guard_config(since) == []
    project.write_baseline({"ruff": {"a.py::E1": 2, "b.py::E2": 1}})
    project.save(Config([Stack("python", ".", {"tests": "true"})]))
    assert cli.guard_config(since) == [
        "unslop.toml changed",
        "baseline grew: ruff a.py::E1",
        "baseline grew: ruff b.py::E2",
    ]


def test_shrinking_the_baseline_is_fine(repo: Path) -> None:
    project.save(Config([Stack("python")]))
    project.write_baseline({"ruff": {"a.py::E1": 2}})
    commit(repo, "adopt")
    since = gitops.git("rev-parse", "HEAD").strip()
    project.write_baseline({"ruff": {"a.py::E1": 1}})
    assert cli.guard_config(since) == []


def test_settings_enable_the_plugin_and_protect_existing_files(repo: Path) -> None:
    write(repo / "pyproject.toml", "[project]\n")
    write(repo / "web/package.json", "{}")
    write(repo / ".claude/settings.json", json.dumps({"permissions": {"deny": ["Read(.env)"]}, "model": "opus"}))
    commit(repo, "legacy")
    footprint.write_settings("9.9.9", ["."])
    written = json.loads((repo / ".claude/settings.json").read_text())
    assert written["model"] == "opus"
    assert written["enabledPlugins"] == {"unslop@unslop": True}
    assert written["extraKnownMarketplaces"]["unslop"]["source"]["ref"] == "v9.9.9"
    deny = written["permissions"]["deny"]
    assert deny[0] == "Read(.env)"
    assert {"Edit(unslop.toml)", "Edit(.unslop/**)", "Edit(pyproject.toml)", "Edit(web/package.json)"} <= set(deny)
    assert "Edit(Cargo.toml)" not in deny
    assert "./pyproject.toml" in written["sandbox"]["filesystem"]["denyWrite"]


def test_settings_merge_is_idempotent(repo: Path) -> None:
    footprint.write_settings(__version__, ["."])
    first = (repo / ".claude/settings.json").read_text()
    footprint.write_settings(__version__, ["."])
    assert (repo / ".claude/settings.json").read_text() == first


def test_workflow_pins_the_action_and_adds_a_container_for_swift(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(footprint, "action_ref", lambda version: f"sha-for-{version}")
    commit_placeholder = write(repo / "a.txt", "a\n")
    assert commit_placeholder.exists()
    commit(repo, "root")
    plain = footprint.workflow("1.0.0", "python")
    assert "uses: kimkun0504/unslop@sha-for-1.0.0" in plain
    assert "branches: [main]" in plain
    assert "container" not in plain
    swift = footprint.workflow("1.0.0", "swift")
    assert "container: swift:6.4.2-noble" in swift
    assert swift.index("apt-get") < swift.index("actions/checkout")


def test_ruleset_requires_the_unslop_check() -> None:
    rules = json.loads(footprint.ruleset())
    checks = next(rule for rule in rules["rules"] if rule["type"] == "required_status_checks")
    assert checks["parameters"]["required_status_checks"] == [{"context": "unslop"}]


def test_default_base_follows_the_remote_default_branch(tmp_path: Path, repo: Path) -> None:
    write(repo / "app.py", "x = 1\n")
    commit(repo, "root")
    remote = tmp_path / "remote.git"
    _ = gitops.git("init", "-q", "--bare", "-b", "master", str(remote))
    _ = gitops.git("branch", "-m", "master")
    _ = gitops.git("remote", "add", "origin", str(remote))
    _ = gitops.git("push", "-q", "origin", "master")
    _ = gitops.git("remote", "set-head", "origin", "master")
    base = gitops.git("rev-parse", "HEAD").strip()
    write(repo / "app.py", "x = 2\n")
    commit(repo, "work")
    assert gitops.default_ref() == "origin/master"
    assert gitops.diff_base() == base
    with pytest.raises(gitops.GitError, match="pass --base"):
        _ = gitops.diff_base("origin/develop")
