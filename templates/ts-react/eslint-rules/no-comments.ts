import type { Rule } from "eslint";

const tripleSlashReference = /^\/\s*<reference\s/;

export const noComments: Rule.RuleModule = {
  meta: {
    type: "problem",
    schema: [],
    messages: {
      banned: "Comments are forbidden (ADR-0001): encode intent in names, types, tests or a decision record.",
    },
  },
  create(context) {
    return {
      Program() {
        for (const comment of context.sourceCode.getAllComments()) {
          const kind: string = comment.type;
          const isAllowedDirective = kind === "Line" && tripleSlashReference.test(comment.value);
          if (kind !== "Shebang" && !isAllowedDirective && comment.loc) {
            context.report({ loc: comment.loc, messageId: "banned" });
          }
        }
      },
    };
  },
};
