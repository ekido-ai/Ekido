"""Quality Guard statistics: a paired non-inferiority test on per-example correctness.

The decision: pass if the one-sided lower confidence bound of (candidate - reference) accuracy is
at least -margin. A pass means "no degradation detected beyond the margin", not that the models
are equivalent. Standard library only.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class PairedComparison:
    n: int
    candidate_accuracy: float
    reference_accuracy: float
    difference: float
    ci_lower: float
    confidence: float
    resamples: int
    candidate_only_correct: int
    reference_only_correct: int
    mcnemar_p: float


@dataclass(frozen=True)
class Decision:
    verdict: str  # "PASS" or "FAIL"
    reasons: list[str] = field(default_factory=list)


def mcnemar_exact_p(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts. Reported only, never decides."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # Sum in log space, so large counts don't overflow.
    log_half = n * math.log(0.5)
    tail = sum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + log_half) for i in range(k + 1))
    return min(1.0, 2.0 * tail)


def compare_paired(
    candidate_correct: Sequence[bool],
    reference_correct: Sequence[bool],
    *,
    confidence: float,
    resamples: int,
    seed: int,
) -> PairedComparison:
    """Paired bootstrap of the accuracy difference.

    Only discordant pairs affect the difference, so each resample draws just two counts from the
    multinomial instead of touching every example. This is exactly equivalent to resampling
    examples and takes milliseconds.
    """
    n = len(candidate_correct)
    if n == 0:
        raise ValueError("no examples to compare")
    if len(reference_correct) != n:
        raise ValueError(f"evaluations are not comparable: {n} vs {len(reference_correct)} examples")
    if not 0.5 < confidence < 1:
        raise ValueError("confidence must be between 0.5 and 1")
    if resamples < 1:
        raise ValueError("resamples must be positive")

    candidate_total = sum(1 for c in candidate_correct if c)
    reference_total = sum(1 for r in reference_correct if r)
    b = sum(1 for c, r in zip(candidate_correct, reference_correct) if c and not r)
    c = sum(1 for c, r in zip(candidate_correct, reference_correct) if r and not c)

    rng = random.Random(seed)
    p_b = b / n
    p_c_given_not_b = c / (n - b) if n > b else 0.0
    differences = []
    for _ in range(resamples):
        draw_b = rng.binomialvariate(n, p_b)
        draw_c = rng.binomialvariate(n - draw_b, p_c_given_not_b)
        differences.append((draw_b - draw_c) / n)
    differences.sort()
    index = min(resamples - 1, math.floor((1 - confidence) * resamples))

    return PairedComparison(
        n=n,
        candidate_accuracy=candidate_total / n,
        reference_accuracy=reference_total / n,
        difference=(b - c) / n,
        ci_lower=differences[index],
        confidence=confidence,
        resamples=resamples,
        candidate_only_correct=b,
        reference_only_correct=c,
        mcnemar_p=mcnemar_exact_p(b, c),
    )


def macro_f1(predictions: Sequence[int], labels: Sequence[int]) -> float:
    """Reported alongside accuracy. Classes absent from both predictions and labels are ignored."""
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels differ in length")
    classes = set(predictions) | set(labels)
    if not classes:
        raise ValueError("no examples")
    scores = []
    for cls in classes:
        tp = sum(1 for p, y in zip(predictions, labels) if p == cls and y == cls)
        fp = sum(1 for p, y in zip(predictions, labels) if p == cls and y != cls)
        fn = sum(1 for p, y in zip(predictions, labels) if p != cls and y == cls)
        scores.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(scores) / len(scores)


def margin_for(policy: dict, is_final: bool) -> float:
    """Honest training dips between checkpoints, so mid-training checks can use a wider margin. The final check never does."""
    if is_final:
        return policy["non_inferiority_margin"]
    return policy.get("probation_margin", policy["non_inferiority_margin"])


def decide(
    comparison: PairedComparison,
    *,
    margin: float,
    min_absolute: float,
    is_final: bool,
    signature_valid: bool = True,
    lineage_valid: bool = True,
    no_nan_inf: bool = True,
    weights_changed: bool = True,
) -> Decision:
    """Apply the policy. Every failed rule is reported, so the UI can explain the verdict."""
    reasons = []
    if not signature_valid:
        reasons.append("INVALID_SIGNATURE")
    if not lineage_valid:
        reasons.append("INVALID_LINEAGE")
    if not no_nan_inf:
        reasons.append("NAN_OR_INF")
    if not weights_changed:
        reasons.append("WEIGHTS_UNCHANGED")
    if comparison.ci_lower < -margin:
        reasons.append("NON_INFERIORITY_FAILED")
    if is_final and comparison.candidate_accuracy < min_absolute:
        reasons.append("BELOW_ABSOLUTE_FLOOR")
    return Decision("FAIL" if reasons else "PASS", reasons)
