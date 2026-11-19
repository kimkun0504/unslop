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
  expect_fail "untested new file" "every changed line must be covered"
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
}
