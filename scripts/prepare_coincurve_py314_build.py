#!/usr/bin/env python3.14
"""Prepare cffi metadata for building coincurve 21 on CPython 3.14.

coincurve 21.0.0 expects cffi's LICENSE file directly inside the
``*.dist-info`` directory.  cffi 2.0.0, the first release shipping CPython
3.14 wheels, follows PEP 639 and stores it under ``dist-info/licenses``.
This copies the already-installed license to the legacy location used by the
coincurve build hook.  It does not patch either package's runtime code.
"""

from __future__ import annotations

import csv
import shutil
from importlib.metadata import distribution
from pathlib import Path


def _dist_info_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if parent.name.endswith(".dist-info"):
            return parent
    return None


def main() -> None:
    cffi = distribution("cffi")
    license_files = [
        Path(item.locate()).resolve()
        for item in cffi.files or ()
        if item.name == "LICENSE"
    ]

    legacy_files = [
        path
        for path in license_files
        if path.parent.name.endswith(".dist-info")
    ]
    if len(legacy_files) == 1:
        return
    if legacy_files:
        raise RuntimeError(
            f"Expected at most one legacy cffi LICENSE, got {legacy_files!r}"
        )

    nested_files = [
        (path, _dist_info_parent(path))
        for path in license_files
        if _dist_info_parent(path) is not None
    ]
    if len(nested_files) != 1:
        raise RuntimeError(
            f"Expected exactly one cffi LICENSE in package metadata, got {license_files!r}"
        )

    source, dist_info = nested_files[0]
    assert dist_info is not None
    target = dist_info / "LICENSE"
    shutil.copyfile(source, target)

    # importlib.metadata enumerates files from RECORD, so the compatibility
    # copy must be registered as package metadata for coincurve's build hook.
    record = dist_info / "RECORD"
    relative_target = target.relative_to(dist_info.parent).as_posix()
    with record.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not any(row and row[0] == relative_target for row in rows):
        with record.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow((relative_target, "", ""))


if __name__ == "__main__":
    main()
