"""Build the Python SDK/CLI and TypeScript client from this source snapshot.

Requires Python 3.12–3.13, uv, Node.js 22+, and npm. No service credentials or
private repository checkout are needed. Dependencies are fetched from the
configured package registries; this script never publishes a package.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    output = ROOT / "dist"
    if output.exists() and any(output.iterdir()):
        raise SystemExit("dist must be empty; preserve or move the previous build first")
    output.mkdir(exist_ok=True)
    python = ROOT / "packages/python"
    node = ROOT / "packages/typescript"
    # Hatchling includes a parent .gitignore in source archives. Build from
    # package-only inputs so checkout metadata cannot enter the distribution.
    with tempfile.TemporaryDirectory(prefix="evalrouter-python-build-") as temporary:
        staged = Path(temporary)
        for name in ("README.md", "LICENSE", "pyproject.toml"):
            shutil.copyfile(python / name, staged / name)
        shutil.copytree(python / "src", staged / "src")
        run("uv", "build", str(staged), "--no-sources", "--out-dir", str(output))
    run("npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund", cwd=node)
    run("npm", "run", "build", cwd=node)
    # The installable tarball contains only compiled client files. Source build
    # tooling stays in this repository and is never an npm install hook.
    with tempfile.TemporaryDirectory(prefix="evalrouter-client-pack-") as temporary:
        staged = Path(temporary)
        for name in ("README.md", "LICENSE"):
            shutil.copyfile(node / name, staged / name)
        shutil.copytree(node / "dist", staged / "dist")
        metadata = json.loads((node / "package.json").read_text())
        metadata.pop("scripts", None)
        metadata.pop("devDependencies", None)
        (staged / "package.json").write_text(json.dumps(metadata, indent=2) + "\n")
        run("npm", "pack", "--ignore-scripts", "--pack-destination", str(output), cwd=staged)
    artifacts = sorted(p for p in output.iterdir() if p.suffix in {".whl", ".gz", ".tgz"})
    if len(artifacts) != 3:
        raise SystemExit("Expected one wheel, one Python source archive, and one npm archive")
    manifest = {
        "schema_version": 1,
        "kind": "local_source_build",
        "artifacts": [
            {
                "filename": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
            for path in artifacts
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Built three local artifacts in dist/. No package was published.")


if __name__ == "__main__":
    main()
