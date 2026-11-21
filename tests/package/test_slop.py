import json
import time
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import cli, events, gitops, guards, mutation, project, slop
from unslop.project import Config, ConfigError, Gates, Stack


def head() -> str:
    return gitops.git("rev-parse", "HEAD").strip()


def test_gates_round_trip_and_reject_bad_values(repo: Path) -> None:
    config = Config([Stack("python")], gates=Gates(comments="allow", coverage=80, mutation=True, sql_dialect="off"))
    project.save(config)
    assert project.load() == config
    assert "[gates]" in (repo / "unslop.toml").read_text()
    for bad, problem in [
        ('[gates]\ncomments = "sometimes"\n', "comments must be one of"),
        ("[gates]\ncoverage = 101\n", "coverage must be 0 to 100"),
        ('[gates]\ncoverage = "all"\n', "coverage must be a int"),
        ("[gates]\nspeed = 1\n", "does not know speed"),
        ('[gates]\nsql_dialect = "oracle"\n', "sql_dialect must be one of"),
        ('gates = "on"\n', "must be a table"),
    ]:
        write(repo / "unslop.toml", f'version = "1"\nprofile = "python"\n{bad}')
        with pytest.raises(ConfigError, match=problem):
            _ = project.load()


def test_older_files_without_gates_get_the_defaults(repo: Path) -> None:
    write(repo / "unslop.toml", 'version = "1"\nprofile = "python"\n')
    assert project.load().gates == Gates()


def test_allowing_comments_skips_the_comment_gate(repo: Path) -> None:
    write(repo / "src/a.py", "x = 1\n")
    commit(repo, "root")
    since = head()
    write(repo / "src/a.py", "x = 1  # why this matters\n")
    assert cli.gates(since, Config([Stack("python")])) == ["comments"]
    assert cli.gates(since, Config([Stack("python")], gates=Gates(comments="allow"))) == []


def test_new_dependencies_need_the_label_in_ci(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo / "pyproject.toml", '[project]\nname = "a"\ndependencies = []\n')
    write(repo / "web/package.json", json.dumps({"name": "w", "dependencies": {}}))
    commit(repo, "root")
    since = head()
    write(repo / "pyproject.toml", '[project]\nname = "a"\ndependencies = ["httpx>=0.28"]\n')
    write(repo / "web/package.json", json.dumps({"name": "w", "dependencies": {"zod": "^4.1.0"}}))
    stacks = [".", "web"]
    problems, notes = guards.review(since, stacks)
    assert problems == []
    assert "pyproject.toml: adds httpx >=0.28" in notes[0]
    monkeypatch.setenv(guards.IN_CI, "1")
    summary = repo / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    problems, _ = guards.review(since, stacks)
    assert problems == [
        "dependency review: pyproject.toml: adds httpx >=0.28",
        "dependency review: web/package.json: adds zod ^4.1.0",
    ]
    assert "adds zod" in summary.read_text()
    monkeypatch.setenv(guards.CONFIG_REVIEWED, "1")
    assert guards.review(since, stacks)[0] == []
    assert capsys.readouterr().out == ""


