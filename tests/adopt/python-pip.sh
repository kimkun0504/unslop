build_legacy() {
  mkdir -p src/legacy tests
  cat > pyproject.toml <<'TOML'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "legacy"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["python-dateutil>=2.8"]

[project.optional-dependencies]
dev = ["pytest>=7"]

[tool.hatch.build.targets.wheel]
packages = ["src/legacy"]
TOML
  : > src/legacy/__init__.py
  printf 'from dateutil import parser\n\n\ndef year(text):\n    return parser.parse(text).year\n' > src/legacy/dates.py
  printf 'from legacy.dates import year\n\n\ndef test_year():\n    assert year("2026-11-19") == 2026\n' > tests/test_dates.py
  printf '.venv/\n__pycache__/\n' > .gitignore
}
cases() {
  printf 'from dateutil import parser\n\n\ndef month(text: str) -> int:\n    return parser.parse(text).month\n' > src/legacy/months.py
  printf 'from legacy.months import month\n\n\ndef test_month() -> None:\n    assert month("2026-11-19") == 11\n' > tests/test_months.py
  expect_pass "new code using a third-party dependency"
  printf 'from pathlib import Path\n\nfrom legacy.dates import year\n\n\ndef test_year():\n    assert year("2026-11-19") == 2026\n\n\ndef test_year_from_file(tmp_path: Path) -> None:\n    source = tmp_path / "d.txt"\n    _ = source.write_text("2025-01-02")\n    assert year(source.read_text()) == 2025\n' > tests/test_dates.py
  expect_pass "a test appended to an existing file with its import"
  printf 'from legacy.dates import year\n\n\ndef test_year():\n    assert year("2026-11-19") > 0\n' > tests/test_dates.py
  expect_fail "a weakened existing test" "existing tests were modified"
}
