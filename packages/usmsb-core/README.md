# usmsb-core (prerelease)

Portable USMSB contracts and opt-in local collaboration mechanisms for Python
3.14. The default installation has no third-party runtime dependencies. This
engineering prerelease is built locally; it is not a claim of a PyPI release or
production certification.

## Build and install

Run from the repository root in a Python 3.14 virtual environment (on Windows,
replace `python` with `.venv/Scripts/python.exe`):

```sh
python -E -B -m pip install 'setuptools>=77' build wheel
python -E -B scripts/build_core_distribution.py
python -E -B -m pip install --no-deps dist/core/usmsb_core-0.9.0a1-py3-none-any.whl
```

`--out-dir PATH` overrides the default `dist/core/` destination. All export, build,
and egg-info files are generated in a temporary directory and cleaned up when
the build ends. Only the resulting sdist and wheel are copied to the destination.
The wheel is built from the sdist, which also contains the generated source,
manifest, and license and can be built independently of the repository.

This directory contains packaging metadata, not a second source tree. The build
uses `scripts/export_autonomy.py` to copy the canonical audited subset from
`src/usmsb_sdk`, with the exporter's LF normalization and generated namespace
shims. Build this distribution through the script from a Git checkout; running
`pip install packages/usmsb-core` directly does not generate its source.

## Import

The root `usmsb_core` and `usmsb_core.core` packages are namespace shims. Import
the contracts and elements from their explicit modules:

```python
import usmsb_core.autonomy as autonomy
from usmsb_core.core.elements import Goal

goal = autonomy.goal_element({
    "id": "research-1", "title": "Review a public dataset",
    "description": "Check the published observations", "owner_id": "researcher-1",
    "status": "active",
})
assert isinstance(goal, Goal)
assert autonomy.remote_status({"state": "accepted", "run_ref": "local:1"})["state"] == "accepted"
```

The optional existing experience adapter needs `pydantic>=2,<3`. To use it,
install the wheel with its extra (allowing pip to resolve Pydantic):

```sh
python -E -B -m pip install './dist/core/usmsb_core-0.9.0a1-py3-none-any.whl[learning]'
```

Then import `usmsb_core.autonomy.learning`. Core imports never import that
adapter. The distribution has no LLM provider, wallet, web server, model calls,
external service requirement, or background scheduler. Host authentication,
execution, and evidence verification remain the host's responsibility.

`usmsb-core` can coexist with the full `usmsb-sdk`: it owns only the
`usmsb_core` namespace. Existing SDK consumers can keep using `usmsb_sdk`;
its public exports resolve lazily to their original classes and functions.

## License and provenance

The wheel includes the MIT license in both `usmsb_core/LICENSE` and distribution
license metadata. `usmsb_core/MANIFEST.json` records the source commit, the
exported sources' dirty status, canonical source paths, per-file SHA256 hashes
(including generated shims and the license), and an aggregate content digest.
Hashes describe the exported bytes after LF normalization. A dirty build is
explicitly marked `base_commit_with_worktree_changes`; it must not be presented
as the exact contents of that commit. These records support inspection and
comparison, not publisher authentication or a cryptographic signature.

The license and manifest are accessible without SDK dependencies:

```python
from importlib.resources import files
import json

package = files("usmsb_core")
manifest = json.loads(package.joinpath("MANIFEST.json").read_text(encoding="utf-8"))
print(manifest["revision"], manifest["revision_kind"])
print(package.joinpath("LICENSE").read_text(encoding="utf-8"))
```
