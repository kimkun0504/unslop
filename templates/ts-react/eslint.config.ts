import comments from "@eslint-community/eslint-plugin-eslint-comments";
import tailwind from "eslint-plugin-better-tailwindcss";
import boundaries from "eslint-plugin-boundaries";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import { defineConfig } from "eslint/config";
import tseslint from "typescript-eslint";
import { noComments } from "./eslint-rules/no-comments";

export default defineConfig(
  { ignores: ["dist", "coverage", "reports", ".stryker-tmp", "node_modules"] },
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  reactHooks.configs.flat["recommended-latest"],
  jsxA11y.flatConfigs.strict,
  {
    languageOptions: { parserOptions: { projectService: true } },
    linterOptions: { noInlineConfig: true, reportUnusedDisableDirectives: "error" },
    plugins: {
      "@eslint-community/eslint-comments": comments,
      "better-tailwindcss": tailwind,
      boundaries,
      local: { rules: { "no-comments": noComments } },
    },
    settings: {
      "better-tailwindcss": { entryPoint: "src/styles.css" },
      "import/resolver": { node: { extensions: [".ts", ".tsx"] } },
      "boundaries/elements": [
        { type: "app", pattern: "src/app" },
        { type: "feature-ui", pattern: "src/features/*/ui", capture: ["feature"] },
        { type: "feature-domain", pattern: "src/features/*/domain", capture: ["feature"] },
        { type: "test-support", pattern: "src/test" },
      ],
    },
    rules: {
      "local/no-comments": "error",
      "@eslint-community/eslint-comments/no-use": ["error", { allow: [] }],
      "@typescript-eslint/ban-ts-comment": [
        "error",
        { "ts-expect-error": true, "ts-ignore": true, "ts-nocheck": true, "ts-check": false },
      ],
      "@typescript-eslint/consistent-type-assertions": ["error", { assertionStyle: "never" }],
      "@typescript-eslint/no-non-null-assertion": "error",
      "@typescript-eslint/switch-exhaustiveness-check": "error",
      "@typescript-eslint/explicit-module-boundary-types": "error",
      "@typescript-eslint/prefer-readonly": "error",
      "no-console": "error",
      "no-param-reassign": "error",
      eqeqeq: ["error", "always"],
      complexity: ["error", 10],
      "max-depth": ["error", 3],
      "max-params": ["error", 4],
      "max-lines": ["error", { max: 300, skipBlankLines: true }],
      "max-lines-per-function": ["error", { max: 60, skipBlankLines: true }],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            "**/utils",
            "**/utils/**",
            "**/helpers",
            "**/helpers/**",
            "**/common",
            "**/common/**",
            "**/shared",
            "**/shared/**",
            "./utils",
            "./helpers",
          ],
        },
      ],
      "no-restricted-syntax": [
        "error",
        { selector: "JSXAttribute[name.name='style']", message: "Use design tokens through Tailwind classes." },
        { selector: "ExportDefaultDeclaration", message: "Use named exports." },
      ],
      "better-tailwindcss/no-unknown-classes": "error",
      "better-tailwindcss/enforce-consistent-class-order": "error",
      "better-tailwindcss/no-duplicate-classes": "error",
      "better-tailwindcss/no-conflicting-classes": "error",
      "better-tailwindcss/no-deprecated-classes": "error",
      "better-tailwindcss/no-unnecessary-whitespace": "error",
      "better-tailwindcss/enforce-shorthand-classes": "error",
      "better-tailwindcss/no-restricted-classes": [
        "error",
        {
          restrict: [{ pattern: "\\[.*\\]", message: "Arbitrary values bypass the design tokens in src/styles.css." }],
        },
      ],
      "boundaries/no-unknown-files": "error",
      "boundaries/dependencies": [
        "error",
        {
          default: "disallow",
          policies: [
            { from: { element: { type: "app" } }, allow: { to: { element: { types: ["app", "feature-ui"] } } } },
            {
              from: { element: { type: "feature-ui" } },
              allow: { to: { element: { types: ["feature-ui", "feature-domain"] } } },
            },
            { from: { element: { type: "feature-domain" } }, allow: { to: { element: { type: "feature-domain" } } } },
            {
              from: { element: { type: "test-support" } },
              allow: { to: { element: { types: ["feature-ui", "feature-domain"] } } },
            },
          ],
        },
      ],
    },
  },
  {
    files: ["eslint.config.ts", "vite.config.ts", "eslint-rules/**"],
    rules: { "no-restricted-syntax": "off", "boundaries/no-unknown-files": "off" },
  },
);
