"""GPCK/1 checkpoints: safetensors plus a JSON manifest. Pickle is never used, on save or load.

Providers are untrusted, so loading validates everything before any tensor reaches a model.
Signature, fencing and lineage are checked by the caller, because they need outside context.
Requires torch and safetensors.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Mapping

import torch
from safetensors import SafetensorError, safe_open
from safetensors.torch import save_file

from .canonical import document_hash

FORMAT = "GPCK/1"
TRAINABLE_FILE = "trainable.safetensors"
OPTIMIZER_FILE = "optimizer.safetensors"
MANIFEST_FILE = "manifest.json"
OPTIMIZER_FIELDS = ("exp_avg", "exp_avg_sq", "step")
DEFAULT_MAX_FILE_BYTES = 512 * 1024 * 1024


class CheckpointError(ValueError):
    """The checkpoint must be refused. `code` matches the quality report's reason codes."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_durable(tensors: dict[str, torch.Tensor], path: Path) -> None:
    save_file(tensors, str(path))
    # Windows refuses to fsync a file opened only for reading.
    with open(path, "r+b") as handle:
        os.fsync(handle.fileno())


def optimizer_state_to_tensors(optimizer: torch.optim.Optimizer, names: Mapping[int, str]) -> dict[str, torch.Tensor]:
    """Adam state keyed by parameter name, because indexes aren't stable across environments."""
    states = {id(param): state for param, state in optimizer.state.items()}
    missing = sorted(name for param_id, name in names.items() if not isinstance(states.get(param_id), dict) or not all(field in states[param_id] for field in OPTIMIZER_FIELDS))
    if missing:
        raise CheckpointError("BAD_CHECKPOINT", f"no optimizer state or incomplete Adam state for {len(missing)} trainable parameters, such as {missing[0]}")
    tensors: dict[str, torch.Tensor] = {}
    for param, state in optimizer.state.items():
        if id(param) not in names:
            raise CheckpointError("BAD_CHECKPOINT", "optimizer state contains an unknown parameter")
        name = names[id(param)]
        tensors[f"{name}.exp_avg"] = state["exp_avg"].detach().cpu().clone()
        tensors[f"{name}.exp_avg_sq"] = state["exp_avg_sq"].detach().cpu().clone()
        tensors[f"{name}.step"] = torch.as_tensor(state["step"]).detach().cpu().clone().reshape(1)
    return tensors


