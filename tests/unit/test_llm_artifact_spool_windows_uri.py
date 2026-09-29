"""Native file URI round trips and adversarial reads on Windows and POSIX."""

from __future__ import annotations

import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from usmsb_sdk.llm_artifacts import LLMArtifactSpool, LLMArtifactSpoolError


@pytest.fixture
def artifact(tmp_path):
    spool = LLMArtifactSpool(tmp_path / "spool")
    payload = {"content": "URI security regression"}
    reference = spool.enqueue_redacted(payload)
    try:
        assert spool.flush(timeout=5)
        assert reference.uri is not None
        yield spool, reference, payload
    finally:
        assert spool.close(timeout=5)


@pytest.mark.parametrize(
    "root_name",
    [
        "ordinary",
        "with spaces",
        "unicode-\u6d4b\u8bd5-\u00e9-\U0001f512",
        "plus+sign",
        "hash#and;semicolon",
        "literal-%2F-%5C-%2e%2e-%00-%252F",
    ],
)
def test_native_uri_round_trip_after_restart(tmp_path, root_name):
    root = tmp_path / root_name
    payload = {"content": "read after restart", "unicode": "\u6d4b\u8bd5"}
    first = LLMArtifactSpool(root)
    reference = first.enqueue_redacted(payload)
    assert first.close(timeout=5)
    assert reference.uri is not None
    expected = (
        root.resolve() / "sha256" / reference.sha256[:2] / reference.sha256[2:4]
        / f"{reference.sha256}.json"
    )
    assert reference.uri == expected.as_uri()
    assert Path.from_uri(reference.uri) == expected

    restarted = LLMArtifactSpool(root)
    try:
        assert restarted.read(uri=reference.uri, expected_sha256=reference.sha256) == payload
        assert restarted.read_by_hash(reference.sha256) == payload
        local_uri = "file://localhost" + urlsplit(reference.uri).path
        assert restarted.read(uri=local_uri, expected_sha256=reference.sha256) == payload
    finally:
        assert restarted.close(timeout=5)


@pytest.mark.parametrize("variant", ["single-slash", "escaped-unreserved", "lowercase-escape"])
def test_valid_local_uri_spellings(artifact, variant):
    spool, reference, payload = artifact
    path = urlsplit(reference.uri).path
    if variant == "single-slash":
        uri = "file:" + path
    elif variant == "escaped-unreserved":
        uri = "file://" + path.replace("/sha256/", "/%73ha256/")
    else:
        uri = reference.uri.replace(".json", "%2ejson")
    assert spool.read(uri=uri, expected_sha256=reference.sha256) == payload


@pytest.mark.parametrize(
    "authority",
    [
        "remote.example", "127.0.0.1", "[::1]", "localhost.", "LOCALHOST",
        "localhost:80", "user@localhost", "user:secret@localhost", "@localhost",
        "localhost@remote.example", "%6cocalhost", "localhost%00", "C:",
        "[invalid", "[::1]suffix",
    ],
)
def test_rejects_unapproved_authorities_before_filesystem_access(artifact, monkeypatch, authority):
    spool, reference, _ = artifact
    monkeypatch.setattr(
        spool, "_reject_symlink_components",
        lambda _path: pytest.fail("untrusted authority reached filesystem validation"),
    )
    uri = "file://" + authority + urlsplit(reference.uri).path
    with pytest.raises(LLMArtifactSpoolError):
        spool.read(uri=uri, expected_sha256=reference.sha256)


def test_local_hostname_does_not_expand_authority_allowlist(artifact, monkeypatch):
    spool, reference, _ = artifact
    # The stdlib converter also accepts the local hostname. The spool's
    # intentionally narrower authority contract must be checked first.
    hostname = socket.gethostname()
    if hostname == "localhost":
        hostname = "local-machine.example"
    monkeypatch.setattr(
        spool, "_reject_symlink_components",
        lambda _path: pytest.fail("hostname authority reached filesystem validation"),
    )
    with pytest.raises(LLMArtifactSpoolError, match="local file"):
        spool.read(uri="file://" + hostname + urlsplit(reference.uri).path)


@pytest.mark.parametrize(
    "template",
    [
        "https://localhost{path}", "ftp://localhost{path}", "{path}",
        "file:sha256/{digest}.json", "file:///{digest}.json",
        "file://{path}?token=x", "file://{path}#fragment", "file://{path}?", "file://{path}#",
        " file://{path}", "\x00file://{path}", "\nfile://{path}",
        "file://{path}\r", "file://{path}\t", "file://{path}\x7f",
        "file://{parent}/./{digest}.json", "file://{parent}/%2e/{digest}.json",
        "file://{parent}/../{shard}/{digest}.json",
        "file://{parent}/%2E%2e/{shard}/{digest}.json",
        "file://{parent}/%252e%252e/{shard}/{digest}.json",
        "file://{parent}//{digest}.json", "file://{path}/",
        "file://{parent}%2f{digest}.json", "file://{parent}%2F{digest}.json",
        "file://{parent}%5c{digest}.json", "file://{parent}%5C{digest}.json",
        "file://{parent}\\{digest}.json", "file://{parent}/%00{digest}.json",
        "file://{parent}/%{digest}.json", "file://{parent}/%GG{digest}.json",
        "file://{parent}/%FF{digest}.json", "file://{parent}/%C0%AF{digest}.json",
        "file://{parent}/%2{digest}.json",
        "file://{path}:stream", "file://{path}:stream.json", "file://{path}::$DATA",
        "file://{path}%3Astream.json", "file://{path}.", "file://{path}%20",
        "file:////server/share/{digest}.json", "file://///server/share/{digest}.json",
        "file://localhost//server/share/{digest}.json",
        "file:///%2Fserver/share/{digest}.json",
        "file:///%5C%5Cserver/share/{digest}.json",
        "file:////?/C:/{digest}.json", "file:////%3F/C:/{digest}.json",
        "file:////./C:/{digest}.json", "file:///%5C%5C%3F%5CC:%5C{digest}.json",
        "file:///C|/{digest}.json", "file:///C%3A/{digest}.json",
        "file:///C:relative/{digest}.json", "file:C:relative/{digest}.json",
    ],
)
def test_rejects_ambiguous_or_escaping_uris_before_filesystem_access(
    artifact, monkeypatch, template,
):
    spool, reference, _ = artifact
    path = urlsplit(reference.uri).path
    uri = template.format(
        path=path, parent=path.rsplit("/", 1)[0], digest=reference.sha256,
        shard=reference.sha256[2:4],
    )
    monkeypatch.setattr(
        spool, "_reject_symlink_components",
        lambda _path: pytest.fail("invalid URI reached filesystem validation"),
    )
    with pytest.raises(LLMArtifactSpoolError):
        spool.read(uri=uri, expected_sha256=reference.sha256)


