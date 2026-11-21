import json
import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import unquote, urlparse

LINE = re.compile(r"^(?P<path>[^:\n]+):(?P<line>\d+):\d+: (?P<message>.*)$")
TERMINAL_CODES = re.compile(r"\x1b\]8;;[^\x1b]*\x1b\\|\x1b\[[0-9;?]*[A-Za-z]")
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'|`[^`]*`|\d+")
VULTURE_LINE = re.compile(
    r"^(?P<path>[^:\n]+):(?P<line>\d+): (?P<message>unused (?P<kind>function|class|method) '[^']*')"
)
KNIP_SKIPPED = frozenset({"file", "owners", "catalog", "catalogReferences"})
TSC_LINE = re.compile(r"^(?P<path>.+?)\((?P<line>\d+),\d+\): error (?P<rule>TS\d+): (?P<message>.*)$")

type Json = dict[str, object]


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    rule: str
    line: int
    message: str

    def render(self) -> str:
        return f"  {self.path}:{self.line}: [{self.rule}] {self.message}"


def relative(raw: str) -> str:
    text = unquote(urlparse(raw).path) if raw.startswith("file:") else raw
    path = Path(text)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    return Path(os.path.normpath(text)).as_posix()


def objects(value: object) -> list[Json]:
    return (
        [cast("Json", item) for item in cast("list[object]", value) if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def table(value: object) -> Json:
    return cast("Json", value) if isinstance(value, dict) else {}


def field(value: Json, *keys: str) -> object:
    current: object = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = table(cast("object", current)).get(key)
    return current


def text(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def number(value: object) -> int:
    return value if isinstance(value, int) else 0


def sarif(report: str) -> Iterator[Finding]:
    document = cast("Json", json.loads(report))
    for run in objects(document.get("runs")):
        for result in objects(run.get("results")):
            locations = objects(result.get("locations"))
            location = locations[0] if locations else {}
            uri = text(field(location, "physicalLocation", "artifactLocation", "uri"), "<unknown>")
            yield Finding(
                relative(uri),
                text(result.get("ruleId"), "unnamed"),
                number(field(location, "physicalLocation", "region", "startLine")),
                text(field(result, "message", "text")),
            )


def pyright(report: str) -> Iterator[Finding]:
    document = cast("Json", json.loads(report))
    for diagnostic in objects(document.get("generalDiagnostics")):
        yield Finding(
            relative(text(diagnostic.get("file"), "<unknown>")),
            text(diagnostic.get("rule"), text(diagnostic.get("severity"), "unnamed")),
            number(field(diagnostic, "range", "start", "line")) + 1,
            text(diagnostic.get("message")).splitlines()[0] if text(diagnostic.get("message")) else "",
        )


def eslint(report: str) -> Iterator[Finding]:
    for entry in objects(json.loads(report)):
        for message in objects(entry.get("messages")):
            yield Finding(
                relative(text(entry.get("filePath"), "<unknown>")),
                text(message.get("ruleId"), "fatal"),
                number(message.get("line")),
                text(message.get("message")),
            )


def tsc(report: str) -> Iterator[Finding]:
    for line in report.splitlines():
        match = TSC_LINE.match(line)
        if match is not None:
            yield Finding(relative(match["path"]), match["rule"], int(match["line"]), match["message"])


def lines(report: str) -> Iterator[Finding]:
    for line in report.splitlines():
        match = LINE.match(line)
        if match is not None:
            message = match["message"]
            yield Finding(relative(match["path"]), message.split(";")[0].split(" (")[0], int(match["line"]), message)


def vulture(report: str) -> Iterator[Finding]:
    for line in report.splitlines():
        match = VULTURE_LINE.match(line)
        if match is not None:
            yield Finding(relative(match["path"]), f"unused-{match['kind']}", int(match["line"]), match["message"])


def knip_items(value: object) -> list[Json]:
    if isinstance(value, dict):
        return [item for group in cast("dict[str, object]", value).values() for item in objects(group)]
    return objects(value)


def knip(report: str) -> Iterator[Finding]:
    document = cast("Json", json.loads(report))
    for issue in objects(document.get("issues")):
        path = relative(text(issue.get("file"), "<unknown>"))
        for category, value in issue.items():
            if category in KNIP_SKIPPED:
                continue
            for item in knip_items(value):
                name = text(item.get("name"))
                yield Finding(path, category, number(item.get("line")) or 1, f"unused {category}: {name}")


def sqlfluff(report: str) -> Iterator[Finding]:
    decoder = json.JSONDecoder()
    position = 0
    while position < len(report):
        if report[position].isspace():
            position += 1
            continue
        document, position = decoder.raw_decode(report, position)
        for entry in objects(document):
            path = relative(text(entry.get("filepath"), "<unknown>"))
            for violation in objects(entry.get("violations")):
                yield Finding(
                    path,
                    text(violation.get("code"), "unnamed"),
                    number(violation.get("start_line_no")),
                    text(violation.get("description")),
                )


def shape(message: str) -> str:
    return QUOTED.sub("_", message).strip()


PARSERS: dict[str, Callable[[str], Iterator[Finding]]] = {
    "sarif": sarif,
    "pyright": pyright,
    "eslint": eslint,
    "tsc": tsc,
    "lines": lines,
    "vulture": vulture,
    "knip": knip,
    "sqlfluff": sqlfluff,
}
