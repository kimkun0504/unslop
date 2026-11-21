stacks() {
  echo "--stack python --stack typescript:web"
}
build_legacy() {
  mkdir -p src/legacy tests web/src
  cat > pyproject.toml <<'TOML'
[project]
name = "legacy"
version = "0.1.0"
requires-python = ">=3.12"

[tool.setuptools.packages.find]
where = ["src"]
TOML
  printf 'def total(items):\n    return sum(items)\n' > src/legacy/__init__.py
  printf 'from legacy import total\n\n\ndef test_total():\n    assert total([1, 2]) == 3\n' > tests/test_total.py
  cat > web/package.json <<'JSON'
{
  "name": "legacy-web",
  "private": true,
  "type": "module",
  "devDependencies": {
    "@vitest/coverage-v8": "3.2.4",
    "typescript": "5.9.3",
    "vitest": "3.2.4"
  }
}
JSON
  printf '{ "compilerOptions": { "target": "es2022", "module": "esnext", "moduleResolution": "bundler", "strict": false, "noEmit": true }, "include": ["src"] }\n' > web/tsconfig.json
  printf 'export function add(a, b) { return a + b }\n' > web/src/calc.ts
  printf 'import { expect, test } from "vitest";\nimport { add } from "./calc";\ntest("adds", () => { expect(add(1, 2)).toBe(3) });\n' > web/src/calc.test.ts
  printf 'node_modules/\n*.egg-info/\n__pycache__/\n' > .gitignore
  (cd web && npm install --no-audit --no-fund --silent)
}
cases() {
  printf 'export const half = (value: number): number => value / 2;\n' > web/src/half.ts
  expect_fail "untested front-end file" "of changed lines must be covered"
  printf 'export const n: number = "text";\n' > web/src/wrong.ts
  printf 'import { expect, test } from "vitest";\nimport { n } from "./wrong";\n\ntest("n", () => {\n  expect(n).toBeDefined();\n});\n' > web/src/wrong.test.ts
  expect_fail "front-end type error" "web:tsc: web/src/wrong.ts has 1"
  printf 'export const half = (value: number): number => value / 2;\n' > web/src/half.ts
  printf 'import { expect, test } from "vitest";\nimport { half } from "./half";\n\ntest("halves", () => {\n  expect(half(4)).toBe(2);\n});\n' > web/src/half.test.ts
  expect_pass "tested front-end file"
  printf 'def double(value: int) -> int:\n    return value * 2\n' > src/legacy/double.py
  expect_fail "untested back-end file" "of changed lines must be covered"
  printf 'def total(items):\n    return sum(items)  # adds\n' > src/legacy/__init__.py
  expect_fail "back-end comment" "comments are forbidden"
  printf 'def double(value: int) -> int:\n    return value * 2\n' > src/legacy/double.py
  printf 'from legacy.double import double\n\n\ndef test_double() -> None:\n    assert double(2) == 4\n' > tests/test_double.py
  expect_pass "tested back-end file"
}
