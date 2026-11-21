import json
import re

from unslop import footprint, project
from unslop.findings import table

ACTION_LINE = re.compile(rf"(uses:\s*{re.escape(footprint.REPOSITORY)}@)\S+")
BARE_TRIGGER = re.compile(r"^(\s*)pull_request:[ \t]*$(?!\n\1[ \t]+\S)", re.MULTILINE)
LABEL_TYPES = "[opened, synchronize, reopened, labeled, unlabeled]"


class UpgradeError(Exception):
    pass


def marketplace_ref() -> str | None:
    if not footprint.SETTINGS.is_file():
        return None
    settings = table(json.loads(footprint.SETTINGS.read_text()))
    source = table(table(table(settings.get("extraKnownMarketplaces")).get(footprint.MARKETPLACE)).get("source"))
    ref = source.get("ref")
    return ref if isinstance(ref, str) else None


def workflow_ref() -> str | None:
    if not footprint.WORKFLOW.is_file():
        return None
    found = ACTION_LINE.search(footprint.WORKFLOW.read_text())
    return found.group(0).rsplit("@", 1)[1] if found else None


def set_workflow_ref(ref: str) -> None:
    content = footprint.WORKFLOW.read_text()
    updated, count = ACTION_LINE.subn(lambda match: f"{match.group(1)}{ref}", content)
    if count == 0:
        message = f"{footprint.WORKFLOW} has no `uses: {footprint.REPOSITORY}@…` step to update"
        raise UpgradeError(message)
    _ = footprint.WORKFLOW.write_text(updated)


def rerun_on_labels() -> bool:
    content = footprint.WORKFLOW.read_text()
    types = f"  types: {LABEL_TYPES}"
    updated, count = BARE_TRIGGER.subn(lambda found: f"{found.group(0)}\n{found.group(1)}{types}", content)
    if count:
        _ = footprint.WORKFLOW.write_text(updated)
    return bool(count)


READ_ONLY = re.compile(r"^(?P<indent>[ \t]*)contents: read[ \t]*$", re.MULTILINE)


def allow_label_edits() -> bool:
    content = footprint.WORKFLOW.read_text()
    if "pull-requests: write" in content:
        return False
    updated, count = READ_ONLY.subn(
        lambda found: f"{found.group(0)}\n{found.group('indent')}pull-requests: write", content, 1
    )
    if count:
        _ = footprint.WORKFLOW.write_text(updated)
    return bool(count)


def upgrade(version: str) -> list[str]:
    config = project.load()
    if not footprint.SETTINGS.is_file() or not footprint.WORKFLOW.is_file():
        message = f"expected {footprint.SETTINGS} and {footprint.WORKFLOW}; run `unslop init` to create them"
        raise UpgradeError(message)
    ref = footprint.action_ref(version)
    if ref == f"v{version}":
        message = f"v{version} is not tagged on github.com/{footprint.REPOSITORY} yet, so nothing can pin it"
        raise UpgradeError(message)
    changes: list[str] = []
    if config.version != version:
        changes.append(f"unslop.toml: {config.version} -> {version}")
        config.version = version
        project.save(config)
    before = footprint.SETTINGS.read_text()
    footprint.write_settings(version, [stack.path for stack in config.stacks])
    if footprint.SETTINGS.read_text() != before:
        changes.append(f"{footprint.SETTINGS}: plugin pinned to v{version}, protected files refreshed")
    if workflow_ref() != ref:
        changes.append(f"{footprint.WORKFLOW}: action {workflow_ref()} -> {ref}")
        set_workflow_ref(ref)
    if rerun_on_labels():
        changes.append(f"{footprint.WORKFLOW}: pull requests rerun when a label is added or removed")
    if allow_label_edits():
        changes.append(f"{footprint.WORKFLOW}: the check can remove a review label that new commits made stale")
    return changes
