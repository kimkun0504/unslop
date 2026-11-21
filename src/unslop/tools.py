import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from unslop.findings import table, text

NODE = resources.files("unslop") / "data" / "tools" / "node"


class ToolError(RuntimeError):
    pass


def python_tool(name: str) -> str:
    return shlex.quote(str(Path(sys.executable).parent / name))


def node_manifest() -> dict[str, object]:
    loaded: object = json.loads((NODE / "package.json").read_text())
    return table(loaded)


def node_version(package: str) -> str:
    manifest = node_manifest()
    for section in ("dependencies", "devDependencies"):
        version = table(manifest.get(section)).get(package)
        if version is not None:
            return text(version)
    message = f"{package} is not pinned in unslop's Node tools"
    raise ToolError(message)


def cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "unslop" / "node-tools"


def node_home() -> Path:
    lock = (NODE / "package-lock.json").read_bytes()
    return cache_root() / hashlib.sha256(lock).hexdigest()[:16]


def ensure_node() -> Path:
    home = node_home()
    if (home / "installed").is_file():
        return home
    npm = shutil.which("npm")
    if npm is None:
        message = "Node.js and npm are needed for knip and jscpd"
        raise ToolError(message)
    staging = home.with_name(f"{home.name}.partial")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    for name in ("package.json", "package-lock.json"):
        _ = (staging / name).write_bytes((NODE / name).read_bytes())
    command = [npm, "ci", "--omit=dev", "--ignore-scripts", "--no-audit", "--no-fund", "--silent"]
    result = subprocess.run(command, cwd=staging, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = f"could not install unslop's Node tools: {result.stderr[-1000:]}"
        raise ToolError(message)
    _ = (staging / "installed").write_text("ok\n")
    shutil.rmtree(home, ignore_errors=True)
    _ = staging.rename(home)
    return home


def node_tool(name: str) -> str:
    return f"{shlex.quote(sys.executable)} -m unslop.tools {name}"


def main(arguments: list[str]) -> int:
    name, *rest = arguments
    try:
        binary = ensure_node() / "node_modules" / ".bin" / name
    except ToolError as error:
        print(f"unslop: {error}", file=sys.stderr)
        return 127
    return subprocess.run([str(binary), *rest], check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
