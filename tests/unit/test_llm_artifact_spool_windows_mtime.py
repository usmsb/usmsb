from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from usmsb_sdk import llm_artifacts
from usmsb_sdk.llm_artifacts import LLMArtifactSpool


def test_refresh_mtime_requests_nofollow(monkeypatch, tmp_path):
    target = tmp_path / "artifact.json"
    target.write_text("{}", encoding="utf-8")
    observed = {}

    def capture(path, times, *, follow_symlinks):
        observed.update(
            path=path,
            times=times,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(llm_artifacts.os, "utime", capture)
    llm_artifacts._refresh_mtime_nofollow(target)

    assert observed == {
        "path": target,
        "times": None,
        "follow_symlinks": False,
    }


def test_refresh_mtime_uses_windows_handle_when_nofollow_is_unsupported(
    monkeypatch,
    tmp_path,
):
    target = tmp_path / "artifact.json"
    target.write_text("{}", encoding="utf-8")
    observed = []

    def unsupported(*_args, **_kwargs):
        raise NotImplementedError

    os_proxy = SimpleNamespace(name="nt", utime=unsupported)
    monkeypatch.setattr(llm_artifacts, "os", os_proxy)
    monkeypatch.setattr(
        llm_artifacts,
        "_refresh_mtime_windows_nofollow",
        observed.append,
    )

    llm_artifacts._refresh_mtime_nofollow(target)

    assert observed == [target]


@pytest.mark.skipif(os.name != "nt", reason="requires the Windows file API")
def test_deduplicated_artifact_refreshes_mtime_on_windows(tmp_path):
    spool = LLMArtifactSpool(root=tmp_path / "spool")
    try:
        first = spool.enqueue_redacted({"kind": "deduplicated"})
        assert spool.flush(timeout=5)
        path = spool._path_for_digest(first.sha256)
        before = path.stat().st_mtime_ns
        os.utime(path, ns=(before - 2_000_000_000, before - 2_000_000_000))

        second = spool.enqueue_redacted({"kind": "deduplicated"})
        assert second.sha256 == first.sha256
        assert spool.flush(timeout=5)
        assert path.stat().st_mtime_ns > before - 2_000_000_000
    finally:
        assert spool.close(timeout=5)
