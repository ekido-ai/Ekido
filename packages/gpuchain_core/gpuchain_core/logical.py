"""The logical-step invariant: a logical step means the same thing on every GPU.

Everything here is a pure function of the job spec and the step number, so resuming on different
hardware needs no sampler, scheduler or RNG state from the previous machine. Standard library only.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


class InvalidExecConfig(ValueError):
    pass


def check_exec_config(exec_config: dict, logical_batch_size: int) -> None:
    """Rules JSON Schema can't express. Raises InvalidExecConfig."""
    micro = exec_config["micro_batch"]
    accumulation = exec_config["accumulation"]
    if micro * accumulation != logical_batch_size:
        raise InvalidExecConfig(
            f"micro_batch {micro} x accumulation {accumulation} must equal logical batch {logical_batch_size}"
        )


def feasible_micro_batches(logical_batch_size: int) -> list[int]:
    """Micro-batches that divide the logical batch exactly, largest first."""
    return [m for m in range(logical_batch_size, 0, -1) if logical_batch_size % m == 0]


def derive_seed(*parts: int | str) -> int:
    """Stable across machines and Python versions, unlike hash()."""
    text = "\x1f".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "big")


def micro_batch_seed(job_seed: int, logical_step: int, micro_index: int) -> int:
    """Seed for dropout in one micro-batch.

    Masks still differ when the micro-batch size changes, because each micro-batch draws its own.
    That is a known, reported difference, not an equivalence claim.
    """
    return derive_seed("micro", job_seed, logical_step, micro_index)


@dataclass(frozen=True)
class StepPosition:
    epoch: int
    start: int  # Offset into this epoch's permutation.


def step_position(logical_step: int, logical_batch_size: int, dataset_size: int) -> StepPosition:
    """Which epoch and offset a step uses. An incomplete batch at an epoch's end is dropped."""
    if logical_batch_size > dataset_size:
        raise ValueError("logical batch is larger than the dataset")
    steps_per_epoch = dataset_size // logical_batch_size
    epoch, index = divmod(logical_step, steps_per_epoch)
    return StepPosition(epoch=epoch, start=index * logical_batch_size)


def epoch_permutation(job_seed: int, epoch: int, dataset_size: int) -> list[int]:
    # random.Random's shuffle is deterministic for a given seed and documented as stable for seeding
    # with an int, so this does not depend on numpy or torch versions.
    order = list(range(dataset_size))
    random.Random(derive_seed("epoch", job_seed, epoch)).shuffle(order)
    return order


def logical_batch_indices(job_seed: int, logical_step: int, logical_batch_size: int, dataset_size: int) -> list[int]:
    """Example indices for a logical step. Independent of micro-batch size and hardware."""
    position = step_position(logical_step, logical_batch_size, dataset_size)
    order = epoch_permutation(job_seed, position.epoch, dataset_size)
    return order[position.start : position.start + logical_batch_size]


def split_micro_batches(indices: list[int], micro_batch: int) -> list[list[int]]:
    return [indices[i : i + micro_batch] for i in range(0, len(indices), micro_batch)]


def micro_loss_weight(micro_size: int, logical_batch_size: int) -> float:
    """Multiply a micro-batch's mean loss by this, so accumulated gradients equal the full batch's mean."""
    return micro_size / logical_batch_size


def learning_rate(schedule: dict, base_lr: float, logical_step: int, total_steps: int) -> float:
    """A pure function of the step, so there is no scheduler state to corrupt or migrate."""
    name = schedule["name"]
    if name == "constant":
        return base_lr
    if name == "linear_warmup_linear_decay":
        warmup = schedule["warmup_steps"]
        if logical_step < warmup:
            return base_lr * (logical_step + 1) / warmup
        remaining = max(0, total_steps - logical_step)
        return base_lr * remaining / max(1, total_steps - warmup)
    raise ValueError(f"unknown schedule: {name}")
