build_legacy() {
  mkdir -p src/legacy tests
  cat > pyproject.toml <<'TOML'
[project]
name = "legacy"
version = "0.1.0"
requires-python = ">=3.12"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
TOML
  : > src/legacy/__init__.py
  printf 'import os, sys\n# legacy comment\n\n\ndef add(a, b):\n    print("adding")\n    return a+b\n\ndef unused(x):\n    try:\n        return 1/x\n    except:\n        pass\n' > src/legacy/calc.py
  printf 'from legacy.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n' > tests/test_calc.py
  printf '.venv/\n__pycache__/\n' > .gitignore
  uv lock -q
}
cases() {
  printf '\n\ndef mul(a: int, b: int) -> int:\n    return a * b  # new\n' >> src/legacy/calc.py
  expect_fail "comment on an added line" "comments are forbidden"
  printf 'def shout(word: str) -> str:\n    print(word)\n    return word.upper()\n' > src/legacy/extra.py
  printf 'from legacy.extra import shout\n\n\ndef test_shout() -> None:\n    assert shout("a") == "A"\n' > tests/test_extra.py
  expect_fail "print in new code" "\[T201\]"
  printf 'def half(value: int) -> int:\n    return value / 2\n' > src/legacy/typed.py
  expect_fail "type error in new code" "reportReturnType"
  printf 'def triple(value: int) -> int:\n    return value * 3\n' > src/legacy/uncovered.py
  expect_fail "untested new code" "of changed lines must be covered"
  printf 'def f( x ):\n    return x\n' > src/legacy/ugly.py
  expect_fail "unformatted new file" "new file is not formatted"
  printf 'import pytest\n\n\n@pytest.mark.skip\ndef test_later() -> None:\n    assert True\n' > tests/test_later.py
  expect_fail "skipped test" "new skip or suppression"
  printf 'from legacy.calc import add\n\ndef test_add():\n    assert add(1, 2) == 4\n' > tests/test_calc.py
  expect_fail "edited existing test" "existing tests were modified"
  sed -i 's/return a+b/return a + b/' src/legacy/calc.py
  expect_pass "touching a covered legacy line"
  printf 'def orphan(value: int) -> int:\n    return value * 5\n' > src/legacy/orphan.py
  expect_fail "unused new function" "\[unused-function\]"
  body='    total = 0\n    for item in items:\n        if item > 10:\n            total += item * 2 - 1\n        else:\n            total += item + 3\n    return total\n'
  printf 'def score(items: list[int]) -> int:\n%b\n\ndef rank(items: list[int]) -> int:\n%b' "$body" "$body" > src/legacy/twice.py
  printf 'from legacy.twice import rank, score\n\n\ndef test_twice() -> None:\n    assert score([1, 20]) == rank([1, 20])\n' > tests/test_twice.py
  expect_fail "copy-pasted function" "copy-pasted code"
  mkdir -p db && printf 'select a,b from t;\n' > db/report.sql
  expect_fail "badly formatted SQL" "\[LT01\]"
  sed -i 's/version = "0.1.0"/version = "0.1.1"/' pyproject.toml
  expect_pass "a version bump in pyproject.toml"
  printf '\n[tool.pytest.ini_options]\naddopts = "-q"\n' >> pyproject.toml
  expect_fail "test settings changed in pyproject.toml" "changed outside its dependency sections"
}
