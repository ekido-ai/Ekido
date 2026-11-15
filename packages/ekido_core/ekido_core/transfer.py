"""Moving checkpoint blobs between a worker and the coordinator's store.

When the coordinator offers a short-lived object-storage link, the bytes go straight to or from storage and skip the
coordinator. Otherwise they go through the coordinator, as before. The link carries its own authorization, so the
coordinator's token is never sent to storage. Either way the content is checked against its SHA-256: storage refuses
an upload whose hash doesn't match, and every download is verified by `save_checkpoint_blob`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from .download import save_checkpoint_blob


def _offer(request: urllib.request.Request, timeout: float) -> dict | None:
    """The coordinator's answer, or None when it doesn't offer direct links (an older coordinator, or none set up)."""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def download_blob(base: str, token: str, digest: str, target: Path, expected_bytes: int, timeout: float = 300) -> None:
    auth = {"Authorization": f"Bearer {token}"}
    offer = _offer(urllib.request.Request(f"{base}/artifacts/{digest}/download-url", headers=auth), timeout=30)
    if offer and offer.get("url"):
        request = urllib.request.Request(offer["url"])
    else:
        request = urllib.request.Request(f"{base}/artifacts/{digest}", headers=auth)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        save_checkpoint_blob(response, target, digest, expected_bytes)


def upload_blob(base: str, token: str, path: Path, digest: str, timeout: float = 300) -> None:
    """Streams the file from disk, so a large checkpoint isn't held in memory."""
    size = Path(path).stat().st_size
    auth = {"Authorization": f"Bearer {token}"}
    ask = urllib.request.Request(
        f"{base}/artifacts/{digest}/upload-url", data=json.dumps({"bytes": size}).encode(), method="POST",
        headers={**auth, "Content-Type": "application/json"},
    )
    offer = _offer(ask, timeout=30)
    if offer and offer.get("exists"):
        return
    with open(path, "rb") as handle:
        if offer and offer.get("url"):
            headers = {**offer.get("headers", {}), "Content-Length": str(size)}
            request = urllib.request.Request(offer["url"], data=handle, method="PUT", headers=headers)
        else:
            headers = {**auth, "Content-Type": "application/octet-stream", "Content-Length": str(size)}
            request = urllib.request.Request(f"{base}/artifacts/{digest}", data=handle, method="PUT", headers=headers)
        with urllib.request.urlopen(request, timeout=timeout):
            pass
