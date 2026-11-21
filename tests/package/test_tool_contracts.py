import json
import shutil
from pathlib import Path

import pytest

from conftest import commit, write
from unslop import findings, gitops, slop, tools
from unslop.profiles import CONFIG, install_data, python
from unslop.ratchet import shell

needs_node = pytest.mark.skipif(shutil.which("npm") is None, reason="needs Node.js")


def run(command: str) -> None:
    result = shell(command)
    assert result.returncode in {0, 1}, result.stdout + result.stderr


def test_ruff_basedpyright_and_vulture_reports_parse(repo: Path) -> None:
    write(repo / "pyproject.toml", '[project]\nname = "a"\nversion = "1"\n')
    run("uv venv -q .venv")
    write(repo / "src/app/core.py", "import os\n\n\ndef helper(value):\n    return value + undefined_name\n")
    commit(repo, "root")
    plan = python("unslop")
    install_data("python")
    reports: dict[str, list[tuple[str, str, int]]] = {}
    for check in plan["checks"]:
        run(check["run"])
        content = Path(check["report"]).read_text()
        reports[check["name"]] = [(f.path, f.rule, f.line) for f in findings.PARSERS[check["format"]](content)]
    assert ("src/app/core.py", "F401", 1) in reports["ruff"]
    assert any(rule == "reportUndefinedVariable" for _, rule, _ in reports["basedpyright"])
    assert reports["vulture"] == [("src/app/core.py", "unused-function", 4)]
    assert Path(CONFIG, "ruff.toml").is_file()


def test_sqlfluff_report_parses(repo: Path) -> None:
    write(repo / "db/1.sql", "select a,b from t\n")
    commit(repo, "root")
    check = slop.sql_check(slop.Gates())
    assert check is not None
    run(check["run"])
    found = list(findings.PARSERS["sqlfluff"](Path(check["report"]).read_text()))
    assert {finding.rule for finding in found} >= {"LT01"}
    assert all(finding.path == "db/1.sql" for finding in found)


@needs_node
def test_knip_report_parses(repo: Path) -> None:
    write(repo / "package.json", json.dumps({"name": "a", "private": True, "type": "module"}))
    write(repo / "src/index.ts", 'import { used } from "./lib.js";\nconsole.log(used);\n')
    write(repo / "src/lib.ts", "export const used = 1;\nexport const spare = 2;\n")
    write(repo / "src/orphan.ts", "export const orphan = 3;\n")
    commit(repo, "root")
    run(f"{tools.node_tool('knip')} --reporter json --no-exit-code --no-progress > report.json")
    found = {(f.path, f.rule) for f in findings.PARSERS["knip"](Path("report.json").read_text())}
    assert ("src/lib.ts", "exports") in found
    assert ("src/orphan.ts", "files") in found


@needs_node
def test_jscpd_marks_only_new_clones(repo: Path) -> None:
    body = "".join(f"    total = total + item * {n} - {n + 1}\n" for n in range(12))
    write(repo / "a.py", f"def first(item):\n    total = 0\n{body}    return total\n")
    commit(repo, "root")
    since = gitops.git("rev-parse", "HEAD").strip()
    write(repo / "b.py", f"def second(item):\n    total = 0\n{body}    return total\n")
    assert not slop.duplication(since)
    commit(repo, "copy")
    assert slop.duplication(gitops.git("rev-parse", "HEAD").strip())


def test_node_tools_are_pinned_together() -> None:
    manifest = tools.node_manifest()
    lock = json.loads((tools.NODE / "package-lock.json").read_text())
    packages = lock["packages"]
    for section in ("dependencies", "devDependencies"):
        for name, version in findings.table(manifest.get(section)).items():
            assert packages[f"node_modules/{name}"]["version"] == version
    assert tools.node_version("@stryker-mutator/core") == tools.node_version("@stryker-mutator/vitest-runner")
    with pytest.raises(tools.ToolError):
        _ = tools.node_version("left-pad")
