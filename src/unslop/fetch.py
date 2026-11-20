import hashlib
import os
import platform
import shutil
import stat
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

SWIFTLINT = "https://github.com/realm/SwiftLint/releases/download/0.65.1"


@dataclass(frozen=True, slots=True)
class Download:
    url: str
    sha256: str
    name: str
    inner: str | None = None


class FetchError(Exception):
    pass


def swiftlint() -> Download:
    system, machine = platform.system(), platform.machine()
    if system == "Linux" and machine == "x86_64":
        return Download(
            f"{SWIFTLINT}/swiftlint_linux_amd64.zip",
            "caeed6f4a679c35539ffaf124f6c4ab4a8416917f7d8796279dc52b74026059d",
            "swiftlint.zip",
            "swiftlint",
        )
    if system == "Linux" and machine in {"aarch64", "arm64"}:
        return Download(
            f"{SWIFTLINT}/swiftlint_linux_arm64.zip",
            "9ffa52f478e6d8eb485d37d14715ffac90abc81c58f3370d598bf75be05605f8",
            "swiftlint.zip",
            "swiftlint",
        )
    if system == "Darwin":
        return Download(
            f"{SWIFTLINT}/portable_swiftlint.zip",
            "c1e429b0599cf1b516f369a2d9ec04eaf0e436f3c12b637df8851fa52ff694d0",
            "swiftlint.zip",
            "swiftlint",
        )
    message = f"no SwiftLint build for {system}-{machine}"
    raise FetchError(message)


def catalog(tool: str) -> Download:
    known = {
        "detekt": Download(
            "https://github.com/detekt/detekt/releases/download/v1.23.8/detekt-cli-1.23.8-all.jar",
            "2ce2ff952e150baf28a29cda70a363b0340b3e81a55f43e51ec5edffc3d066c1",
            "detekt-cli.jar",
        ),
        "pmd": Download(
            "https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.29.0/pmd-dist-7.29.0-bin.zip",
            "d27177c185b837fa57f097e482d1253468aa035379c5eb2671fa0a279109b179",
            "pmd.zip",
            "pmd-bin-7.29.0/bin/pmd",
        ),
        "phpstan": Download(
            "https://github.com/phpstan/phpstan/releases/download/2.3.7/phpstan.phar",
            "87fa9aa451bb9b61d7c65d40ec7d14d5bab67e3ad74ce75a09b3140d6f22631a",
            "phpstan.phar",
        ),
    }
    if tool == "swiftlint":
        return swiftlint()
    if tool not in known:
        message = f"unknown tool {tool}; known: {', '.join([*sorted(known), 'swiftlint'])}"
        raise FetchError(message)
    return known[tool]


def cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "unslop"


def download(item: Download, target: Path) -> None:
    if not item.url.startswith("https://"):
        message = f"refusing to download {item.url} over anything but https"
        raise FetchError(message)
    partial = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    with urllib.request.urlopen(item.url, timeout=120) as response, partial.open("wb") as sink:
        while chunk := response.read(1 << 20):
            digest.update(chunk)
            _ = sink.write(chunk)
    if digest.hexdigest() != item.sha256:
        partial.unlink()
        message = f"checksum mismatch for {item.url}"
        raise FetchError(message)
    _ = partial.replace(target)


def unpack(archive: Path, inner: str) -> Path:
    unpacked = archive.parent / "unpacked"
    if not unpacked.is_dir():
        staging = archive.parent / "unpacked.part"
        shutil.rmtree(staging, ignore_errors=True)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(staging)
        _ = staging.replace(unpacked)
    binary = unpacked / inner
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return binary


def fetch(tool: str) -> Path:
    item = catalog(tool)
    directory = cache_root() / item.sha256
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / item.name
    if not target.is_file():
        download(item, target)
    return target if item.inner is None else unpack(target, item.inner)
