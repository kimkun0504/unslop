import json
import os
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import unquote, urlparse

LINE = re.compile(r"^(?P<path>[^:\n]+):(?P<line>\d+):\d+: (?P<message>.*)$")
MSBUILD_LINE = re.compile(
    r"^(?P<path>[^(\n]+?)\((?P<line>\d+),\d+(?:,\d+,\d+)?\): "
    r"(?:warning|error) (?P<rule>[A-Za-z]+\d+): (?P<message>.*?)(?: \[[^\]]*\])?$"
)
COMPILER_LINE = re.compile(r"^(?P<path>[^:\n]+\.[A-Za-z]+):(?P<line>\d+):\d+: (?:warning|error): (?P<message>.*)$")
ELIXIR_WARNING = re.compile(r"^\s*warning: (?P<message>.*)$")
ELIXIR_LOCATION = re.compile(r"^\s*(?:└─ )?(?P<path>[^\s:]+\.exs?):(?P<line>\d+)(?::\d+)?:")
TERMINAL_CODES = re.compile(r"\x1b\]8;;[^\x1b]*\x1b\\|\x1b\[[0-9;?]*[A-Za-z]")
QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'|`[^`]*`|\d+")
SWIFT_GROUP = re.compile(r"\[#(?P<group>[A-Za-z]+)\]")
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


def shape(message: str) -> str:
    return QUOTED.sub("_", message).strip()


def cargo(report: str) -> Iterator[Finding]:
    for line in report.splitlines():
        if not line.startswith("{"):
            continue
        entry = cast("Json", json.loads(line))
        message = entry.get("message")
        if entry.get("reason") != "compiler-message" or not isinstance(message, dict):
            continue
        diagnostic = cast("Json", message)
        primary = [span for span in objects(diagnostic.get("spans")) if span.get("is_primary") is True]
        if not primary:
            continue
        text_ = text(diagnostic.get("message"))
        rule = text(field(diagnostic, "code", "code"), shape(text_))
        yield Finding(relative(text(primary[0].get("file_name"))), rule, number(primary[0].get("line_start")), text_)


def msbuild(report: str) -> Iterator[Finding]:
    seen: set[str] = set()
    for line in report.splitlines():
        match = MSBUILD_LINE.match(line.strip())
        if match is not None and line.strip() not in seen:
            seen.add(line.strip())
            yield Finding(relative(match["path"]), match["rule"], int(match["line"]), match["message"])


def compiler(report: str) -> Iterator[Finding]:
    seen: set[str] = set()
    for line in report.splitlines():
        match = COMPILER_LINE.match(line.strip())
        if match is not None and line.strip() not in seen:
            seen.add(line.strip())
            message = match["message"]
            group = SWIFT_GROUP.search(message)
            rule = group["group"] if group is not None else shape(message)
            yield Finding(relative(match["path"]), rule, int(match["line"]), message)


def elixir(report: str) -> Iterator[Finding]:
    pending: str | None = None
    for line in report.splitlines():
        warning = ELIXIR_WARNING.match(line)
        if warning is not None:
            pending = warning["message"]
            continue
        location = ELIXIR_LOCATION.match(line)
        if location is not None and pending is not None:
            yield Finding(relative(location["path"]), shape(pending), int(location["line"]), pending)
            pending = None


def phpstan(report: str) -> Iterator[Finding]:
    document = cast("Json", json.loads(report))
    for path, entry in table(document.get("files")).items():
        for message in objects(table(entry).get("messages")):
            text_ = text(message.get("message"))
            yield Finding(
                relative(path), text(message.get("identifier"), shape(text_)), number(message.get("line")), text_
            )


def rubocop(report: str) -> Iterator[Finding]:
    document = cast("Json", json.loads(report))
    for entry in objects(document.get("files")):
        for offense in objects(entry.get("offenses")):
            yield Finding(
                relative(text(entry.get("path"))),
                text(offense.get("cop_name"), "unnamed"),
                number(field(offense, "location", "start_line")),
                text(offense.get("message")),
            )


def credo(report: str) -> Iterator[Finding]:
    document = cast("Json", json.loads(report))
    for issue in objects(document.get("issues")):
        yield Finding(
            relative(text(issue.get("filename"))),
            text(issue.get("check"), "unnamed"),
            number(issue.get("line_no")),
            text(issue.get("message")),
        )


PARSERS: dict[str, Callable[[str], Iterator[Finding]]] = {
    "sarif": sarif,
    "pyright": pyright,
    "eslint": eslint,
    "tsc": tsc,
    "lines": lines,
    "cargo": cargo,
    "msbuild": msbuild,
    "compiler": compiler,
    "elixir": elixir,
    "phpstan": phpstan,
    "rubocop": rubocop,
    "credo": credo,
}
