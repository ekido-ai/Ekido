"""Stable identity for the text and labels in an ordered AG News split."""
from __future__ import annotations

import hashlib
import re

_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def require_commit(value: str, name: str) -> str:
    if not isinstance(value, str) or not _COMMIT.fullmatch(value) or value == "0" * 40:
        raise ValueError(f"{name} must be a lowercase 40-character immutable commit")
    return value


def require_digest(value: str, name: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value) or value == "0" * 64:
        raise ValueError(f"{name} must be a nonzero lowercase SHA-256 digest")
    return value


def hash_text_labels(rows) -> str:
    """Hash ordered UTF-8 text and integer labels, with lengths to prevent ambiguity."""
    digest = hashlib.sha256(b"GPUChain/AGNews/text-labels/v1\0")
    count = 0
    for row in rows:
        text, label = row["text"], row["label"]
        if not isinstance(text, str) or isinstance(label, bool) or not isinstance(label, int):
            raise ValueError("dataset rows must contain text and an integer label")
        encoded = text.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(label.to_bytes(8, "big", signed=True))
        count += 1
    digest.update(count.to_bytes(8, "big"))
    return digest.hexdigest()


def check_split(rows, expected: str, name: str) -> None:
    require_digest(expected, name)
    if hash_text_labels(rows) != expected:
        raise ValueError(f"{name} mismatch: refusing to use different data")


def validate_spec_identity(spec: dict) -> bool:
    """Validate all identity fields together; historical unpinned specs remain usable."""
    dataset = spec.get("dataset", {})
    fields = {"revision", "content_sha256", "test_content_sha256"}
    if not fields.intersection(dataset):
        return False
    if not fields.issubset(dataset):
        raise ValueError("dataset identity must include revision and both split hashes")
    require_commit(spec["model"]["revision"], "model.revision")
    require_commit(dataset["revision"], "dataset.revision")
    train_hash = require_digest(dataset["content_sha256"], "dataset.content_sha256")
    require_digest(dataset["test_content_sha256"], "dataset.test_content_sha256")
    if dataset.get("fingerprint") != train_hash:
        raise ValueError("dataset fingerprint must match training content hash")
    return True


def apply_identity(spec: dict, identity: dict) -> dict:
    """Make a new immutable spec; never alter a historical checkpoint's spec."""
    from copy import deepcopy

    if spec.get("template") != "distilbert-lora-agnews/v1":
        raise ValueError("identity applies only to the AG News workload")
    if "provider_terms" in spec:
        raise ValueError("pin identity before collecting provider quotes")
    if identity.get("model_id") != spec["model"]["id"] or identity.get("dataset_id") != spec["dataset"]["id"]:
        raise ValueError("identity model or dataset does not match the job")
    model_revision = require_commit(identity.get("model_revision"), "model_revision")
    data_revision = require_commit(identity.get("dataset_revision"), "dataset_revision")
    train_hash = require_digest(identity.get("train_sha256"), "train_sha256")
    test_hash = require_digest(identity.get("test_sha256"), "test_sha256")
    pinned = deepcopy(spec)
    pinned["model"]["revision"] = model_revision
    pinned["dataset"].update(revision=data_revision, fingerprint=train_hash,
                             content_sha256=train_hash, test_content_sha256=test_hash)
    return pinned
