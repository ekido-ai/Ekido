"""Job lifecycle rules, shared by the coordinator and its tests. Matches plan.md section C."""

from __future__ import annotations

from enum import StrEnum


class JobState(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    RECOVERING = "RECOVERING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DISPUTED = "DISPUTED"
    REFUNDED = "REFUNDED"


S = JobState

TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    S.OPEN: frozenset({S.ASSIGNED, S.CANCELLED}),
    S.ASSIGNED: frozenset({S.RUNNING, S.RECOVERING}),
    S.RUNNING: frozenset({S.RECOVERING, S.VALIDATING}),
    S.RECOVERING: frozenset({S.RUNNING, S.FAILED}),
    S.VALIDATING: frozenset({S.COMPLETED, S.RECOVERING, S.FAILED}),
    S.COMPLETED: frozenset({S.SETTLED, S.DISPUTED}),
    S.DISPUTED: frozenset({S.SETTLED, S.REFUNDED}),
    S.FAILED: frozenset({S.REFUNDED}),
    S.SETTLED: frozenset(),
    S.REFUNDED: frozenset(),
    S.CANCELLED: frozenset(),
}

TERMINAL = frozenset(state for state, targets in TRANSITIONS.items() if not targets)

# Coarse on-chain state for each off-chain state, matching GPUChainEscrow.State.
ONCHAIN_STATE: dict[JobState, str] = {
    S.OPEN: "Funded",
    S.ASSIGNED: "Active",
    S.RUNNING: "Active",
    S.RECOVERING: "Active",
    S.VALIDATING: "Active",
    S.COMPLETED: "Attested",
    S.DISPUTED: "Disputed",
    S.SETTLED: "Settled",
    S.FAILED: "Active",  # Becomes Refunded once the failure verdict or timeout refund lands.
    S.REFUNDED: "Refunded",
    S.CANCELLED: "Cancelled",
}


class IllegalTransition(ValueError):
    pass


def check_transition(current: JobState, target: JobState) -> None:
    if target not in TRANSITIONS.get(current, frozenset()):
        raise IllegalTransition(f"{current} cannot move to {target}")
