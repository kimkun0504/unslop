build_legacy() {
  mkdir -p src
  cat > package.json <<'JSON'
{
  "name": "legacy-ts",
  "private": true,
  "type": "module",
  "scripts": { "test": "vitest run" },
  "devDependencies": {
    "@eslint/js": "9.36.0",
    "@vitest/coverage-v8": "3.2.4",
    "eslint": "9.36.0",
    "prettier": "3.6.2",
    "typescript": "5.9.3",
    "vitest": "3.2.4"
  }
}
JSON
  printf '{ "compilerOptions": { "target": "es2022", "module": "esnext", "moduleResolution": "bundler", "strict": false, "noEmit": true }, "include": ["src"] }\n' > tsconfig.json
  printf 'import js from "@eslint/js";\nexport default [js.configs.recommended];\n' > eslint.config.js
  printf '// legacy\nexport function add(a, b) { return a + b }\nexport function first(items: string[]) { var unused = 1; return items[0].length }\n' > src/calc.ts
  printf 'import { expect, test } from "vitest";\nimport { add } from "./calc";\ntest("adds", () => { expect(add(1, 2)).toBe(3) });\n' > src/calc.test.ts
  printf 'node_modules/\n' > .gitignore
  npm install --no-audit --no-fund --silent
}
cases() {
  printf 'export const double = (value: number): number => value * 2;\n' > src/double.ts
  expect_fail "untested new file" "of changed lines must be covered"
  printf 'export const pick = (items: string[]): number => items[0].length;\n' > src/pick.ts
  printf 'import { expect, test } from "vitest";\nimport { pick } from "./pick";\n\ntest("picks", () => {\n  expect(pick(["ab"])).toBe(2);\n});\n' > src/pick.test.ts
  expect_fail "unchecked index access" "TS2532"
  printf 'export const one = 1; // note\n' > src/one.ts
  expect_fail "comment" "comments are forbidden"
  printf 'export const   one=1\n' > src/one.ts
  printf 'import { expect, test } from "vitest";\nimport { one } from "./one";\n\ntest("one", () => {\n  expect(one).toBe(1);\n});\n' > src/one.test.ts
  expect_fail "unformatted new file" "new file is not formatted"
  printf 'const x = 1;\nexport const y = 2;\n' > tool.js
  expect_fail "new ESLint finding" "no-unused-vars"
  printf 'export const double = (value: number): number => value * 2;\n' > src/double.ts
  printf 'import { expect, test } from "vitest";\nimport { double } from "./double";\n\ntest("doubles", () => {\n  expect(double(2)).toBe(4);\n});\n' > src/double.test.ts
  expect_pass "clean, tested new code"
  printf 'export const double = (value: number): number => value * 2;\nexport const triple = (value: number): number => value * 3;\n' > src/double.ts
  printf 'import { expect, test } from "vitest";\nimport { double, triple } from "./double";\n\ntest("doubles", () => {\n  expect(double(2)).toBe(4);\n  expect(triple(2)).toBeGreaterThan(0);\n});\n' > src/double.test.ts
  printf 'export const unusedHelper = (value: number): number => value + 1;\n' > src/helper.ts
  expect_fail "a file nothing imports" "\[files\]"
  jq '.version = "2.0.0"' package.json > package.json.next && mv package.json.next package.json
  expect_pass "a version bump in package.json"
  jq '.scripts.test = "true"' package.json > package.json.next && mv package.json.next package.json
  expect_fail "the test script changed in package.json" "changed outside its dependency sections"
  rm node_modules/.bin/tsc
  printf '#!/bin/sh\necho "tsc: cannot start" >&2\nexit 1\n' > node_modules/.bin/tsc
  chmod +x node_modules/.bin/tsc
  expect_fail "a check whose tool cannot start" "instead of trusting an empty result"
  ln -sf ../typescript/bin/tsc node_modules/.bin/tsc
}
