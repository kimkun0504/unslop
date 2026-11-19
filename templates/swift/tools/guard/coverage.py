import json
import sys
from pathlib import Path

MEASURED = ("Sources/Domain/", "Sources/CLI/")


def main(report: str) -> int:
    root = Path.cwd().resolve().as_posix() + "/"
    data = json.loads(Path(report).read_text())["data"][0]["files"]
    gaps = []
    measured = 0
    for entry in data:
        name = entry["filename"].removeprefix(root)
        if not name.startswith(MEASURED):
            continue
        measured += 1
        for kind in ("lines", "regions", "functions"):
            summary = entry["summary"][kind]
            if summary["covered"] != summary["count"]:
                gaps.append(f"{name}: {summary['covered']} of {summary['count']} {kind} covered")
    if measured == 0:
        print("coverage: no source files under Sources/Domain or Sources/CLI in the report")
        return 1
    if gaps:
        print("coverage below 100%:")
        print("\n".join(gaps))
        return 1
    print(f"coverage: 100% of lines, regions and functions in {measured} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