def write_checkpoint(directory: Path, trainable: dict[str, torch.Tensor], optimizer_tensors: dict[str, torch.Tensor], manifest: dict) -> dict:
    """Writes tensors, then the manifest last. Returns the completed, unsigned manifest.

    A crash before the manifest exists leaves nothing that can be committed.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    trainable_path = directory / TRAINABLE_FILE
    optimizer_path = directory / OPTIMIZER_FILE
    _write_durable(trainable, trainable_path)
    _write_durable(optimizer_tensors, optimizer_path)

    completed = dict(manifest)
    completed["format"] = FORMAT
    completed["files"] = {
        TRAINABLE_FILE: {"sha256": sha256_file(trainable_path), "bytes": trainable_path.stat().st_size},
        OPTIMIZER_FILE: {"sha256": sha256_file(optimizer_path), "bytes": optimizer_path.stat().st_size},
    }
    temp = directory / (MANIFEST_FILE + ".tmp")
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(completed, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, directory / MANIFEST_FILE)
    return completed


def read_manifest(directory: Path) -> dict:
    path = Path(directory) / MANIFEST_FILE
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        raise CheckpointError("MALFORMED_CHECKPOINT", f"unreadable manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
        raise CheckpointError("MALFORMED_CHECKPOINT", "not a GPCK/1 manifest")
    return manifest


def manifest_hash(manifest: dict) -> str:
    return document_hash(manifest)


def _check_file(directory: Path, name: str, manifest: dict, max_bytes: int) -> Path:
    path = directory / name
    entry = manifest.get("files", {}).get(name)
    if not isinstance(entry, dict):
        raise CheckpointError("MALFORMED_CHECKPOINT", f"{name} missing from manifest")
    if not path.is_file():
        raise CheckpointError("MALFORMED_CHECKPOINT", f"{name} missing from checkpoint")
    size = path.stat().st_size
    if size > max_bytes:
        raise CheckpointError("MALFORMED_CHECKPOINT", f"{name} is {size} bytes, over the {max_bytes} limit")
    if size != entry.get("bytes"):
        raise CheckpointError("HASH_MISMATCH", f"{name} size differs from manifest")
    if sha256_file(path) != entry.get("sha256"):
        raise CheckpointError("HASH_MISMATCH", f"{name} hash differs from manifest")
    return path


def _expected_dtype(name: str, dtype: torch.dtype) -> torch.dtype:
    # Adam's step counter is a scalar in torch's default dtype, whatever dtype the weights use.
    return torch.float32 if name.endswith(".step") else dtype


def _load_validated(path: Path, expected: Mapping[str, tuple[int, ...]], dtype: torch.dtype) -> dict[str, torch.Tensor]:
    """Parses as safetensors only, so a renamed pickle is just a parse error and nothing executes."""
    tensors: dict[str, torch.Tensor] = {}
    try:
        with safe_open(str(path), framework="pt", device="cpu") as handle:
            found = set(handle.keys())
            if found != set(expected):
                missing, extra = sorted(set(expected) - found), sorted(found - set(expected))
                raise CheckpointError("MALFORMED_CHECKPOINT", f"{path.name}: tensor names differ, missing {missing[:3]}, unexpected {extra[:3]}")
            for name in sorted(found):
                tensor = handle.get_tensor(name)
                if tuple(tensor.shape) != tuple(expected[name]):
                    raise CheckpointError("MALFORMED_CHECKPOINT", f"{name}: shape {tuple(tensor.shape)}, expected {tuple(expected[name])}")
                wanted = _expected_dtype(name, dtype)
                if tensor.dtype != wanted:
                    raise CheckpointError("MALFORMED_CHECKPOINT", f"{name}: dtype {tensor.dtype}, expected {wanted}")
                if not torch.isfinite(tensor).all():
                    raise CheckpointError("NAN_OR_INF", f"{name} contains NaN or Inf")
                tensors[name] = tensor
    except (SafetensorError, OSError, ValueError, RuntimeError) as exc:
        if isinstance(exc, CheckpointError):
            raise
        raise CheckpointError("MALFORMED_CHECKPOINT", f"{path.name} is not valid safetensors: {exc}") from exc
    return tensors


def expected_optimizer_shapes(param_shapes: Mapping[str, tuple[int, ...]]) -> dict[str, tuple[int, ...]]:
    shapes: dict[str, tuple[int, ...]] = {}
    for name, shape in param_shapes.items():
        shapes[f"{name}.exp_avg"] = tuple(shape)
        shapes[f"{name}.exp_avg_sq"] = tuple(shape)
        shapes[f"{name}.step"] = (1,)
    return shapes


def load_checkpoint(
    directory: Path,
    param_shapes: Mapping[str, tuple[int, ...]],
    *,
    dtype: torch.dtype = torch.float32,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    expected_immutable_hash: str | None = None,
) -> tuple[dict, dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    """Validate a checkpoint and return (manifest, trainable, optimizer tensors), all on CPU."""
    directory = Path(directory)
    manifest = read_manifest(directory)
    if expected_immutable_hash is not None and manifest.get("immutable_hash") != expected_immutable_hash:
        raise CheckpointError("INVALID_LINEAGE", "checkpoint belongs to a different job spec")
    trainable_path = _check_file(directory, TRAINABLE_FILE, manifest, max_file_bytes)
    optimizer_path = _check_file(directory, OPTIMIZER_FILE, manifest, max_file_bytes)
    trainable = _load_validated(trainable_path, param_shapes, dtype)
    optimizer_tensors = _load_validated(optimizer_path, expected_optimizer_shapes(param_shapes), dtype)
    return manifest, trainable, optimizer_tensors


def restore_optimizer_state(optimizer: torch.optim.Optimizer, named_params: Mapping[str, torch.nn.Parameter], tensors: Mapping[str, torch.Tensor]) -> None:
    """Puts validated Adam state back, moving each tensor to its parameter's device."""
    for name, param in named_params.items():
        optimizer.state[param] = {
            "step": tensors[f"{name}.step"].reshape(()).clone().to(param.device),
            "exp_avg": tensors[f"{name}.exp_avg"].clone().to(param.device),
            "exp_avg_sq": tensors[f"{name}.exp_avg_sq"].clone().to(param.device),
        }
