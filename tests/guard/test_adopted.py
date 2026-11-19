import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[2] / "adopt" / "shared" / ".unslop" / "guard" / "adopted.py"
spec = importlib.util.spec_from_file_location("adopted", GUARD)
assert spec is not None
assert spec.loader is not None
adopted = importlib.util.module_from_spec(spec)
sys.modules["adopted"] = adopted
spec.loader.exec_module(adopted)


def test_sarif_paths_become_repository_relative() -> None:
    absolute = (adopted.ROOT / "src" / "a.py").as_uri()
    report = {
        "runs": [
            {
                "results": [
                    {"ruleId": "T201", "message": {"text": "print"}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": absolute}, "region": {"startLine": 3}}}]},
                    {"ruleId": "E1", "message": {"text": "x"}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": "./lib/../b.py"}}}]},
                ]
            }
        ]
    }
    found = list(adopted.sarif(json.dumps(report)))
    assert [(f.path, f.rule, f.line) for f in found] == [("src/a.py", "T201", 3), ("b.py", "E1", 0)]


def test_pyright_eslint_and_tsc_reports_parse() -> None:
    pyright = {"generalDiagnostics": [{"file": "a.py", "rule": "reportReturnType", "range": {"start": {"line": 1}}, "message": "bad\nmore"}]}
    eslint = [{"filePath": "tool.js", "messages": [{"ruleId": None, "line": 2, "message": "parse"}]}]
    tsc = "src/a.ts(4,7): error TS2532: Object is possibly 'undefined'.\n  continuation\n"
    guard = "src/A.kt:5:5: println() is forbidden; use the logger\nnoise\n"
    found = [*adopted.pyright(json.dumps(pyright)), *adopted.eslint(json.dumps(eslint)), *adopted.tsc(tsc), *adopted.lines(guard)]
    assert [(f.path, f.rule, f.line, f.message) for f in found] == [
        ("a.py", "reportReturnType", 2, "bad"),
        ("tool.js", "fatal", 2, "parse"),
        ("src/a.ts", "TS2532", 4, "Object is possibly 'undefined'."),
        ("src/A.kt", "println() is forbidden", 5, "println() is forbidden; use the logger"),
    ]


def finding(path: str, rule: str, line: int = 1) -> object:
    return adopted.Finding(path, rule, line, "m")


def test_ratchet_allows_the_baseline_and_rejects_growth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    check = {"name": "lint"}
    (tmp_path / ".unslop" / "baseline").mkdir(parents=True)
    (tmp_path / ".unslop" / "baseline" / "lint.json").write_text(json.dumps({"a.py::R1": 2}))
    assert adopted.ratchet(check, [finding("a.py", "R1", 1), finding("a.py", "R1", 9)])
    assert not adopted.ratchet(check, [finding("a.py", "R1"), finding("a.py", "R1"), finding("a.py", "R1", 5)])
    assert not adopted.ratchet(check, [finding("b.py", "R1")])
    assert adopted.ratchet(check, [finding("a.py", "R1")])
    output = capsys.readouterr().out
    assert "a.py has 3 [R1] findings; the baseline allows 2" in output
    assert "b.py has 1 [R1] findings; the baseline allows 0" in output
    assert "1 recorded findings are fixed" in output


def test_patterns_match_paths_and_names() -> None:
    assert adopted.matches("src/deep/a.py", ["*.py"])
    assert adopted.matches(".unslop/guard/adopted.py", list(adopted.GUARD_PATHS))
    assert not adopted.matches("src/a.ts", ["*.py"])


def git(cwd: Path, *arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, text=True, check=True).stdout


def test_formatting_is_required_only_where_it_was_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(tmp_path)
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "a@b")
    git(tmp_path, "config", "user.name", "a")
    (tmp_path / "tidy.txt").write_text("tidy\n")
    (tmp_path / "messy.txt").write_text("MESSY\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    base = git(tmp_path, "rev-parse", "HEAD").strip()
    rule = {"name": "lower", "glob": ["*.txt"], "run": "tr A-Z a-z"}
    (tmp_path / "messy.txt").write_text("MESSY\nMORE\n")
    assert adopted.formatted(rule, base)
    (tmp_path / "tidy.txt").write_text("tidy\nBROKEN\n")
    (tmp_path / "new.txt").write_text("NEW\n")
    assert not adopted.formatted(rule, base)
    output = capsys.readouterr().out
    assert "tidy.txt: was formatted before this change and is not now" in output
    assert "new.txt: new file is not formatted" in output
    assert "messy.txt" not in output


def test_a_broken_tool_is_not_mistaken_for_a_clean_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    report = ".unslop/out/tsc.txt"
    broken = {"name": "tsc", "format": "tsc", "report": report, "run": f"echo 'tsc: not found' >&2; exit 127 > {report}; : > {report}; exit 127"}
    with pytest.raises(adopted.BrokenCheckError, match="exit code 127"):
        adopted.collect(broken)
    clean = {"name": "tsc", "format": "tsc", "report": report, "run": f": > {report}"}
    assert adopted.collect(clean) == []
    found = {"name": "tsc", "format": "tsc", "report": report, "run": f"echo 'a.ts(1,1): error TS1: x' > {report}; exit 2"}
    assert [f.rule for f in adopted.collect(found)] == ["TS1"]
    invalid = {"name": "lint", "format": "sarif", "report": ".unslop/out/lint.sarif", "run": "printf 'oops' > .unslop/out/lint.sarif"}
    with pytest.raises(adopted.BrokenCheckError, match="not valid JSON"):
        adopted.collect(invalid)
    missing = {"name": "lint", "format": "sarif", "report": ".unslop/out/none.sarif", "run": "true"}
    with pytest.raises(adopted.BrokenCheckError, match="wrote no report"):
        adopted.collect(missing)


def test_cargo_messages_use_the_lint_name_and_primary_span() -> None:
    lines = [
        json.dumps({"reason": "compiler-artifact"}),
        json.dumps(
            {
                "reason": "compiler-message",
                "message": {
                    "message": "used `unwrap()` on a `Result` value",
                    "code": {"code": "clippy::unwrap_used"},
                    "spans": [{"file_name": "src/lib.rs", "line_start": 7, "is_primary": True}],
                },
            }
        ),
        json.dumps(
            {
                "reason": "compiler-message",
                "message": {
                    "message": "unused variable: `x`",
                    "code": None,
                    "spans": [{"file_name": "src/main.rs", "line_start": 2, "is_primary": True}],
                },
            }
        ),
        json.dumps({"reason": "compiler-message", "message": {"message": "2 warnings emitted", "code": None, "spans": []}}),
        "Finished dev profile",
    ]
    found = list(adopted.cargo("\n".join(lines)))
    assert [(f.path, f.rule, f.line) for f in found] == [("src/lib.rs", "clippy::unwrap_used", 7), ("src/main.rs", "unused variable: _", 2)]


def test_msbuild_and_compiler_lines_parse_once_each() -> None:
    build = (
        "/w/src/Api/Quote.cs(12,9): warning CA1822: Member 'Total' does not access instance data [/w/src/Api/Api.csproj]\n"
        "/w/src/Api/Quote.cs(12,9): warning CA1822: Member 'Total' does not access instance data [/w/src/Api/Api.csproj]\n"
        "  Api -> /w/bin/Api.dll\n"
    )
    swift = (
        "Sources/Domain/Money.swift:4:9: warning: var 'count' is not concurrency-safe [#MutableGlobalVariable]\n"
        "Sources/Domain/Money.swift:9:5: warning: initialization of immutable value 'x' was never used\n"
    )
    assert [(f.path, f.rule, f.line) for f in adopted.msbuild(build)] == [("/w/src/Api/Quote.cs", "CA1822", 12)]
    assert [(f.path, f.rule) for f in adopted.compiler(swift)] == [
        ("Sources/Domain/Money.swift", "MutableGlobalVariable"),
        ("Sources/Domain/Money.swift", "initialization of immutable value _ was never used"),
    ]


def test_elixir_warnings_pair_with_their_location() -> None:
    report = (
        '    warning: variable "x" is unused (prefix it with an underscore)\n'
        "    │\n"
        "  3 │   def f(x), do: 1\n"
        "    │\n"
        "    └─ lib/legacy.ex:3:9: Legacy.f/1\n"
        "\n"
        "warning: function g/0 is unused\n"
        "  lib/legacy.ex:8: Legacy (module)\n"
    )
    found = list(adopted.elixir(report))
    assert [(f.path, f.rule, f.line) for f in found] == [
        ("lib/legacy.ex", "variable _ is unused (prefix it with an underscore)", 3),
        ("lib/legacy.ex", "function g/_ is unused", 8),
    ]


def test_phpstan_rubocop_and_credo_reports_parse() -> None:
    phpstan = {"files": {"src/Calc.php": {"messages": [{"message": "Missing type", "line": 4, "identifier": "missingType.parameter"}]}}}
    rubocop = {"files": [{"path": "lib/calc.rb", "offenses": [{"cop_name": "Style/StringLiterals", "message": "quotes", "location": {"start_line": 2}}]}]}
    credo = {"issues": [{"filename": "lib/a.ex", "line_no": 5, "check": "Credo.Check.Readability.Specs", "message": "spec"}]}
    found = [*adopted.phpstan(json.dumps(phpstan)), *adopted.rubocop(json.dumps(rubocop)), *adopted.credo(json.dumps(credo))]
    assert [(f.path, f.rule, f.line) for f in found] == [
        ("src/Calc.php", "missingType.parameter", 4),
        ("lib/calc.rb", "Style/StringLiterals", 2),
        ("lib/a.ex", "Credo.Check.Readability.Specs", 5),
    ]


def test_terminal_colour_codes_are_stripped_before_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    line = "Sources/A.swift:3:9: \x1b[1;33mwarning: \x1b[1;39mvalue 'x' was never used\x1b[0;0m [#\x1b]8;;https://x\x1b\\NoUsage\x1b]8;;\x1b\\]"
    report = ".unslop/out/build.txt"
    (tmp_path / "sample.txt").write_text(line + "\n")
    check = {"name": "compiler", "format": "compiler", "report": report, "run": f"cp sample.txt {report}"}
    assert [(f.path, f.rule, f.line) for f in adopted.collect(check)] == [("Sources/A.swift", "NoUsage", 3)]
