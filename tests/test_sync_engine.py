"""Tests for SyncSimulator — all 10 synchronization algorithms."""

import pytest

from engine.sync_engine import SyncSimulator

SIM = SyncSimulator()

ALL_ALGORITHMS = [
    "peterson",
    "dekker",
    "mutex",
    "binary_semaphore",
    "counting_semaphore",
    "producer_consumer",
    "readers_writers",
    "monitor",
    "race_condition",
    "deadlock_demo",
]


# ---------------------------------------------------------------------------
# General contract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", ALL_ALGORITHMS)
class TestSyncContract:
    def test_returns_required_keys(self, algo):
        r = SIM.run(algo)
        for key in ("algorithm", "steps", "summary", "total_ticks"):
            assert key in r, f"Missing key '{key}' in {algo} result"

    def test_steps_is_non_empty_list(self, algo):
        r = SIM.run(algo)
        assert isinstance(r["steps"], list)
        assert len(r["steps"]) > 0

    def test_total_ticks_matches_steps_length(self, algo):
        r = SIM.run(algo)
        assert r["total_ticks"] == len(r["steps"])

    def test_each_step_has_required_fields(self, algo):
        r = SIM.run(algo)
        for step in r["steps"]:
            for field in ("tick", "processes", "action", "message"):
                assert field in step, f"{algo}: step missing field '{field}'"

    def test_unknown_algorithm_raises(self, algo):
        with pytest.raises(ValueError, match="Unknown"):
            SIM.run("not_a_real_algo")


# ---------------------------------------------------------------------------
# Mutual exclusion — only one process in CS at a time
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", [
    "peterson", "dekker", "mutex", "binary_semaphore",
    "counting_semaphore", "monitor",
])
def test_mutual_exclusion(algo):
    """At most one process should be in the critical section per step
    for single-slot algorithms."""
    r = SIM.run(algo, {"processes": 3, "iterations": 2, "slots": 1})
    for step in r["steps"]:
        cs = step.get("critical_section", [])
        assert len(cs) <= 1, (
            f"{algo}: multiple processes in CS at tick {step['tick']}: {cs}"
        )


# ---------------------------------------------------------------------------
# Peterson's Solution
# ---------------------------------------------------------------------------

class TestPeterson:
    def test_summary_flags_mutual_exclusion(self):
        r = SIM.run("peterson", {"iterations": 2})
        assert r["summary"]["mutual_exclusion"] is True

    def test_summary_flags_deadlock_free(self):
        r = SIM.run("peterson", {"iterations": 2})
        assert r["summary"]["deadlock_free"] is True

    def test_counter_increments_correctly(self):
        iterations = 3
        r = SIM.run("peterson", {"iterations": iterations})
        # 2 processes × iterations
        assert r["summary"]["final_counter"] == 2 * iterations


# ---------------------------------------------------------------------------
# Mutex
# ---------------------------------------------------------------------------

class TestMutex:
    def test_counter_is_correct(self):
        r = SIM.run("mutex", {"processes": 3, "iterations": 2})
        assert r["summary"]["final_counter"] == 3 * 2

    def test_last_step_is_done(self):
        r = SIM.run("mutex", {"processes": 2, "iterations": 1})
        assert r["steps"][-1]["action"] == "done"


# ---------------------------------------------------------------------------
# Producer–Consumer
# ---------------------------------------------------------------------------

class TestSemaphores:
    def test_blocked_process_wakes_only_after_v_signal(self):
        r = SIM.run("binary_semaphore", {"processes": 2, "iterations": 1})
        actions = [step["action"] for step in r["steps"]]
        block_idx = actions.index("block")
        wake_idx = actions.index("wakeup")
        assert "V_signal" in actions[block_idx:wake_idx]


class TestProducerConsumer:
    def test_produced_equals_consumed(self):
        r = SIM.run("producer_consumer", {"buffer_size": 5, "items": 4})
        assert r["summary"]["produced"] == r["summary"]["consumed"]

    def test_buffer_never_exceeds_size(self):
        buffer_size = 3
        r = SIM.run("producer_consumer", {"buffer_size": buffer_size, "items": 6})
        for step in r["steps"]:
            buf = step.get("shared_vars", {}).get("buffer", [])
            assert len(buf) <= buffer_size


# ---------------------------------------------------------------------------
# Readers-Writers
# ---------------------------------------------------------------------------

class TestReadersWriters:
    def test_readers_can_share_critical_section(self):
        r = SIM.run("readers_writers", {"readers": 2, "writers": 1, "operations": 1})
        assert any(
            len(step.get("critical_section", [])) > 1
            and all(pid.startswith("R") for pid in step.get("critical_section", []))
            for step in r["steps"]
        )

    def test_writer_does_not_overlap_readers(self):
        r = SIM.run("readers_writers", {"readers": 2, "writers": 1, "operations": 1})
        for step in r["steps"]:
            cs = step.get("critical_section", [])
            if any(pid.startswith("W") for pid in cs):
                assert len(cs) == 1


# ---------------------------------------------------------------------------
# Deadlock Demo
# ---------------------------------------------------------------------------

class TestDeadlockDemo:
    def test_summary_reports_deadlock(self):
        r = SIM.run("deadlock_demo")
        assert r["summary"]["deadlock"] is True

    def test_processes_end_blocked(self):
        r = SIM.run("deadlock_demo")
        last = r["steps"][-1]
        for state in last["processes"].values():
            assert state == "BLOCKED"


# ---------------------------------------------------------------------------
# Race Condition
# ---------------------------------------------------------------------------

class TestRaceCondition:
    def test_unsafe_mode_detects_race(self):
        r = SIM.run("race_condition", {"processes": 3, "increments": 5, "corrected": False})
        assert r["summary"]["race_detected"] is True

    def test_safe_mode_no_race(self):
        r = SIM.run("race_condition", {"processes": 3, "increments": 5, "corrected": True})
        assert r["summary"]["race_detected"] is False
        assert r["summary"]["final_counter"] == r["summary"]["expected"]
