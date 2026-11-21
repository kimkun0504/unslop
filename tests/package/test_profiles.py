import json
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import profiles
from unslop.profiles import DetectError

SETUPS: dict[str, dict[str, str]] = {
    "python": {"pyproject.toml": "[project]\nname = 'x'\n", "src/app.py": "x = 1\n"},
    "typescript": {
        "package.json": json.dumps({"devDependencies": {"vitest": "1", "@vitest/coverage-v8": "1", "prettier": "3"}}),
        "tsconfig.json": "{}",
        "eslint.config.js": "export default []\n",
        "pnpm-lock.yaml": "",
    },
    "jvm": {"build.gradle.kts": "", "src/main/kotlin/A.kt": "class A\n", "src/main/java/B.java": "class B {}\n"},
}


@pytest.mark.parametrize("name", sorted(profiles.PROFILES))
def test_every_profile_plans_against_its_project(repo: Path, name: str) -> None:
    for path, content in SETUPS[name].items():
        write(repo / path, content)
    commit(repo, "legacy")
    assert profiles.guess() == [name]
    plan = profiles.plan(name, "unslop")
    assert plan["stack"] == name
    for check in plan["checks"]:
        assert check["report"].startswith(".unslop/out/")
        assert ".unslop/config/" not in check["run"]
        assert ".unslop/guard/" not in check["run"]
    for referenced in (word for check in plan["checks"] for word in check["run"].split() if "/out/config/" in word):
        assert Path(referenced.strip('"').removeprefix("$PWD/")).is_file(), referenced


def test_profiles_report_a_missing_project(repo: Path) -> None:
    with pytest.raises(DetectError, match=r"no package\.json"):
        _ = profiles.plan("typescript", "unslop")
    with pytest.raises(DetectError, match="no Gradle or Maven build"):
        _ = profiles.plan("jvm", "unslop")


def test_unknown_profile(repo: Path) -> None:
    with pytest.raises(DetectError, match="unknown profile"):
        _ = profiles.plan("cobol", "unslop")


def test_python_without_a_lockfile_uses_a_project_venv(repo: Path) -> None:
    write(repo / "pyproject.toml", '[project]\n[dependency-groups]\ndev = ["pytest"]\n')
    plan = profiles.plan("python", "unslop")
    assert plan.get("setup", "").startswith("uv venv")
    assert '".[dev]"' in plan.get("setup", "")
    assert plan["notes"]


def test_python_with_uv_lock(repo: Path) -> None:
    write(repo / "uv.lock", "")
    plan = profiles.plan("python", "unslop")
    assert plan.get("setup") == "uv sync --locked"


def test_typescript_without_coverage_tooling(repo: Path) -> None:
    write(repo / "package.json", json.dumps({"devDependencies": {"jest": "29"}}))
    write(repo / "yarn.lock", "")
    plan = profiles.plan("typescript", "unslop")
    assert [check["name"] for check in plan["checks"]] == ["knip"]
    assert plan.get("tests", {}).get("run", "").startswith("yarn jest")
    assert plan.get("mutation") == {"tool": "stryker", "runner": "jest"}
    write(repo / "package.json", "{}")
    bare = profiles.plan("typescript", "unslop")
    assert "coverage" not in bare.get("tests", {})
    assert "mutation" not in bare


def test_maven_builds_add_jacoco(repo: Path) -> None:
    write(repo / "pom.xml", "")
    plan = profiles.plan("jvm", "unslop")
    assert "jacoco" in plan.get("tests", {}).get("run", "")
    assert plan.get("mutation") == {"tool": "pit", "runner": "mvn"}


def test_python_dead_code_and_mutation_follow_the_installer(repo: Path) -> None:
    write(repo / "poetry.lock", "")
    plan = profiles.plan("python", "unslop")
    vulture = next(check for check in plan["checks"] if check["name"] == "vulture")
    assert vulture.get("kind") == "dead-code"
    assert "poetry run python" in plan.get("mutation", {}).get("runner", "")
    assert Path(".unslop/out/guard/mutmut_run.py").is_file()
