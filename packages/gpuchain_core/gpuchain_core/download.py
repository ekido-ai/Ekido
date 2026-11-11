"""Bound and authenticate a checkpoint response while copying it to disk."""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import BinaryIO

from .checkpoint_files import MAX_FILE_BYTES


def save_checkpoint_blob(response: BinaryIO, target: Path, digest: str, expected_bytes: int) -> None:
    """Reject truncated, oversized or altered responses without exposing a partial target file."""
    if type(expected_bytes) is not int or not 0 < expected_bytes <= MAX_FILE_BYTES:
        raise ValueError("invalid checkpoint file size")
    target = Path(target)
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.partial")
    hasher = hashlib.sha256()
    received = 0
    try:
        with temp.open("xb") as handle:
            while received < expected_bytes:
                chunk = response.read(min(64 * 1024, expected_bytes - received))
                if not chunk:
                    raise ValueError("checkpoint download is shorter than declared")
                received += len(chunk)
                if received > expected_bytes:
                    raise ValueError("checkpoint download is larger than declared")
                hasher.update(chunk)
                handle.write(chunk)
            if response.read(1):
                raise ValueError("checkpoint download is larger than declared")
            if hasher.hexdigest() != digest:
                raise ValueError("checkpoint download does not match its SHA-256")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
