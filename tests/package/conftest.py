import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


def git(repo: Path, *arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=repo, capture_output=True, text=True, check=True).stdout


def commit(repo: Path, message: str = "change") -> None:
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "commit", "-qm", message)


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[Path]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    previous = Path.cwd()
    os.chdir(root)
    try:
        yield root
    finally:
        os.chdir(previous)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
