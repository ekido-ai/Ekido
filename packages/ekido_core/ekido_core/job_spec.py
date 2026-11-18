"""What a job must say before the coordinator accepts it.

A spec's hash goes on-chain and a client pays against it, so an incomplete one must be refused at the
door instead of failing later on a provider. Full schemas: docs/schemas/job_spec.schema.json and
quality_policy.schema.json. This checks what the workers really read, and is dependency-free.
"""

from __future__ import annotations

import math

from .data_identity import require_commit, require_digest, validate_spec_identity

# A LoRA learning rate above this diverges rather than trains; refusing it up front saves a wasted run.
MAX_LR = 1e-2

TEMPLATES = ("distilbert-lora-agnews/v1", "synthetic-linear/v1", "custom-python/v1", "llm-lora/v1")
# Base models for llm-lora/v1: only ones whose licence allows commercial use, fine-tuning and derivatives (Apache-2.0).
# Qwen2.5-3B is left out on purpose: its licence is not Apache-2.0.
LLM_BASES = ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct")
MAX_PROBATION_MARGIN = 0.15  # Wider than this, a mid-training check would stop catching real damage.
POLICY_FIELDS = ("min_absolute", "non_inferiority_margin", "confidence", "bootstrap_resamples", "eval_set_hash", "eval_version_hash")


def _whole(spec: dict, name: str, minimum: int, problems: list[str]) -> None:
    value = spec.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        problems.append(f"{name} must be a whole number of at least {minimum}")


def _section(spec: dict, name: str, fields: tuple[str, ...], problems: list[str]) -> None:
    section = spec.get(name)
    if not isinstance(section, dict):
        problems.append(f"{name} is missing")
        return
    problems.extend(f"{name}.{field} is missing" for field in fields if field not in section)


def spec_problems(spec: dict) -> list[str]:
    """Everything wrong with a workload, in words a client can act on. Empty means it's acceptable."""
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]
    template = spec.get("template")
    if template not in TEMPLATES:
        return [f"template must be one of {', '.join(TEMPLATES)}"]
    problems: list[str] = []
    _whole(spec, "logical_batch_size", 1, problems)
    _whole(spec, "total_logical_steps", 1, problems)
    _whole(spec, "seed", 0, problems)
    if "checkpoint_every_steps" in spec:
        _whole(spec, "checkpoint_every_steps", 1, problems)
    if "train_examples" in spec:
        _whole(spec, "train_examples", 1, problems)
    _section(spec, "optimizer", ("name", "lr", "weight_decay", "betas", "eps", "max_grad_norm"), problems)
    _section(spec, "lr_schedule", ("name", "warmup_steps"), problems)
    if template == "distilbert-lora-agnews/v1":
        _section(spec, "model", ("id", "revision"), problems)
        _section(spec, "dataset", ("id", "split", "fingerprint"), problems)
        _section(spec, "lora", ("r", "alpha", "dropout", "target_modules"), problems)
        _whole(spec, "max_seq_length", 8, problems)
        try:
            validate_spec_identity(spec)
        except (KeyError, TypeError, ValueError) as exc:
            # Our own ValueErrors name the field and never echo input, so they're safe and useful to show.
            # Anything else (a missing key, a wrong type) reports only its kind.
            detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            problems.append(f"invalid data identity: {detail}")
    if template == "llm-lora/v1":
        _llm_problems(spec, problems)
    from .protocol_fee import fee_problems

    problems.extend(fee_problems(spec))
    if template == "custom-python/v1":
        code = spec.get("code")
        if not isinstance(code, dict) or not _is_sha256(code.get("sha256")):
            problems.append("code.sha256 must be the SHA-256 of job.py")
        files = spec.get("files", {})
        if not isinstance(files, dict) or not all(isinstance(k, str) and _safe_name(k) and _is_sha256(v) for k, v in files.items()):
            problems.append("files must map plain file names to SHA-256 hashes")
        if "user_config" in spec and not isinstance(spec["user_config"], dict):
            problems.append("user_config must be an object")
    return problems


