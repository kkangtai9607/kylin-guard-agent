from __future__ import annotations

from enum import Enum


class TaskState(str, Enum):
    RECEIVED = "RECEIVED"
    INPUT_GUARD = "INPUT_GUARD"
    INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
    CONTEXT_COLLECTING = "CONTEXT_COLLECTING"
    PLANNED = "PLANNED"
    PLAN_GUARD = "PLAN_GUARD"
    TOOL_CALLING = "TOOL_CALLING"
    EVIDENCE_READY = "EVIDENCE_READY"
    ROOT_CAUSE_ANALYZED = "ROOT_CAUSE_ANALYZED"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    ACTION_GUARD = "ACTION_GUARD"
    DRY_RUN = "DRY_RUN"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    BACKING_UP = "BACKING_UP"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    ROLLING_BACK = "ROLLING_BACK"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"


TERMINAL = {
    TaskState.SUCCEEDED,
    TaskState.FAILED,
    TaskState.BLOCKED,
    TaskState.ROLLED_BACK,
    TaskState.CANCELLED,
}
TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.RECEIVED: {TaskState.INPUT_GUARD, TaskState.CANCELLED},
    TaskState.INPUT_GUARD: {TaskState.INTENT_CLASSIFIED, TaskState.BLOCKED, TaskState.FAILED},
    TaskState.INTENT_CLASSIFIED: {
        TaskState.CONTEXT_COLLECTING,
        TaskState.BLOCKED,
        TaskState.FAILED,
    },
    TaskState.CONTEXT_COLLECTING: {TaskState.PLANNED, TaskState.BLOCKED, TaskState.FAILED},
    TaskState.PLANNED: {TaskState.PLAN_GUARD, TaskState.BLOCKED, TaskState.FAILED},
    TaskState.PLAN_GUARD: {TaskState.TOOL_CALLING, TaskState.BLOCKED, TaskState.FAILED},
    TaskState.TOOL_CALLING: {TaskState.EVIDENCE_READY, TaskState.BLOCKED, TaskState.FAILED},
    TaskState.EVIDENCE_READY: {
        TaskState.ROOT_CAUSE_ANALYZED,
        TaskState.SUCCEEDED,
        TaskState.FAILED,
    },
    TaskState.ROOT_CAUSE_ANALYZED: {
        TaskState.ACTION_PROPOSED,
        TaskState.SUCCEEDED,
        TaskState.FAILED,
    },
    TaskState.ACTION_PROPOSED: {TaskState.ACTION_GUARD, TaskState.CANCELLED},
    TaskState.ACTION_GUARD: {TaskState.DRY_RUN, TaskState.BLOCKED, TaskState.FAILED},
    TaskState.DRY_RUN: {TaskState.WAITING_APPROVAL, TaskState.FAILED},
    TaskState.WAITING_APPROVAL: {TaskState.APPROVED, TaskState.BLOCKED, TaskState.CANCELLED},
    TaskState.APPROVED: {TaskState.BACKING_UP, TaskState.BLOCKED},
    TaskState.BACKING_UP: {TaskState.EXECUTING, TaskState.FAILED},
    TaskState.EXECUTING: {TaskState.VERIFYING, TaskState.FAILED},
    TaskState.VERIFYING: {TaskState.SUCCEEDED, TaskState.ROLLING_BACK},
    TaskState.ROLLING_BACK: {TaskState.ROLLED_BACK, TaskState.FAILED},
}


def can_transition(current: TaskState, target: TaskState) -> bool:
    return current not in TERMINAL and target in TRANSITIONS.get(current, set())
