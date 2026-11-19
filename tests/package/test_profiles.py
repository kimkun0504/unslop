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
    "go": {"go.mod": "module x\n"},
    "jvm": {"build.gradle.kts": "", "src/main/kotlin/A.kt": "class A\n", "src/main/java/B.java": "class B {}\n"},
    "terraform": {"main.tf": "", "main.tftest.hcl": ""},
    "rust": {"Cargo.toml": '[package]\nedition = "2024"\n'},
    "dotnet": {"App.slnx": ""},
    "php": {
        "composer.json": json.dumps({"require-dev": {"phpunit/phpunit": "11"}}),
        "src/A.php": "",
        "tests/ATest.php": "",
    },
    "ruby": {
        "Gemfile": "",
        "Gemfile.lock": "GEM\n  specs:\n    rubocop (1.0)\n",
        ".rubocop.yml": "",
        "spec/a_spec.rb": "",
    },
    "elixir": {"mix.exs": "", "mix.lock": '%{"credo": {}}\n'},
    "swift": {"Package.swift": "", ".swift-format": "{}", ".swiftlint.yml": ""},
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
    with pytest.raises(DetectError, match=r"no go\.mod"):
        _ = profiles.plan("go", "unslop")


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
    assert plan["checks"] == []
    assert plan.get("tests", {}).get("run", "").startswith("yarn jest")
    write(repo / "package.json", "{}")
    assert "coverage" not in profiles.plan("typescript", "unslop").get("tests", {})


def test_maven_and_php_folders(repo: Path) -> None:
    write(repo / "pom.xml", "")
    assert "jacoco" in profiles.plan("jvm", "unslop").get("tests", {}).get("run", "")
    write(repo / "composer.json", "{}")
    with pytest.raises(DetectError, match="no src, app or lib"):
        _ = profiles.plan("php", "unslop")


def test_ruby_without_rubocop_installs_it(repo: Path) -> None:
    write(repo / "Gemfile", "")
    plan = profiles.plan("ruby", "unslop")
    assert "gem install" in plan.get("setup", "")
    assert "rake test" in plan.get("tests", {}).get("run", "")


def test_elixir_without_credo_and_swift_without_format(repo: Path) -> None:
    write(repo / "mix.exs", "")
    assert [check["name"] for check in profiles.plan("elixir", "unslop")["checks"]] == ["compiler"]
    write(repo / "Package.swift", "")
    assert profiles.plan("swift", "unslop")["format"] == []


def test_dotnet_and_terraform_need_projects(repo: Path) -> None:
    with pytest.raises(DetectError):
        _ = profiles.plan("dotnet", "unslop")
    with pytest.raises(DetectError):
        _ = profiles.plan("terraform", "unslop")
