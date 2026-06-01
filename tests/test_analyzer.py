"""Tests for AnalysisEngine."""

import pytest

from engine.analyzer import AnalysisEngine
from engine.constants import SYNC_ALGORITHM_NAMES

ANALYZER = AnalysisEngine()


class TestAnalyzeSyncConstants:
    def test_sync_algorithm_names_in_constants_not_analyzer(self):
        """SyncSimulatorNames must no longer be defined in analyzer.py."""
        import engine.analyzer as mod
        assert not hasattr(mod, "SyncSimulatorNames"), (
            "SyncSimulatorNames should be in constants.py, not analyzer.py"
        )

    def test_constants_module_has_names(self):
        assert len(SYNC_ALGORITHM_NAMES) == 10
        ids = {a["id"] for a in SYNC_ALGORITHM_NAMES}
        assert "mutex" in ids
        assert "monitor" in ids


class TestAnalyzeSync:
    MUTEX_RESULT = {
        "algorithm": "mutex",
        "summary": {"mutual_exclusion": True, "race_detected": False, "deadlock": False},
    }
    RACE_RESULT = {
        "algorithm": "race_condition",
        "summary": {"mutual_exclusion": False, "race_detected": True, "deadlock": False},
    }

    def test_returns_required_keys(self):
        r = ANALYZER.analyze_sync([self.MUTEX_RESULT])
        for key in ("rankings", "best", "worst", "explanation", "recommendation"):
            assert key in r

    def test_best_has_highest_score(self):
        r = ANALYZER.analyze_sync([self.MUTEX_RESULT, self.RACE_RESULT])
        assert r["best"]["algorithm"] == "mutex"

    def test_race_detected_lowers_score(self):
        r = ANALYZER.analyze_sync([self.RACE_RESULT])
        assert r["best"]["score"] < 60  # base 50 − 40 = 10, capped at 20

    def test_deadlock_lowers_score(self):
        deadlock_result = {
            "algorithm": "deadlock_demo",
            "summary": {"mutual_exclusion": False, "race_detected": False, "deadlock": True},
        }
        r = ANALYZER.analyze_sync([deadlock_result])
        assert r["best"]["score"] < 40

    def test_empty_results_returns_error(self):
        r = ANALYZER.analyze_sync([])
        assert "error" in r

    def test_deadlock_detected_when_deadlock_present(self):
        deadlock_result = {
            "algorithm": "deadlock_demo",
            "summary": {"deadlock": True},
        }
        r = ANALYZER.analyze_sync([deadlock_result])
        assert r["deadlock_detected"] is True
        assert r["starvation_detected"] is False


class TestAnalyzeScheduling:
    COMPARISONS = {
        "fcfs": {"averages": {"avg_waiting": 5.0, "avg_turnaround": 10.0, "avg_response": 3.0, "throughput": 0.3}},
        "sjf":  {"averages": {"avg_waiting": 2.0, "avg_turnaround": 7.0,  "avg_response": 2.0, "throughput": 0.4}},
    }

    def test_best_is_lowest_avg_waiting(self):
        r = ANALYZER.analyze_scheduling(self.COMPARISONS)
        assert r["best"]["algorithm"] == "sjf"

    def test_worst_is_highest_avg_waiting(self):
        r = ANALYZER.analyze_scheduling(self.COMPARISONS)
        assert r["worst"]["algorithm"] == "fcfs"

    def test_empty_returns_error(self):
        r = ANALYZER.analyze_scheduling({})
        assert "error" in r


class TestBuildLlmContext:
    def test_returns_string(self):
        phase1 = {
            "comparisons": {
                "fcfs": {"averages": {"avg_waiting": 5, "avg_turnaround": 10, "throughput": 0.3}}
            },
            "primary_algorithm": "fcfs",
        }
        phase2 = {
            "sync_comparison": {
                "rankings": [{"name": "Mutex", "score": 92, "strengths": ["Simple"]}],
                "best": {"name": "Mutex", "score": 92},
            }
        }
        ctx = ANALYZER.build_llm_context(phase1, phase2)
        assert isinstance(ctx, str)
        assert "FCFS" in ctx
        assert "Mutex" in ctx
