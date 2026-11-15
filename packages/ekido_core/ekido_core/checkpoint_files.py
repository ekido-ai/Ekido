"""Validate untrusted checkpoint file entries before they reach a downloader or disk path."""

import re

CHECKPOINT_FILENAMES = frozenset(("trainable.safetensors", "optimizer.safetensors"))
MAX_FILE_BYTES = 512 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}")


def checkpoint_files(manifest: dict) -> dict:
    files = manifest.get("files") if isinstance(manifest, dict) else None
    # Exact basenames also exclude traversal, absolute paths, alternate streams and extra files.
    if not isinstance(files, dict) or set(files) != CHECKPOINT_FILENAMES:
        raise ValueError("GPCK/1 requires exactly trainable.safetensors and optimizer.safetensors")
    for name, entry in files.items():
        if not isinstance(entry, dict):
            raise ValueError(f"invalid file entry for {name}")
        digest, size = entry.get("sha256"), entry.get("bytes")
        if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            raise ValueError(f"invalid SHA-256 for {name}")
        if type(size) is not int or not 0 < size <= MAX_FILE_BYTES:
            raise ValueError(f"invalid file size for {name}")
    return files
