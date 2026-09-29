"""Explicit collaboration policies, not a global identity or value authority."""

import re
from dataclasses import asdict, dataclass
from urllib.parse import quote

from .contracts import _check, _text


@dataclass(frozen=True)
class CollaborationProfile:
    id: str
    version: int = 1
    review_mode: str = "independent"
    media_types: tuple[str, ...] = ("*",)
    max_criteria: int = 16
    max_steps: int = 32
    legacy: bool = False

    def __post_init__(self):
        _check(_text(self.id, 180) == self.id, "Profile id must be canonical")
        _check(type(self.version) is int and self.version >= 1, "Invalid profile version")
        _check(
            isinstance(self.review_mode, str)
            and self.review_mode in {"independent", "peer", "self"},
            "Invalid review mode",
        )
        _check(type(self.legacy) is bool, "Invalid compatibility mode")
        _check(
            isinstance(self.media_types, tuple) and 1 <= len(self.media_types) <= 32,
            "Profile media types must be a bounded immutable tuple",
        )
        for media in self.media_types:
            _check(media == "*" or valid_media_type(media), "Invalid media type")
        for limit in (self.max_criteria, self.max_steps):
            _check(type(limit) is int and 1 <= limit <= 1024, "Invalid profile limit")

    def record(self):
        return {**asdict(self), "media_types": list(self.media_types)}

    def accepts(self, media_type):
        return valid_media_type(media_type) and (
            "*" in self.media_types or media_type in self.media_types
        )


def valid_media_type(value):
    return (
        isinstance(value, str)
        and len(value) <= 180
        and bool(re.fullmatch(r"[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*", value))
    )


WISHBUD_V1 = CollaborationProfile(
    "wishbud:collaboration", media_types=("application/json", "text/markdown"), legacy=True
)
OPEN_COLLABORATION_V1 = CollaborationProfile("usmsb:open-collaboration")
PEER_COLLABORATION_V1 = CollaborationProfile("usmsb:peer-collaboration", review_mode="peer")


def checked_profile(profile=None):
    value = WISHBUD_V1 if profile is None else profile
    _check(isinstance(value, CollaborationProfile), "Install a profile in trusted host code")
    return value


def world_reference_for_profile(node, ledger, kind, record_id, profile):
    profile = checked_profile(profile)
    if profile.legacy:
        _check(
            isinstance(node, str) and re.fullmatch(r"wishbud:ed25519:[A-Za-z0-9_-]{43}", node),
            "Invalid node identity",
        )
        _check(
            isinstance(ledger, str) and re.fullmatch(r"storage_[a-f0-9]{20}", ledger),
            "Invalid ledger identity",
        )
        for value in (kind, record_id):
            _check(
                isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,120}", value),
                "Invalid record reference",
            )
        return f"{node}/{ledger}/{kind}/{record_id}"
    parts = [_text(value, 300) for value in (node, ledger, kind, record_id)]
    return "usmsb-ref:" + "/".join(quote(value, safe="") for value in parts)


def entity_reference(authority, namespace, kind, record_id, *, version=None):
    """An attributed locator. Never fetch it or treat it as an access grant."""
    result = {
        "schema": "usmsb.entity-reference.v1",
        "authority": _text(authority, 300),
        "namespace": _text(namespace, 180),
        "kind": _text(kind, 120),
        "id": _text(record_id, 180),
    }
    if version is not None:
        result["version"] = _text(version, 180)
    return result


def artifact_reference(
    artifact_id, media_type, sha256, uri, size_bytes, *, profile=OPEN_COLLABORATION_V1
):
    """Validate a descriptor, not the bytes, content truth, or safety of its URI."""
    profile = checked_profile(profile)
    _check(profile.accepts(media_type), "Unsupported media type for this profile")
    _check(isinstance(sha256, str) and re.fullmatch(r"[a-f0-9]{64}", sha256), "Invalid SHA256")
    _check(type(size_bytes) is int and 0 <= size_bytes <= 2**53 - 1, "Invalid artifact size")
    location = _text(uri, 2000)
    _check(
        bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]+", location)), "Expected an opaque URI"
    )
    return {
        "schema": "usmsb.artifact-reference.v1",
        "id": _text(artifact_id, 180),
        "media_type": media_type,
        "sha256": sha256,
        "uri": location,
        "size_bytes": size_bytes,
    }
