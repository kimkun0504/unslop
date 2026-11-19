import json
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import findings, ratchet
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


def test_pyright_eslint_rubocop_credo_phpstan() -> None:
    pyright = {
        "generalDiagnostics": [
            {"file": "a.py", "rule": "reportX", "range": {"start": {"line": 4}}, "message": "m\nmore"}
        ]
    }
    assert parse("pyright", json.dumps(pyright)) == [("a.py", "reportX", 5)]
    eslint = [{"filePath": "a.ts", "messages": [{"ruleId": None, "line": 2, "message": "parse"}]}]
    assert parse("eslint", json.dumps(eslint)) == [("a.ts", "fatal", 2)]
    rubocop = {
        "files": [{"path": "a.rb", "offenses": [{"cop_name": "Lint/X", "location": {"start_line": 7}, "message": "m"}]}]
    }
    assert parse("rubocop", json.dumps(rubocop)) == [("a.rb", "Lint/X", 7)]
    credo = {"issues": [{"filename": "a.ex", "check": "Credo.X", "line_no": 1, "message": "m"}]}
    assert parse("credo", json.dumps(credo)) == [("a.ex", "Credo.X", 1)]
    phpstan = {"files": {"src/A.php": {"messages": [{"message": "Call 3 times", "line": 9}]}}}
    assert parse("phpstan", json.dumps(phpstan)) == [("src/A.php", "Call _ times", 9)]


def test_line_formats() -> None:
    assert parse("tsc", "src/a.ts(3,5): error TS2532: Object is possibly 'undefined'.") == [("src/a.ts", "TS2532", 3)]
    assert parse("lines", "src/A.kt:4:1: println() is forbidden; use a logger") == [
        ("src/A.kt", "println() is forbidden", 4)
    ]
    msbuild = "src/A.cs(10,5): warning CA1822: Mark members as static [/x/A.csproj]"
    assert parse("msbuild", f"{msbuild}\n{msbuild}") == [("src/A.cs", "CA1822", 10)]
    swift = "\x1b[1mSources/A.swift:2:3: warning: x is never used [#UnusedVariable]\x1b[0m"
    assert parse("compiler", findings.TERMINAL_CODES.sub("", swift)) == [("Sources/A.swift", "UnusedVariable", 2)]
    elixir = '    warning: variable "x" is unused\n    │\n    └─ lib/a.ex:3:5: A.f/0\n'
    assert parse("elixir", elixir) == [("lib/a.ex", "variable _ is unused", 3)]
    cargo = json.dumps(
        {
            "reason": "compiler-message",
            "message": {
                "message": "used unwrap",
                "code": {"code": "clippy::unwrap_used"},
                "spans": [{"is_primary": True, "file_name": "src/lib.rs", "line_start": 8}],
            },
        }
    )
    assert parse("cargo", f"not json\n{cargo}") == [("src/lib.rs", "clippy::unwrap_used", 8)]


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
    assert not ratchet.formatted(rule, since)
    write(repo / "tidy.txt", "b\n")
    write(repo / "new.txt", "d\n")
    assert ratchet.formatted(rule, since)


def test_tests_must_write_a_coverage_report(repo: Path) -> None:
    assert ratchet.tested({"run": "true"}, "HEAD")
    assert not ratchet.tested({"run": "false"}, "HEAD")
    assert not ratchet.tested({"run": "true", "coverage": ".unslop/out/none.xml"}, "HEAD")


def test_fetch_catalog_is_pinned() -> None:
    for tool in ("detekt", "pmd", "phpstan", "swiftlint"):
        item = catalog(tool)
        assert item.url.startswith("https://")
        assert len(item.sha256) == 64
    with pytest.raises(FetchError, match="unknown tool"):
        _ = catalog("nope")