def test_routine_updates_need_no_label(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(repo / "package.json", json.dumps({"dependencies": {"react": "^19.1.0", "tiny": "^0.3.1", "gone": "1"}}))
    write(repo / "pnpm-lock.yaml", "a\n")
    write(repo / "requirements.txt", "httpx==0.28.1\nrich==14.0.0\n")
    write(repo / "gradle/libs.versions.toml", '[versions]\nkotlin = "2.4.0"\n')
    commit(repo, "root")
    since = head()
    write(repo / "package.json", json.dumps({"dependencies": {"react": "^19.2.0", "tiny": "^0.3.4"}}))
    write(repo / "pnpm-lock.yaml", "b\n")
    write(repo / "requirements.txt", "httpx==0.28.2\nrich==14.1.0\n")
    write(repo / "gradle/libs.versions.toml", '[versions]\nkotlin = "2.4.21"\n')
    monkeypatch.setenv(guards.IN_CI, "1")
    problems, notes = guards.review(since, ["."])
    assert problems == []
    routine = "gradle/libs.versions.toml, package.json, pnpm-lock.yaml, requirements.txt"
    assert notes == [f"routine dependency updates in {routine} need no label"]


def test_risky_updates_are_named(repo: Path) -> None:
    write(repo / "package.json", json.dumps({"dependencies": {"react": "^18.3.0", "tiny": "^0.3.1"}}))
    write(repo / "requirements.txt", "httpx==0.28.1\n")
    write(repo / "gradle/libs.versions.toml", '[versions]\nkotlin = "2.4.0"\n')
    write(repo / "build.gradle.kts", "plugins {}\n")
    write(repo / "pyproject.toml", '[project]\nname = "a"\n')
    commit(repo, "root")
    since = head()
    package = {"dependencies": {"react": "^19.0.0", "tiny": "^0.4.0"}, "overrides": {"x": "1"}}
    write(repo / "package.json", json.dumps(package))
    write(repo / "requirements.txt", "--index-url https://example.test/simple\nhttpx==0.28.1\n")
    write(repo / "gradle/libs.versions.toml", '[versions]\nkotlin = "2.4.0"\nktor = "3.3.0"\n')
    write(repo / "build.gradle.kts", 'plugins { id("x") }\n')
    write(repo / "pyproject.toml", '[project]\nname = "a"\n[tool.uv.sources]\nx = { git = "https://example.test/x" }\n')
    write(repo / "web/package.json", "{}")
    assert guards.risks(since, "package.json") == [
        "package.json: moves react from ^18.3.0 to ^19.0.0",
        "package.json: moves tiny from ^0.3.1 to ^0.4.0",
        "package.json: changes overrides or resolutions",
    ]
    assert guards.risks(since, "requirements.txt") == ["requirements.txt: changes installer options"]
    assert guards.risks(since, "gradle/libs.versions.toml") == ['gradle/libs.versions.toml: adds versions.ktor "3.3.0"']
    assert guards.risks(since, "build.gradle.kts") == [
        "build.gradle.kts changed; build files can change more than dependencies"
    ]
    assert guards.risks(since, "pyproject.toml") == ["pyproject.toml: changes [tool.uv.sources]"]
    assert guards.risks(since, "web/package.json") == ["web/package.json is new"]
    write(repo / "package.json", "{not json")
    assert guards.risks(since, "package.json") == ["package.json could not be parsed"]


def test_poetry_and_groups_are_read(repo: Path) -> None:
    old = '[tool.poetry.dependencies]\npython = "^3.12"\n[tool.poetry.group.dev.dependencies]\npytest = "^8"\n'
    new = '[tool.poetry.dependencies]\npython = "^3.12"\n[tool.poetry.group.dev.dependencies]\npytest = "^9"\n'
    assert guards.pyproject_risks(old, new) == ['moves pytest from "^8" to "^9"']
    grouped = '[dependency-groups]\ndev = ["ruff==0.17.6", {include-group = "x"}]\n'
    assert guards.pyproject_risks(grouped, grouped.replace("0.17.6", "0.17.7")) == []


def test_new_guarded_commits_make_labels_stale(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(repo / "ruff.toml", "")
    write(repo / "tests/test_a.py", "def test_a():\n    assert 1\n")
    commit(repo, "root")
    since = head()
    write(repo / "src/a.py", "x = 1\n")
    commit(repo, "labelled")
    labelled = head()
    write(repo / "ruff.toml", "[lint]\n")
    write(repo / "tests/test_a.py", "def test_a():\n    assert 2\n")
    commit(repo, "later")
    monkeypatch.setenv(guards.CONFIG_REVIEWED, "1")
    monkeypatch.setenv(guards.TESTS_REVIEWED, "1")
    monkeypatch.setenv(guards.EVENT, "synchronize")
    monkeypatch.setenv(guards.PUSH_BEFORE, labelled)
    monkeypatch.setenv(guards.PUSH_AFTER, head())
    guards.mark_stale(since, ["."])
    assert not guards.reviewed()
    assert not guards.reviewed(guards.TESTS_REVIEWED)
    assert (repo / ".unslop/out/stale-labels.txt").read_text() == "tests-reviewed\nunslop-reviewed\n"
    monkeypatch.setenv(guards.PUSH_BEFORE, head())
    guards.mark_stale(since, ["."])
    assert guards.reviewed()
    monkeypatch.setenv(guards.PUSH_BEFORE, "0" * 40)
    guards.mark_stale(since, ["."])
    assert not guards.reviewed()
    monkeypatch.setenv(guards.EVENT, "labeled")
    guards.mark_stale(since, ["."])
    assert guards.reviewed()


def test_other_manifest_edits_need_review_even_locally(repo: Path) -> None:
    write(repo / "pyproject.toml", '[project]\nname = "a"\n[tool.pytest.ini_options]\naddopts = "-q"\n')
    write(repo / "package.json", json.dumps({"scripts": {"test": "vitest"}}))
    commit(repo, "root")
    since = head()
    write(repo / "pyproject.toml", '[project]\nname = "a"\n[tool.pytest.ini_options]\naddopts = "-k fast"\n')
    write(repo / "package.json", json.dumps({"scripts": {"test": "true"}}))
    problems, _ = guards.review(since, ["."])
    assert problems[:2] == [
        "package.json changed outside its dependency sections",
        "pyproject.toml changed outside its dependency sections",
    ]
    write(repo / "pyproject.toml", "not = [valid")
    assert guards.beyond_dependencies(since, "pyproject.toml")


def test_ci_flags_guardrail_file_changes(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(repo / "ruff.toml", "")
    write(repo / ".unslop/baseline.json", "{}\n")
    commit(repo, "root")
    since = head()
    write(repo / "ruff.toml", "[lint]\n")
    write(repo / ".github/workflows/ci.yml", "on: push\n")
    write(repo / ".unslop/baseline.json", "{}\n\n")
    write(repo / "src/app.py", "x = 1\n")
    assert guards.protected(since, ["."]) == [".github/workflows/ci.yml", "ruff.toml"]
    monkeypatch.setenv(guards.IN_CI, "1")
    assert "guardrail file changed: ruff.toml" in guards.review(since, ["."])[0]


def test_diff_size_warns_then_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "a.py", "x = 1\n")
    commit(repo, "root")
    since = head()
    write(repo / "a.py", "".join(f"x{n} = {n}\n" for n in range(30)))
    write(repo / "b.py", "".join(f"y{n} = {n}\n" for n in range(20)))
    write(repo / "uv.lock", "".join(f"z{n}\n" for n in range(500)))
    assert slop.diff_lines(since) == 51
    assert slop.diff_size(since, Gates(diff_warn_lines=40))
    assert "51 changed lines" in capsys.readouterr().out
    assert not slop.diff_size(since, Gates(diff_max_lines=50))
    assert "over the limit of 50" in capsys.readouterr().out
    assert slop.diff_size(since, Gates(diff_warn_lines=0))
    assert capsys.readouterr().out == ""


def test_duplication_reports_only_new_clones(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = {
        "duplicates": [
            {
                "isNew": True,
                "lines": 8,
                "firstFile": {"name": "a.py", "startLoc": {"line": 1}, "endLoc": {"line": 8}},
                "secondFile": {"name": "b.py", "startLoc": {"line": 3}, "endLoc": {"line": 10}},
            },
            {"isNew": False, "lines": 9},
        ]
    }

    def fake(command: str) -> object:
        assert "--baseline-from-ref abc" in command
        write(repo / ".unslop/out/jscpd/jscpd-report.json", json.dumps(report))
        return type("Done", (), {"stdout": "", "stderr": ""})()

    monkeypatch.setattr(slop, "shell", fake)
    monkeypatch.setattr(slop.shutil, "which", lambda name: f"/bin/{name}")
    assert not slop.duplication("abc")
    report["duplicates"] = [{"isNew": False}]
    assert slop.duplication("abc")


def test_duplication_needs_node_and_a_report(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(slop.shutil, "which", lambda name: None)
    assert slop.duplication("abc")
    assert "Node.js is not installed" in capsys.readouterr().out
    monkeypatch.setattr(slop.shutil, "which", lambda name: name)
    monkeypatch.setattr(slop, "shell", lambda command: type("Done", (), {"stdout": "x", "stderr": "y"})())
    assert not slop.duplication("abc")
    assert "jscpd wrote no report" in capsys.readouterr().out


def test_sql_check_only_when_there_is_sql(repo: Path) -> None:
    write(repo / "a.py", "x = 1\n")
    commit(repo, "root")
    assert slop.sql_check(Gates()) is None
    write(repo / "db/1.sql", "select 1;\n")
    check = slop.sql_check(Gates())
    assert check is not None
    assert "--dialect postgres" in check["run"]
    assert (repo / ".unslop/out/sql-files.txt").read_text() == "db/1.sql\n"
    write(repo / ".sqlfluff", "[sqlfluff]\ndialect = mysql\n")
    assert "--dialect" not in (slop.sql_check(Gates()) or {"run": "--dialect"})["run"]
    assert slop.sql_check(Gates(sql_dialect="off")) is None


def test_fast_check_skips_tests(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo / "uv.lock", "")
    project.save(Config([Stack("python", ".", {"tests": "false"})], gates=Gates(duplication=False)))
    project.write_baseline({})
    commit(repo, "root")
    write(repo / "notes.txt", "hello\n")
    resolve = cli.stacks.resolve
    monkeypatch.setattr(cli.stacks, "resolve", lambda stack, unslop: {**resolve(stack, unslop), "checks": []})
    assert cli.main(["check", "--fast"]) == 0
    assert "tests and coverage run in CI" in capsys.readouterr().out
    assert cli.main(["check"]) == 1
    result = json.loads((repo / ".unslop/out/result.json").read_text())
    assert result["failed"] == ["tests:python"]
    assert result["review_lines"] == 40
    assert result["changed_lines"] == 0


def test_stats_command(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(repo / "state"))
    write(repo / "a.txt", "a\n")
    commit(repo, "root")
    assert cli.main(["stats", "--days", "3"]) == 0
    assert "no blocks in the last 3 days" in capsys.readouterr().out


def test_ranges_merge_consecutive_lines() -> None:
    assert mutation.ranges(frozenset({1, 2, 3, 7, 9, 10}), 0) == [(1, 3), (7, 7), (9, 10)]
    assert mutation.ranges(None, 4) == [(1, 4)]


def test_mutation_targets_skip_tests_and_other_languages(repo: Path) -> None:
    touched: dict[str, frozenset[int] | None] = {
        "web/src/a.ts": frozenset({2}),
        "web/src/a.test.ts": None,
        "web/README.md": None,
        "api/x.py": None,
    }
    changed = sorted(touched)
    assert mutation.targets("stryker", changed, "web", touched) == {"src/a.ts": frozenset({2})}
    assert mutation.targets("mutmut", changed, ".", touched) == {"api/x.py": None}


def test_mutmut_names_map_back_to_lines(repo: Path) -> None:
    source = write(
        repo / "src/app/core.py",
        "def free(x):\n    return x\n\n\n"
        "class Box:\n    def size(self):\n        if self:\n            return 1\n        return 0\n",
    )
    files: dict[str, frozenset[int] | None] = {"src/app/core.py": None}
    located = mutation.locate("app.core.x_free__mutmut_1", files, ["src"])
    assert located is not None
    assert mutation.definition(source, located[1]) == 1
    method = mutation.locate("app.core.xǁBoxǁsize__mutmut_3", files, ["src"])
    assert method is not None
    assert mutation.definition(source, method[1]) == 6
    assert mutation.locate("app.other.x_free__mutmut_1", files, ["src"]) is None
    assert mutation.locate("not a mutant", files, ["src"]) is None
    diff = (
        "# name\n--- src/app/core.py\n+++ src/app/core.py\n"
        "@@ -1,4 +1,4 @@\n def size(self):\n-    if self:\n+    if not self:\n"
    )
    assert mutation.changed_line(diff) == 2
    assert mutation.source_roots(files) == ["src"]


def test_mutation_without_changes_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo / "a.py", "x = 1\n")
    commit(repo, "root")
    assert mutation.run({"tool": "mutmut", "runner": "python"}, head(), ".")
    assert "no changed source lines" in capsys.readouterr().out


def test_events_are_summarised_per_rule(repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert "no blocks" in events.summary(14, "/r")
    log = events.log_path()
    log.parent.mkdir(parents=True)
    now = time.time()
    rows = [
        {"time": now, "hook": "stop-gate", "rule": "lint:ruff", "detail": "attempt 1", "repo": "/r", "session": "a"},
        {"time": now, "hook": "stop-gate", "rule": "lint:ruff", "detail": "attempt 2", "repo": "/r", "session": "a"},
        {"time": now, "hook": "protect-paths", "rule": "claude settings", "detail": ".claude/x", "repo": "/r"},
        {"time": now - 40 * 86400, "hook": "stop-gate", "rule": "old", "repo": "/r"},
        {"time": now, "hook": "guard-bash", "rule": "force push", "repo": "/other"},
    ]
    _ = log.write_text("\n".join(json.dumps(row) for row in rows) + "\nnot json\n")
    text = events.summary(14, "/r")
    assert text.startswith("3 blocks in 2 sessions")
    assert "    2  stop-gate: lint:ruff" in text
    assert "attempt 2" in text
    assert "old" not in text
    assert "force push" in events.summary(14, None)


def test_pit_helpers(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = write(repo / "src/main/kotlin/legacy/Clamp.kt", "package legacy.core\n\nfun clamp(value: Int) = value\n")
    assert mutation.class_name(str(source.relative_to(repo))) == "legacy.core.Clamp"
    write(repo / "Bare.java", "class Bare {}\n")
    assert mutation.class_name("Bare.java") == "Bare"
    fields = "<groupId>org.pitest</groupId><artifactId>pitest</artifactId><version>1.0</version>"
    assert mutation.maven_dependency("org.pitest:pitest:1.0") == f"    <dependency>{fields}</dependency>"
    monkeypatch.delenv("JAVA_HOME", raising=False)
    assert mutation.java_binary() == "java"
    monkeypatch.setenv("JAVA_HOME", "/opt/jdk")
    assert mutation.java_binary() == "/opt/jdk/bin/java"
    write(repo / ".unslop/out/pit/java.txt", "/toolchain/bin/java\n")
    assert mutation.java_binary() == "/toolchain/bin/java"


def test_mutation_budget_stops_with_a_warning(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo / "a.py", "x = 1\n")
    commit(repo, "root")
    since = head()
    write(repo / "a.py", "x = 2\n")

    def slow(plan: object, files: object) -> None:
        _ = mutation.timed("sleep 5")

    monkeypatch.setitem(mutation.RUNNERS, "mutmut", slow)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    started = time.monotonic()
    assert mutation.run({"tool": "mutmut", "runner": "python"}, since, ".", 1)
    assert time.monotonic() - started < 4
    assert "::warning::mutation: stopped after 1s" in capsys.readouterr().out
