"""task.py 领域模型测试。"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from csx.domain.task import (
    ALLOWED_TRANSITIONS,
    InvalidTransition,
    TaskState,
    assert_transition,
    backoff_seconds,
    can_transition,
    next_retry_at,
    on_failure,
)


class TestTaskStateValues:
    def test_queued(self):
        assert TaskState.QUEUED == "queued"

    def test_running(self):
        assert TaskState.RUNNING == "running"

    def test_succeeded(self):
        assert TaskState.SUCCEEDED == "succeeded"

    def test_retry_wait(self):
        assert TaskState.RETRY_WAIT == "retry_wait"

    def test_failed(self):
        assert TaskState.FAILED == "failed"

    def test_dead_letter(self):
        assert TaskState.DEAD_LETTER == "dead_letter"

    def test_cancelled(self):
        assert TaskState.CANCELLED == "cancelled"


class TestAllowedTransitionsTable:
    """验证迁移表完全符合规格。"""

    def test_queued_allowed_targets(self):
        allowed = ALLOWED_TRANSITIONS[TaskState.QUEUED]
        assert allowed == frozenset({TaskState.RUNNING, TaskState.CANCELLED})

    def test_running_allowed_targets(self):
        allowed = ALLOWED_TRANSITIONS[TaskState.RUNNING]
        assert allowed == frozenset(
            {
                TaskState.SUCCEEDED,
                TaskState.RETRY_WAIT,
                TaskState.FAILED,
                TaskState.CANCELLED,
            }
        )

    def test_retry_wait_allowed_targets(self):
        allowed = ALLOWED_TRANSITIONS[TaskState.RETRY_WAIT]
        assert allowed == frozenset(
            {
                TaskState.RUNNING,
                TaskState.QUEUED,
                TaskState.CANCELLED,
                TaskState.DEAD_LETTER,
            }
        )

    def test_failed_allowed_targets(self):
        allowed = ALLOWED_TRANSITIONS[TaskState.FAILED]
        assert allowed == frozenset(
            {
                TaskState.RETRY_WAIT,
                TaskState.DEAD_LETTER,
                TaskState.CANCELLED,
            }
        )

    def test_dead_letter_allowed_targets(self):
        allowed = ALLOWED_TRANSITIONS[TaskState.DEAD_LETTER]
        assert allowed == frozenset({TaskState.QUEUED})

    def test_succeeded_is_terminal(self):
        assert ALLOWED_TRANSITIONS[TaskState.SUCCEEDED] == frozenset()

    def test_cancelled_is_terminal(self):
        assert ALLOWED_TRANSITIONS[TaskState.CANCELLED] == frozenset()


class TestCanTransition:
    def test_valid_queued_to_running(self):
        assert can_transition(TaskState.QUEUED, TaskState.RUNNING) is True

    def test_valid_queued_to_cancelled(self):
        assert can_transition(TaskState.QUEUED, TaskState.CANCELLED) is True

    def test_invalid_queued_to_succeeded(self):
        assert can_transition(TaskState.QUEUED, TaskState.SUCCEEDED) is False

    def test_valid_running_to_succeeded(self):
        assert can_transition(TaskState.RUNNING, TaskState.SUCCEEDED) is True

    def test_valid_running_to_retry_wait(self):
        assert can_transition(TaskState.RUNNING, TaskState.RETRY_WAIT) is True

    def test_valid_running_to_failed(self):
        assert can_transition(TaskState.RUNNING, TaskState.FAILED) is True

    def test_valid_retry_wait_to_running(self):
        assert can_transition(TaskState.RETRY_WAIT, TaskState.RUNNING) is True

    def test_valid_retry_wait_to_queued(self):
        assert can_transition(TaskState.RETRY_WAIT, TaskState.QUEUED) is True

    def test_valid_retry_wait_to_dead_letter(self):
        assert can_transition(TaskState.RETRY_WAIT, TaskState.DEAD_LETTER) is True

    def test_valid_failed_to_retry_wait(self):
        assert can_transition(TaskState.FAILED, TaskState.RETRY_WAIT) is True

    def test_valid_dead_letter_to_queued(self):
        assert can_transition(TaskState.DEAD_LETTER, TaskState.QUEUED) is True

    def test_invalid_succeeded_to_any(self):
        # SUCCEEDED 是终态
        assert can_transition(TaskState.SUCCEEDED, TaskState.QUEUED) is False
        assert can_transition(TaskState.SUCCEEDED, TaskState.RUNNING) is False

    def test_invalid_cancelled_to_any(self):
        # CANCELLED 是终态
        assert can_transition(TaskState.CANCELLED, TaskState.QUEUED) is False
        assert can_transition(TaskState.CANCELLED, TaskState.RUNNING) is False

    def test_same_state_not_allowed(self):
        # 同一状态之间的自转不允许（除了通过其他状态）
        assert can_transition(TaskState.QUEUED, TaskState.QUEUED) is False


class TestAssertTransition:
    def test_valid_transition_no_exception(self):
        assert_transition(TaskState.QUEUED, TaskState.RUNNING)

    def test_invalid_transition_raises(self):
        with pytest.raises(InvalidTransition):
            assert_transition(TaskState.QUEUED, TaskState.SUCCEEDED)

    def test_terminal_state_transition_raises(self):
        with pytest.raises(InvalidTransition):
            assert_transition(TaskState.SUCCEEDED, TaskState.RUNNING)

    def test_unrecognized_source_raises(self):
        # 源状态不存在（通过 can_transition 返回 False）
        with pytest.raises(InvalidTransition):
            assert_transition(TaskState.SUCCEEDED, TaskState.RUNNING)


BACKOFF_SEQUENCE = [60, 120, 240, 480, 960, 1800, 1800, 1800]


class TestBackoffSeconds:
    def test_attempt_one_returns_60(self):
        assert backoff_seconds(1) == 60

    def test_attempt_zero_treated_as_one(self):
        assert backoff_seconds(0) == 60

    def test_attempt_negative_treated_as_one(self):
        assert backoff_seconds(-1) == 60

    def test_attempt_two_returns_120(self):
        assert backoff_seconds(2) == 120

    def test_attempt_three_returns_240(self):
        assert backoff_seconds(3) == 240

    def test_attempt_four_returns_480(self):
        assert backoff_seconds(4) == 480

    def test_attempt_five_returns_960(self):
        assert backoff_seconds(5) == 960

    def test_attempt_six_capped_at_1800(self):
        assert backoff_seconds(6) == 1800

    def test_attempt_seven_still_capped_at_1800(self):
        assert backoff_seconds(7) == 1800

    def test_sequence_matches_spec(self):
        for i, expected in enumerate(BACKOFF_SEQUENCE, start=1):
            assert backoff_seconds(i) == expected, f"Failed at attempt {i}"

    def test_formula_validation(self):
        # attempt=1: 60 * 2**0 = 60 ✓
        # attempt=2: 60 * 2**1 = 120 ✓
        # attempt=3: 60 * 2**2 = 240 ✓
        for attempt in range(1, 7):
            expected = 60 if attempt == 1 else min(60 * (2 ** (attempt - 1)), 1800)
            assert backoff_seconds(attempt) == expected


class TestNextRetryAt:
    def test_naive_datetime(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        result = next_retry_at(now, 1)
        expected = datetime(2024, 1, 1, 12, 1, 0)
        assert result == expected

    def test_timezone_aware_datetime(self):

        now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = next_retry_at(now, 1)
        assert result.tzinfo is not None
        assert result.hour == 12
        assert result.minute == 1

    def test_output_matches_input_type(self):
        naive = datetime(2024, 1, 1, 12, 0, 0)
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.now().astimezone().tzinfo)

        naive_result = next_retry_at(naive, 2)
        aware_result = next_retry_at(aware, 2)

        assert (naive_result.tzinfo is None) == (naive.tzinfo is None)
        assert (aware_result.tzinfo is not None) == (aware.tzinfo is not None)

    def test_different_attempts(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        r1 = next_retry_at(now, 1)
        r2 = next_retry_at(now, 2)
        r3 = next_retry_at(now, 3)
        assert r2 > r1
        assert r3 > r2


class TestOnFailure:
    def test_first_failure_to_retry_wait(self):
        state, attempt = on_failure(TaskState.RUNNING, 1)
        assert state == TaskState.RETRY_WAIT
        assert attempt == 2

    def test_second_failure_to_retry_wait(self):
        # on_failure 的返回值取决于 attempt 而不是 state
        # attempt=1 < max_attempts(3)，所以 new_attempt=2 < 3 → RETRY_WAIT
        state, attempt = on_failure(TaskState.RUNNING, 1)
        assert state == TaskState.RETRY_WAIT
        assert attempt == 2

    def test_third_failure_to_dead_letter(self):
        # attempt=2 < max_attempts(3)，但 next call: new_attempt=3 >= 3 → DEAD_LETTER
        state, attempt = on_failure(TaskState.RETRY_WAIT, 2)
        assert state == TaskState.DEAD_LETTER
        assert attempt == 3

    def test_custom_max_attempts(self):
        # max_attempts=2，第一次失败就进 dead letter
        state, attempt = on_failure(TaskState.RUNNING, 1, max_attempts=2)
        assert state == TaskState.DEAD_LETTER
        assert attempt == 2

    def test_already_in_retry_wait(self):
        state, attempt = on_failure(TaskState.RETRY_WAIT, 1)
        assert state == TaskState.RETRY_WAIT
        assert attempt == 2

    def test_already_in_failed(self):
        state, attempt = on_failure(TaskState.FAILED, 1)
        assert state == TaskState.RETRY_WAIT
        assert attempt == 2

    def test_terminal_states_handled_gracefully(self):
        # 虽然 terminal states 不应该被 failure，但函数仍然有定义
        state, attempt = on_failure(TaskState.SUCCEEDED, 1)
        assert state == TaskState.RETRY_WAIT
        assert attempt == 2

    def test_multiple_failures_simulation(self):
        state = TaskState.RUNNING
        attempt = 1
        final_states = []
        final_attempts = []

        for _ in range(5):
            state, attempt = on_failure(state, attempt)
            final_states.append(state)
            final_attempts.append(attempt)

        # on_failure 不关心 input state，只根据 attempt 决定输出
        # attempt=1 → DEAD_LETTER (new attempt=2 < 3? no, 2<3 so RETRY_WAIT)
        # attempt=2 → DEAD_LETTER (new attempt=3 >= 3)
        # 所以：
        assert final_states[0] == TaskState.RETRY_WAIT  # attempt 1+1=2 < 3
        assert final_states[1] == TaskState.DEAD_LETTER  # attempt 2+1=3 >= 3
        assert final_states[2] == TaskState.DEAD_LETTER  # attempt 3+1=4 >= 3
        assert final_attempts[2] == 4
