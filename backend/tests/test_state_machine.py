from backend.app.agent.state_machine import TaskState, can_transition


def test_legal_transition() -> None:
    assert can_transition(TaskState.RECEIVED, TaskState.INPUT_GUARD)


def test_illegal_and_terminal_transitions() -> None:
    assert not can_transition(TaskState.RECEIVED, TaskState.EXECUTING)
    assert not can_transition(TaskState.SUCCEEDED, TaskState.INPUT_GUARD)
