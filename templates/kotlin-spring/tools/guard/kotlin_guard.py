import sys
from pathlib import Path

import tree_sitter_kotlin
from tree_sitter import Language, Node, Parser

COMMENT_TYPES = {"comment", "line_comment", "block_comment", "multiline_comment"}
FORBIDDEN_CALLS = {"print", "println", "readLine", "TODO"}
PARSER = Parser(Language(tree_sitter_kotlin.language()))


def walk(root: Node) -> list[Node]:
    pending = [root]
    found: list[Node] = []
    while pending:
        node = pending.pop()
        found.append(node)
        pending.extend(node.children)
    return sorted(found, key=lambda n: n.start_byte)


def problem(node: Node, source: bytes) -> str | None:
    if node.type in COMMENT_TYPES:
        return "comments are forbidden (ADR-0001)"
    if node.type == "!!":
        return "the !! operator is forbidden; model absence with types"
    if node.type == "call_expression" and node.children:
        callee = source[node.children[0].start_byte : node.children[0].end_byte].decode()
        if callee.startswith("kotlin.io."):
            callee = callee.removeprefix("kotlin.io.")
        if callee in FORBIDDEN_CALLS:
            return f"{callee}() is forbidden; use the logger or a typed result"
    return None


def violations(path: Path) -> list[str]:
    source = path.read_bytes()
    tree = PARSER.parse(source)
    return [
        f"{path}:{node.start_point[0] + 1}:{node.start_point[1] + 1}: {message}"
        for node in walk(tree.root_node)
        if (message := problem(node, source)) is not None
    ]


def main(argv: list[str]) -> int:
    found = [v for arg in argv if arg.endswith((".kt", ".kts")) for v in violations(Path(arg))]
    _ = sys.stdout.write("".join(f"{v}\n" for v in found))
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
