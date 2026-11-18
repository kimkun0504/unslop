import sys
from pathlib import Path

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

COMMENT_TYPES = {"comment", "line_comment", "block_comment", "multiline_comment"}
PARSER = Parser(Language(tree_sitter_kotlin.language()))


def comment_nodes(root: Node) -> list[Node]:
    pending = [root]
    found: list[Node] = []
    while pending:
        node = pending.pop()
        if node.type in COMMENT_TYPES:
            found.append(node)
        pending.extend(node.children)
    return found


def violations(path: Path) -> list[str]:
    tree = PARSER.parse(path.read_bytes())
    return [
        f"{path}:{node.start_point[0] + 1}:{node.start_point[1] + 1}: comments are forbidden (ADR-0001)"
        for node in sorted(comment_nodes(tree.root_node), key=lambda n: n.start_byte)
    ]


def main(argv: list[str]) -> int:
    found = [v for arg in argv if arg.endswith((".kt", ".kts")) for v in violations(Path(arg))]
    _ = sys.stdout.write("".join(f"{v}\n" for v in found))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
