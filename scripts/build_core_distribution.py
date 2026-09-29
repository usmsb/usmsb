"""Build usmsb-core sdist and wheel from the canonical export in a temporary tree.

Install build, setuptools>=77, and wheel in the invoking Python 3.14 environment
first. This command does not install dependencies or use the SDK build tree.
"""

import argparse
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "packages" / "usmsb-core"


def build_distribution(out_dir: Path | str = ROOT / "dist" / "core") -> Path:
    """Build both archives and return the wheel; keep intermediates outside the repo."""
    out_dir = Path(out_dir).resolve()
    export = runpy.run_path(str(ROOT / "scripts" / "export_autonomy.py"))["export"]
    with tempfile.TemporaryDirectory(prefix="usmsb-core-build-") as temporary:
        project = Path(temporary)
        package = project / "src" / "usmsb_core"
        export(package)
        for name in ("pyproject.toml", "README.md"):
            shutil.copyfile(METADATA / name, project / name)
        # Use the same normalized license bytes as the exported manifest.
        shutil.copyfile(package / "LICENSE", project / "LICENSE")

        # Build backends launch their own Python processes. -E on this process
        # alone cannot protect them from a stale PYTHONHOME/PYTHONPATH.
        environment = {
            key: value for key, value in os.environ.items() if not key.upper().startswith("PYTHON")
        }
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(
            [
                sys.executable,
                "-E",
                "-B",
                "-m",
                "build",
                "--no-isolation",
                "--outdir",
                str(project / "dist"),
                str(project),
            ],
            cwd=project,
            env=environment,
            check=True,
        )
        wheels = list((project / "dist").glob("*.whl"))
        sdists = list((project / "dist").glob("*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise RuntimeError(f"Expected one wheel and sdist, found {len(wheels)}, {len(sdists)}")
        out_dir.mkdir(parents=True, exist_ok=True)
        destination = out_dir / wheels[0].name
        for artifact in (*sdists, *wheels):
            shutil.copyfile(artifact, out_dir / artifact.name)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist" / "core")
    args = parser.parse_args()
    print(build_distribution(args.out_dir))
