import json
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import __version__, cli, doctor, footprint, project, upgrade
from unslop.project import Config, Stack


@pytest.fixture
def adopted(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(footprint, "action_ref", lambda version: f"sha{version}")
    write(repo / "pyproject.toml", "[project]\n")
    project.save(Config([Stack("python", ".", {"tests": "pytest"})], "0.0.9"))
    footprint.write_settings("0.0.9", ["."])
    footprint.write_workflow("0.0.9", ["python"])
    project.write_baseline({})
    commit(repo, "adopted")
    return repo


def test_upgrade_moves_all_three_pins(adopted: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["upgrade"]) == 0
    output = capsys.readouterr().out
    assert "unslop.toml: 0.0.9 -> " in output
    config = project.load()
    assert config.version == __version__
    assert config.stacks[0].commands == {"tests": "pytest"}
    assert upgrade.marketplace_ref() == f"v{__version__}"
    assert upgrade.workflow_ref() == f"sha{__version__}"
    settings = json.loads((adopted / ".claude/settings.json").read_text())
    assert "Edit(pyproject.toml)" in settings["permissions"]["deny"]
    assert cli.main(["upgrade"]) == 0
    assert "already on" in capsys.readouterr().out


def test_upgrade_refuses_an_untagged_version(adopted: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(footprint, "action_ref", lambda version: f"v{version}")
    with pytest.raises(upgrade.UpgradeError, match="not tagged"):
        _ = upgrade.upgrade("9.9.9")
    assert project.load().version == "0.0.9"


def test_upgrade_needs_the_generated_files(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project.save(Config([Stack("python")], "0.0.9"))
    commit(repo, "partial")
    assert cli.main(["upgrade"]) == 1
    assert "run `unslop init`" in capsys.readouterr().err


def test_workflow_without_the_action_is_reported(adopted: Path) -> None:
    write(adopted / ".github/workflows/unslop.yml", "jobs: {}\n")
    with pytest.raises(upgrade.UpgradeError, match="no `uses"):
        upgrade.set_workflow_ref("abc")


def levels(results: list[doctor.Result]) -> dict[str, str]:
    return {result.message: result.level for result in results}


def test_doctor_flags_stale_pins_and_missing_tools(adopted: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda tool: None if tool in {"jq", "uv"} else f"/bin/{tool}")
    monkeypatch.setattr(Path, "home", lambda: adopted / "home")
    found = levels(doctor.diagnose(online=False))
    assert found["jq is missing; the hooks need it (brew install jq or apt install jq)"] == "fail"
    assert any(level == "fail" and "pins 0.0.9" in message for message, level in found.items())
    assert found["python: uv not on PATH, so its checks cannot run here"] == "fail"
    assert any("not installed for you" in message for message in found)


def test_doctor_is_happy_after_an_upgrade(adopted: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda tool: f"/bin/{tool}")
    home = adopted / "home"
    registry = {"version": 2, "plugins": {"unslop@unslop": [{"version": __version__}]}}
    write(home / ".claude/plugins/installed_plugins.json", json.dumps(registry))
    monkeypatch.setattr(Path, "home", lambda: home)
    _ = upgrade.upgrade(__version__)
    commit(adopted, "upgraded")
    results = doctor.diagnose(online=True)
    failures = [result.render() for result in results if result.level == "fail"]
    assert failures == []
    assert f"the unslop plugin {__version__} is installed" in levels(results)


def test_doctor_without_configuration(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "a.txt", "a\n")
    commit(repo, "root")
    assert cli.main(["doctor", "--offline"]) == 1
    assert "run `unslop init` first" in capsys.readouterr().out


def test_doctor_reports_a_stale_plugin_and_uncommitted_baseline(adopted: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = adopted / "home"
    write(
        home / ".claude/plugins/installed_plugins.json",
        json.dumps({"plugins": {"unslop@unslop": [{"version": "0.0.1"}]}}),
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    assert "/plugin update" in doctor.plugin(project.load())[0].message
    (adopted / ".unslop/baseline.json").unlink()
    assert doctor.baseline()[0].level == "fail"


def test_upgrade_retires_the_old_claude_folder_rule(adopted: Path) -> None:
    settings = json.loads((adopted / ".claude/settings.json").read_text())
    settings["permissions"]["deny"].append("Edit(.claude/**)")
    settings["sandbox"]["filesystem"]["denyWrite"].append("./.claude")
    write(adopted / ".claude/settings.json", json.dumps(settings))
    commit(adopted, "old rules")
    _ = upgrade.upgrade(__version__)
    refreshed = json.loads((adopted / ".claude/settings.json").read_text())
    assert "Edit(.claude/**)" not in refreshed["permissions"]["deny"]
    assert "./.claude" not in refreshed["sandbox"]["filesystem"]["denyWrite"]
    assert "Edit(.claude/settings.json)" in refreshed["permissions"]["deny"]


def test_upgrade_reruns_older_workflows_on_labels(adopted: Path) -> None:
    workflow = adopted / ".github/workflows/unslop.yml"
    current = workflow.read_text()
    write(workflow, current.replace(f"\n    types: {upgrade.LABEL_TYPES}", ""))
    commit(adopted, "old trigger")
    changes = upgrade.upgrade(__version__)
    assert any("label" in change for change in changes)
    assert workflow.read_text().replace(f"sha{__version__}", "sha0.0.9") == current
    assert not upgrade.rerun_on_labels()


def test_custom_pull_request_triggers_are_left_alone(adopted: Path) -> None:
    workflow = adopted / ".github/workflows/unslop.yml"
    custom = workflow.read_text().replace(upgrade.LABEL_TYPES, "[opened]")
    write(workflow, custom)
    assert not upgrade.rerun_on_labels()
    assert workflow.read_text() == custom
