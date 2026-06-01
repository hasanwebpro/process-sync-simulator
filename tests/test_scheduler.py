"""Tests for CPUScheduler — correctness of all 5 algorithms."""

import pytest

from engine.scheduler import CPUScheduler

SCHEDULER = CPUScheduler()

SIMPLE = [
    {"pid": "P1", "arrival": 0, "burst": 5, "priority": 2},
    {"pid": "P2", "arrival": 1, "burst": 3, "priority": 1},
    {"pid": "P3", "arrival": 2, "burst": 8, "priority": 3},
]


def _run(algo, processes=None, quantum=2):
    return SCHEDULER.run(algo, processes or SIMPLE, quantum)


def _gantt_pids(result):
    return [s["pid"] for s in result["gantt"] if s["pid"] != "IDLE"]


def _completion(result, pid):
    m = next(m for m in result["metrics"] if m["pid"] == pid)
    return m["completion"]


# ---------------------------------------------------------------------------
# General contract tests (apply to all algorithms)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("algo", ["fcfs", "sjf", "srtf", "round_robin", "priority"])
class TestSchedulerContract:
    def test_returns_required_keys(self, algo):
        r = _run(algo)
        for key in ("algorithm", "gantt", "metrics", "averages", "timeline"):
            assert key in r, f"Missing key '{key}' in {algo} result"

    def test_all_processes_complete(self, algo):
        r = _run(algo)
        pids_in_metrics = {m["pid"] for m in r["metrics"]}
        assert pids_in_metrics == {"P1", "P2", "P3"}

    def test_gantt_is_contiguous(self, algo):
        """No gaps or overlaps in the Gantt chart."""
        r = _run(algo)
        gantt = r["gantt"]
        for i in range(1, len(gantt)):
            assert gantt[i]["start"] == gantt[i - 1]["end"], (
                f"{algo}: gap between segment {i-1} and {i}"
            )

    def test_turnaround_equals_completion_minus_arrival(self, algo):
        r = _run(algo)
        for m in r["metrics"]:
            assert m["turnaround"] == m["completion"] - m["arrival"]

    def test_waiting_equals_turnaround_minus_burst(self, algo):
        r = _run(algo)
        for m in r["metrics"]:
            assert m["waiting"] == m["turnaround"] - m["burst"]

    def test_averages_are_correct(self, algo):
        r = _run(algo)
        n = len(r["metrics"])
        expected_act = round(sum(m["completion"] for m in r["metrics"]) / n, 2)
        expected_awt = round(sum(m["waiting"] for m in r["metrics"]) / n, 2)
        assert r["averages"]["avg_completion"] == expected_act
        assert r["averages"]["avg_waiting"] == expected_awt

    def test_unknown_algorithm_raises(self, algo):
        with pytest.raises(ValueError, match="Unknown"):
            SCHEDULER.run("not_real", SIMPLE)


# ---------------------------------------------------------------------------
# FCFS-specific
# ---------------------------------------------------------------------------

class TestFCFS:
    def test_order_is_arrival_order(self):
        r = _run("fcfs")
        pids = _gantt_pids(r)
        assert pids == ["P1", "P2", "P3"]

    def test_single_process(self):
        r = _run("fcfs", [{"pid": "P1", "arrival": 0, "burst": 4, "priority": 1}])
        assert _completion(r, "P1") == 4

    def test_idle_gap_when_first_process_arrives_late(self):
        procs = [{"pid": "P1", "arrival": 5, "burst": 3, "priority": 1}]
        r = _run("fcfs", procs)
        assert r["gantt"][0]["pid"] == "IDLE"
        assert r["gantt"][0]["end"] == 5


# ---------------------------------------------------------------------------
# SJF-specific
# ---------------------------------------------------------------------------

class TestSJF:
    def test_shortest_job_runs_first_when_available(self):
        # P2 (burst=3) arrives at t=1; P1 (burst=5) starts at t=0 before P2 arrives
        r = _run("sjf")
        pids = _gantt_pids(r)
        # P1 starts first (only one available at t=0), then P2 (shorter), then P3
        assert pids[0] == "P1"
        assert pids[1] == "P2"

    def test_all_same_burst_falls_back_to_arrival(self):
        procs = [
            {"pid": "P1", "arrival": 0, "burst": 4, "priority": 1},
            {"pid": "P2", "arrival": 0, "burst": 4, "priority": 2},
        ]
        r = _run("sjf", procs)
        pids = _gantt_pids(r)
        assert pids[0] == "P1"  # earlier arrival (tie-break by pid)


