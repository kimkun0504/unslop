import json
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import findings, gitops, ratchet
from unslop.fetch import FetchError, catalog
from unslop.findings import Finding


def parse(kind: str, report: str) -> list[tuple[str, str, int]]:
    return [(item.path, item.rule, item.line) for item in findings.PARSERS[kind](report)]


def test_sarif() -> None:
    report = {
        "runs": [
            {
                "results": [
                    {
                        "ruleId": "E1",
                        "message": {"text": "bad"},
                        "locations": [
                            {"physicalLocation": {"artifactLocation": {"uri": "src/a.py"}, "region": {"startLine": 3}}}
                        ],
                    }
                ]
            }
        ]
    }
    assert parse("sarif", json.dumps(report)) == [("src/a.py", "E1", 3)]


def test_pyright_and_eslint() -> None:
    pyright = {
        "generalDiagnostics": [
            {"file": "a.py", "rule": "reportX", "range": {"start": {"line": 4}}, "message": "m\nmore"}
        ]
    }
    assert parse("pyright", json.dumps(pyright)) == [("a.py", "reportX", 5)]
    eslint = [{"filePath": "a.ts", "messages": [{"ruleId": None, "line": 2, "message": "parse"}]}]
    assert parse("eslint", json.dumps(eslint)) == [("a.ts", "fatal", 2)]


def test_line_formats() -> None:
    assert parse("tsc", "src/a.ts(3,5): error TS2532: Object is possibly 'undefined'.") == [("src/a.ts", "TS2532", 3)]
    assert parse("lines", "src/A.kt:4:1: println() is forbidden; use a logger") == [
        ("src/A.kt", "println() is forbidden", 4)
    ]


def test_dead_code_reports() -> None:
    vulture = (
        "src/app/core.py:5: unused function 'helper' (60% confidence)\n"
        "src/app/core.py:9: unused variable 'name' (60% confidence)\n"
        "src/app/core.py:12: unused method 'run' (60% confidence)\n"
    )
    assert parse("vulture", vulture) == [
        ("src/app/core.py", "unused-function", 5),
        ("src/app/core.py", "unused-method", 12),
    ]
    knip = {
        "issues": [
            {"file": "src/orphan.ts", "owners": [], "files": [{"name": "src/orphan.ts"}], "exports": []},
            {"file": "src/math.ts", "exports": [{"name": "unused", "line": 4, "col": 17}], "catalog": []},
            {"file": "src/a.ts", "classMembers": {"A": [{"name": "b", "line": 2}]}},
        ]
    }
    assert parse("knip", json.dumps(knip)) == [
        ("src/orphan.ts", "files", 1),
        ("src/math.ts", "exports", 4),
        ("src/a.ts", "classMembers", 2),
    ]


def test_sqlfluff_reports_may_be_split() -> None:
    first = [{"filepath": "db/1.sql", "violations": [{"code": "LT09", "start_line_no": 1, "description": "x"}]}]
    second = [{"filepath": "db/2.sql", "violations": [{"code": "CP01", "start_line_no": 3, "description": "y"}]}]
    report = f"{json.dumps(first)}\n{json.dumps(second)}\n"
    assert parse("sqlfluff", report) == [("db/1.sql", "LT09", 1), ("db/2.sql", "CP01", 3)]


def test_absolute_and_file_uris_become_relative(repo: Path) -> None:
    assert findings.relative(f"file://{repo}/src/a.py") == "src/a.py"
    assert findings.relative("/elsewhere/a.py") == "/elsewhere/a.py"


def test_ratchet_allows_the_baseline_and_flags_growth(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    old = Finding("a.py", "E1", 1, "old")
    new = Finding("a.py", "E1", 5, "new")
    assert ratchet.ratchet("ruff", [old], {"a.py::E1": 1}, {})
    assert not ratchet.ratchet("ruff", [old, new], {"a.py::E1": 1}, {"a.py": frozenset({5})})
    output = capsys.readouterr().out
    assert "the baseline allows 1" in output
    assert "on lines this change touches" in output
    assert ratchet.ratchet("ruff", [], {"a.py::E1": 2}, {})
    assert "2 recorded findings are fixed" in capsys.readouterr().out


def test_collect_refuses_a_missing_or_broken_report(repo: Path) -> None:
    check: ratchet.Check = {"name": "lint", "format": "sarif", "report": ".unslop/out/r.sarif", "run": "true"}
    with pytest.raises(ratchet.BrokenCheckError, match="wrote no report"):
        _ = ratchet.collect(check)
    check["run"] = "echo nope > .unslop/out/r.sarif"
    with pytest.raises(ratchet.BrokenCheckError, match="not valid JSON"):
        _ = ratchet.collect(check)
    check["run"] = ": > .unslop/out/r.sarif; echo broken >&2; exit 3"
    with pytest.raises(ratchet.BrokenCheckError, match="exit code 3"):
        _ = ratchet.collect(check)


def test_formatting_ratchet(repo: Path) -> None:
    write(repo / "tidy.txt", "a\n")
    write(repo / "messy.txt", "A\n")
    commit(repo, "base")
    since = "HEAD"
    write(repo / "tidy.txt", "B\n")
    write(repo / "messy.txt", "C\n")
    write(repo / "new.txt", "D\n")
    rule: ratchet.FormatRule = {"name": "lower", "glob": ["*.txt"], "run": "tr A-Z a-z"}
    files = ratchet.local_files(gitops.changed_files(since), ".")
    assert not ratchet.formatted(rule, since, files)
    write(repo / "tidy.txt", "b\n")
    write(repo / "new.txt", "d\n")
    assert ratchet.formatted(rule, since, files)


def test_tests_must_write_a_coverage_report(repo: Path) -> None:
    assert ratchet.run_tests({"run": "true"}, "HEAD", ".")
    assert not ratchet.run_tests({"run": "false"}, "HEAD", ".")
    assert not ratchet.run_tests({"run": "true", "coverage": ".unslop/out/none.xml"}, "HEAD", ".")
    assert ratchet.run_tests({"run": "true", "coverage": ".unslop/out/none.xml"}, "HEAD", ".", 0)


def test_coverage_threshold_reaches_diff_cover() -> None:
    command = ratchet.coverage_command({"run": "x"}, ["c.xml"], "abc", ".", 80)
    assert command[command.index("--fail-under") + 1] == "80"


def test_fetch_catalog_is_pinned() -> None:
    for tool in ("detekt", "pmd"):
        item = catalog(tool)
        assert item.url.startswith("https://")
        assert len(item.sha256) == 64
    with pytest.raises(FetchError, match="unknown tool"):
        _ = catalog("nope")
