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
  expect_fail "untested new code" "every changed line must be covered"
  printf 'def f( x ):\n    return x\n' > src/legacy/ugly.py
  expect_fail "unformatted new file" "new file is not formatted"
  printf 'import pytest\n\n\n@pytest.mark.skip\ndef test_later() -> None:\n    assert True\n' > tests/test_later.py
  expect_fail "skipped test" "new skip or suppression"
  printf 'from legacy.calc import add\n\ndef test_add():\n    assert add(1, 2) == 4\n' > tests/test_calc.py
  expect_fail "edited existing test" "existing tests were modified"
  sed -i 's/return a+b/return a + b/' src/legacy/calc.py
  expect_pass "touching a covered legacy line"
}