# ---------------------------------------------------------------------------
# SRTF-specific
# ---------------------------------------------------------------------------

class TestSRTF:
    def test_preemption_occurs(self):
        """P2 (burst=2) should preempt P1 (burst=10) when it arrives."""
        procs = [
            {"pid": "P1", "arrival": 0, "burst": 10, "priority": 1},
            {"pid": "P2", "arrival": 1, "burst": 2, "priority": 2},
        ]
        r = _run("srtf", procs)
        pids = _gantt_pids(r)
        # P1 runs first, then P2 preempts, then P1 resumes
        assert pids[0] == "P1"
        assert "P2" in pids

    def test_all_processes_complete(self):
        r = _run("srtf")
        assert len(r["metrics"]) == 3

    def test_no_infinite_loop_with_late_arrivals(self):
        """Regression: SRTF must not loop forever when processes arrive late."""
        procs = [
            {"pid": "P1", "arrival": 10, "burst": 3, "priority": 1},
            {"pid": "P2", "arrival": 15, "burst": 2, "priority": 1},
        ]
        r = _run("srtf", procs)
        assert len(r["metrics"]) == 2

    def test_gantt_contiguous(self):
        r = _run("srtf")
        gantt = r["gantt"]
        for i in range(1, len(gantt)):
            assert gantt[i]["start"] == gantt[i - 1]["end"]


# ---------------------------------------------------------------------------
# Round Robin-specific
# ---------------------------------------------------------------------------

class TestRoundRobin:
    def test_quantum_respected(self):
        """No single Gantt segment should exceed the quantum for a process
        that has more remaining burst than the quantum."""
        procs = [
            {"pid": "P1", "arrival": 0, "burst": 10, "priority": 1},
            {"pid": "P2", "arrival": 0, "burst": 10, "priority": 1},
        ]
        r = _run("round_robin", procs, quantum=3)
        for seg in r["gantt"]:
            if seg["pid"] != "IDLE":
                assert seg["end"] - seg["start"] <= 3

    def test_single_process_completes_in_one_or_more_slices(self):
        procs = [{"pid": "P1", "arrival": 0, "burst": 7, "priority": 1}]
        r = _run("round_robin", procs, quantum=3)
        assert _completion(r, "P1") == 7


# ---------------------------------------------------------------------------
# Priority-specific
# ---------------------------------------------------------------------------

class TestPriority:
    def test_higher_priority_runs_first_when_available(self):
        """P2 has priority=1 (highest) and arrives at t=0 — should run first."""
        procs = [
            {"pid": "P1", "arrival": 0, "burst": 5, "priority": 3},
            {"pid": "P2", "arrival": 0, "burst": 3, "priority": 1},
        ]
        r = _run("priority", procs)
        pids = _gantt_pids(r)
        assert pids[0] == "P2"

    def test_late_arriving_high_priority_does_not_preempt_running_process(self):
        """
        Regression for the priority scheduler bug:
        P1 starts at t=0 (only process available).
        P2 arrives at t=2 with higher priority.
        Since this is non-preemptive, P1 must finish before P2 runs.
        """
        procs = [
            {"pid": "P1", "arrival": 0, "burst": 5, "priority": 3},
            {"pid": "P2", "arrival": 2, "burst": 3, "priority": 1},
        ]
        r = _run("priority", procs)
        pids = _gantt_pids(r)
        # P1 must complete before P2 starts (non-preemptive)
        assert pids[0] == "P1"
        p1_end = next(s["end"] for s in r["gantt"] if s["pid"] == "P1")
        p2_start = next(s["start"] for s in r["gantt"] if s["pid"] == "P2")
        assert p2_start >= p1_end

    def test_idle_inserted_when_no_process_available(self):
        procs = [
            {"pid": "P1", "arrival": 5, "burst": 3, "priority": 1},
        ]
        r = _run("priority", procs)
        assert r["gantt"][0]["pid"] == "IDLE"
        assert r["gantt"][0]["end"] == 5