def test_rejects_outside_root_with_identical_content_and_layout(artifact):
    spool, reference, _ = artifact
    target = Path.from_uri(reference.uri)
    # The sibling shares the root's string prefix, but is not contained in it.
    outside = spool.root.with_name(spool.root.name + "-outside") / target.relative_to(spool.root)
    outside.parent.mkdir(parents=True)
    outside.write_bytes(target.read_bytes())
    with pytest.raises(LLMArtifactSpoolError, match="canonical|escapes"):
        spool.read(uri=outside.as_uri(), expected_sha256=reference.sha256)


@pytest.mark.parametrize("kind", ["missing", "directory", "tampered", "wrong-shard"])
def test_native_uri_still_validates_file_and_content(artifact, kind):
    spool, reference, _ = artifact
    path = Path.from_uri(reference.uri)
    uri = reference.uri
    if kind == "missing":
        path.unlink()
    elif kind == "directory":
        path.unlink()
        path.mkdir()
    elif kind == "tampered":
        path.write_text('{"content":"tampered"}', encoding="utf-8")
    else:
        uri = (spool.root / "sha256" / "wrong" / path.name).as_uri()
    with pytest.raises(LLMArtifactSpoolError):
        spool.read(uri=uri, expected_sha256=reference.sha256)


@pytest.mark.parametrize("component", ["file", "shard", "content-root", "spool-root"])
@pytest.mark.parametrize("outside", [False, True])
def test_rejects_symlink_components_even_with_matching_bytes(artifact, component, outside):
    spool, reference, _ = artifact
    path = Path.from_uri(reference.uri)
    target = {
        "file": path, "shard": path.parent,
        "content-root": spool.root / "sha256", "spool-root": spool.root,
    }[component]
    destination_parent = spool.root.parent if outside else target.parent
    moved = destination_parent / ("moved-" + target.name)
    is_directory = target.is_dir()
    target.rename(moved)
    try:
        target.symlink_to(moved, target_is_directory=is_directory)
        with pytest.raises(LLMArtifactSpoolError, match="symbolic links"):
            spool.read(uri=reference.uri, expected_sha256=reference.sha256)
    finally:
        if target.is_symlink():
            target.unlink()
        moved.rename(target)


@pytest.mark.skipif(os.name != "nt", reason="requires Windows directory junctions")
@pytest.mark.parametrize("component", ["shard", "spool-root"])
@pytest.mark.parametrize("outside", [False, True])
def test_rejects_windows_junctions(artifact, component, outside):
    import _winapi

    spool, reference, _ = artifact
    target = Path.from_uri(reference.uri).parent if component == "shard" else spool.root
    destination_parent = spool.root.parent if outside else target.parent
    moved = destination_parent / ("moved-" + target.name)
    target.rename(moved)
    try:
        _winapi.CreateJunction(str(moved), str(target))
        assert target.is_junction()
        with pytest.raises(LLMArtifactSpoolError, match="junctions"):
            spool.read(uri=reference.uri, expected_sha256=reference.sha256)
    finally:
        if target.is_junction():
            target.rmdir()
        moved.rename(target)


@pytest.mark.skipif(os.name != "nt", reason="requires native Windows drive paths")
def test_windows_drive_letter_case_round_trip(artifact):
    spool, reference, payload = artifact
    path = urlsplit(reference.uri).path
    assert path[0] == "/" and path[2:4] == ":/"
    for drive_letter in (path[1].lower(), path[1].upper()):
        uri = "file:///" + drive_letter + path[2:]
        assert spool.read(uri=uri, expected_sha256=reference.sha256) == payload


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX filename semantics")
@pytest.mark.parametrize(
    "root_name", ["literal\\backslash", "literal:colon?question", "byte-\udcff"],
)
def test_posix_filename_uri_round_trip(tmp_path, root_name):
    spool = LLMArtifactSpool(tmp_path / root_name)
    payload = {"content": "POSIX filenames"}
    try:
        reference = spool.enqueue_redacted(payload)
        assert spool.flush(timeout=5)
        assert spool.read(uri=reference.uri, expected_sha256=reference.sha256) == payload
    finally:
        assert spool.close(timeout=5)
