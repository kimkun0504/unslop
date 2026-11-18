import io
import sys

import pytest

from app.api.cli import EXIT_OK, EXIT_USAGE, main, run


def call(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, out, err)
    return code, out.getvalue(), err.getvalue()


def test_prints_the_quote() -> None:
    assert call(["60", "40"]) == (EXIT_OK, "subtotal=100.00 tier=SILVER total=95.00\n", "")


def test_rejects_missing_amounts() -> None:
    assert call([]) == (EXIT_USAGE, "", "usage: app AMOUNT [AMOUNT ...]\n")


def test_rejects_malformed_amounts() -> None:
    code, out, err = call(["1.5"])
    assert (code, out) == (EXIT_USAGE, "")
    assert "1.5" in err


def test_run_reads_process_arguments(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["app", "500"])
    assert run() == EXIT_OK
    assert capsys.readouterr().out == "subtotal=500.00 tier=GOLD total=450.00\n"


def test_run_reports_errors_on_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["app", "1.5"])
    assert run() == EXIT_USAGE
    captured = capsys.readouterr()
    assert (captured.out, "'1.5'" in captured.err) == ("", True)
