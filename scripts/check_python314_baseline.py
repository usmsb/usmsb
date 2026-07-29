#!/usr/bin/env python3.14
"""Enforce the supported Python 3.14 runtime across USMSB release surfaces."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_IMAGE = (
    "public.ecr.aws/docker/library/python:3.14-slim-bookworm@"
    "sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30"
)
DOCKERFILES = (
    ROOT / "Dockerfile",
    ROOT / "Dockerfile.dev",
    ROOT / "docker" / "Dockerfile.node",
    ROOT / "src" / "usmsb_sdk" / "agent_sdk" / "templates" / "Dockerfile.agent",
)
PROJECT_FILES = (
    ROOT / "pyproject.toml",
    ROOT / "dist-inference" / "pyproject.toml",
    ROOT
    / "src"
    / "usmsb_sdk"
    / "agent_skill"
    / "usmsb-agent-platform"
    / "pyproject.toml",
)
PACKAGE_METADATA_FILES = (
    ROOT / "src" / "usmsb_sdk.egg-info" / "PKG-INFO",
    ROOT / "dist-inference" / "usmsb_dist_inference.egg-info" / "PKG-INFO",
    ROOT
    / "src"
    / "usmsb_sdk"
    / "agent_skill"
    / "usmsb-agent-platform"
    / "src"
    / "usmsb_agent_platform.egg-info"
    / "PKG-INFO",
)
LEGACY_CLASSIFIER = re.compile(
    r"Programming Language :: Python :: 3\.(?:8|9|10|11|12|13)"
)
LEGACY_DOCUMENTATION_TARGET = re.compile(
    r'(?:Python(?:版本)?(?:\s*\|\s*|\s+)|FROM\s+python:|"python":\s*")'
    r"3\.(?:8|9|10|11|12|13)",
    re.IGNORECASE,
)


def main() -> int:
    errors: list[str] = []
    if (ROOT / ".python-version").read_text(encoding="utf-8").strip() != "3.14":
        errors.append(".python-version must contain exactly 3.14")

    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    if 'PYTHON_VERSION: "3.14"' not in workflow:
        errors.append("test workflow must pin PYTHON_VERSION to 3.14")
    if "check_python314_baseline.py" not in workflow:
        errors.append("test workflow must run the Python 3.14 baseline guard")

    for path in DOCKERFILES:
        text = path.read_text(encoding="utf-8")
        bases = re.findall(r"^FROM\s+(\S+)", text, flags=re.MULTILINE)
        if not bases or bases[0] != PYTHON_IMAGE or any(
            base not in {PYTHON_IMAGE, "base"} for base in bases[1:]
        ):
            errors.append(f"{path.relative_to(ROOT)} must use the pinned Python 3.14 base")

    node_dockerfile = (ROOT / "docker" / "Dockerfile.node").read_text(encoding="utf-8")
    if 'CMD ["python3.14", "-m", "usmsb_sdk.api.rest.main"]' not in node_dockerfile:
        errors.append("docker/Dockerfile.node must start the existing Python 3.14 REST module")

    node_compose = (ROOT / "docker" / "docker-compose.nodes.yml").read_text(
        encoding="utf-8"
    )
    if node_compose.count("dockerfile: docker/Dockerfile.node") != 3:
        errors.append("node compose services must reference docker/Dockerfile.node")
    if node_compose.count("http://localhost:8000/api/health/live") != 3:
        errors.append("node compose health checks must use /api/health/live")

    for path in PROJECT_FILES:
        text = path.read_text(encoding="utf-8")
        if 'requires-python = ">=3.14,<3.15"' not in text:
            errors.append(f"{path.relative_to(ROOT)} must require Python 3.14")
        if re.search(r"\bpy3(?:10|11|12|13)\b|python_version\s*=\s*\"3\.(?:10|11|12|13)\"", text):
            errors.append(f"{path.relative_to(ROOT)} contains a legacy Python target")

    for path in PACKAGE_METADATA_FILES:
        text = path.read_text(encoding="utf-8")
        if "Requires-Python: <3.15,>=3.14" not in text:
            errors.append(f"{path.relative_to(ROOT)} must require Python 3.14")
        if LEGACY_CLASSIFIER.search(text):
            errors.append(f"{path.relative_to(ROOT)} contains a legacy Python classifier")

    documentation_roots = (
        ROOT / "docs",
        ROOT / "frontend" / "public" / "docs",
        ROOT / "src" / "usmsb_sdk" / "agent_skill" / "usmsb-agent-platform",
    )
    for documentation_root in documentation_roots:
        for path in documentation_root.rglob("*.md"):
            if "tests" in path.parts or "node_modules" in path.parts:
                continue
            # Some documentation aliases are tracked symlinks. Their canonical
            # source is scanned under ``docs``; do not make the baseline depend
            # on a developer-machine-specific or temporarily unavailable target.
            if path.is_symlink():
                continue
            if LEGACY_DOCUMENTATION_TARGET.search(path.read_text(encoding="utf-8")):
                errors.append(
                    f"{path.relative_to(ROOT)} contains a legacy Python documentation target"
                )

    for path in ROOT.rglob("*.py"):
        if any(
            part in {
                ".git",
                ".venv",
                ".claude",
                "skills",
                "node_modules",
                "__pycache__",
            }
            for part in path.parts
        ):
            continue
        first_line = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
        if first_line and first_line[0].startswith("#!") and "python" in first_line[0]:
            if first_line[0] != "#!/usr/bin/env python3.14":
                errors.append(f"{path.relative_to(ROOT)} has an unpinned Python shebang")

    if errors:
        print("Python 3.14 baseline failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("Python 3.14 baseline passed (USMSB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