def _llm_problems(spec: dict, problems: list[str]) -> None:
    from .recipes import RECIPES

    _section(spec, "model", ("id", "revision"), problems)
    # The rows travel as one JSONL blob in the artifact store; providers fetch it by hash and size, like checkpoints.
    _section(spec, "dataset", ("sha256", "bytes", "train_rows", "test_rows"), problems)
    _section(spec, "lora", ("r", "alpha", "dropout", "target_modules"), problems)
    model, dataset = spec.get("model"), spec.get("dataset")
    if isinstance(model, dict) and "id" in model:
        if model["id"] not in LLM_BASES:
            problems.append(f"model.id must be one of {', '.join(LLM_BASES)}")
        try:
            require_commit(model.get("revision"), "model.revision")
        except ValueError as exc:
            problems.append(str(exc))
    if isinstance(dataset, dict) and "sha256" in dataset:
        try:
            require_digest(dataset["sha256"], "dataset.sha256")
        except ValueError as exc:
            problems.append(str(exc))
        _whole(dataset, "bytes", 1, problems)
        _whole(dataset, "train_rows", 1, problems)
        _whole(dataset, "test_rows", 20, problems)
        batch, rows = spec.get("logical_batch_size"), dataset.get("train_rows")
        if type(batch) is int and type(rows) is int and batch > rows:
            problems.append("logical_batch_size cannot exceed dataset.train_rows")
    lora = spec.get("lora")
    if isinstance(lora, dict):
        if "r" in lora and (type(lora["r"]) is not int or lora["r"] < 1):
            problems.append("lora.r must be a positive integer")
        if "alpha" in lora and (not _finite_number(lora["alpha"]) or lora["alpha"] <= 0):
            problems.append("lora.alpha must be a positive finite number")
        if "dropout" in lora and (not _finite_number(lora["dropout"]) or not 0 <= lora["dropout"] < 1):
            problems.append("lora.dropout must be a finite number from 0 up to but not including 1")
        if "target_modules" in lora and (not isinstance(lora["target_modules"], list) or not lora["target_modules"]
                                         or not all(isinstance(x, str) and x.strip() for x in lora["target_modules"])):
            problems.append("lora.target_modules must be a non-empty list of names")
    optimizer = spec.get("optimizer")
    if isinstance(optimizer, dict):
        if "name" in optimizer and optimizer["name"] != "adamw":
            problems.append("optimizer.name must be adamw")
        for field in ("lr", "eps", "max_grad_norm"):
            if field in optimizer and (not _finite_number(optimizer[field]) or optimizer[field] <= 0):
                problems.append(f"optimizer.{field} must be a positive finite number")
        if "lr" in optimizer and _finite_number(optimizer["lr"]) and optimizer["lr"] > MAX_LR:
            problems.append(f"optimizer.lr must be at most {MAX_LR}")
        if "weight_decay" in optimizer and (not _finite_number(optimizer["weight_decay"]) or optimizer["weight_decay"] < 0):
            problems.append("optimizer.weight_decay must be a non-negative finite number")
        if "betas" in optimizer:
            betas = optimizer["betas"]
            if not isinstance(betas, list) or len(betas) != 2 or not all(_finite_number(v) and 0 <= v < 1 for v in betas):
                problems.append("optimizer.betas must contain two finite numbers in [0, 1)")
    schedule = spec.get("lr_schedule")
    if isinstance(schedule, dict):
        if "name" in schedule and schedule["name"] not in ("constant", "linear_warmup_linear_decay"):
            problems.append("lr_schedule.name must be constant or linear_warmup_linear_decay")
        if "warmup_steps" in schedule and (type(schedule["warmup_steps"]) is not int or schedule["warmup_steps"] < 0):
            problems.append("lr_schedule.warmup_steps must be a non-negative integer")
        elif ("warmup_steps" in schedule and type(spec.get("total_logical_steps")) is int
              and schedule["warmup_steps"] > spec["total_logical_steps"]):
            problems.append("lr_schedule.warmup_steps cannot exceed total_logical_steps")
    recipe_id = spec.get("recipe_id")
    if not isinstance(recipe_id, str) or recipe_id not in RECIPES:
        problems.append(f"recipe_id must be one of {', '.join(sorted(RECIPES))}")
    length = spec.get("max_seq_length")
    if isinstance(length, bool) or not isinstance(length, int) or not 32 <= length <= 2048:
        problems.append("max_seq_length must be a whole number from 32 to 2048")


def _finite_number(value) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _is_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _safe_name(name: str) -> bool:
    """No folders, no hidden files and no tricks: the name is used as a path inside the sandbox."""
    return 0 < len(name) <= 120 and "/" not in name and "\\" not in name and not name.startswith(".") and name not in ("..", ".")


def policy_problems(policy: dict) -> list[str]:
    """Verifiers can't judge a job without these. Only enforced when a quality gate is running."""
    problems = [f"policy.{field} is missing" for field in POLICY_FIELDS if field not in policy]
    probation = policy.get("probation_margin")
    if probation is not None and "non_inferiority_margin" in policy and not policy["non_inferiority_margin"] <= probation <= MAX_PROBATION_MARGIN:
        problems.append(f"policy.probation_margin must be between non_inferiority_margin and {MAX_PROBATION_MARGIN}")
    return problems
