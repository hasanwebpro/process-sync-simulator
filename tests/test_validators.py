"""Tests for input validation helpers."""

import pytest

from engine.validators import (
    ValidationError,
    validate_processes,
    validate_quantum,
    validate_sched_algorithms,
    validate_sync_algorithms,
    validate_sync_config,
)


# ---------------------------------------------------------------------------
# validate_processes
# ---------------------------------------------------------------------------

class TestValidateProcesses:
    VALID = [
        {"pid": "P1", "arrival": 0, "burst": 5, "priority": 1},
        {"pid": "P2", "arrival": 1, "burst": 3, "priority": 2},
    ]

    def test_valid_input_returns_cleaned_list(self):
        result = validate_processes(self.VALID)
        assert len(result) == 2
        assert result[0]["pid"] == "P1"
        assert result[0]["burst"] == 5

    def test_not_a_list_raises(self):
        with pytest.raises(ValidationError, match="array"):
            validate_processes({"pid": "P1"})

    def test_empty_list_raises(self):
        with pytest.raises(ValidationError):
            validate_processes([])

    def test_too_many_processes_raises(self):
        procs = [{"pid": f"P{i}", "arrival": 0, "burst": 1, "priority": 1} for i in range(21)]
        with pytest.raises(ValidationError, match="Maximum"):
            validate_processes(procs)

    def test_duplicate_pid_raises(self):
        procs = [
            {"pid": "P1", "arrival": 0, "burst": 5, "priority": 1},
            {"pid": "P1", "arrival": 1, "burst": 3, "priority": 2},
        ]
        with pytest.raises(ValidationError, match="Duplicate"):
            validate_processes(procs)

    def test_burst_zero_raises(self):
        with pytest.raises(ValidationError, match="burst"):
            validate_processes([{"pid": "P1", "arrival": 0, "burst": 0, "priority": 1}])

    def test_negative_arrival_raises(self):
        with pytest.raises(ValidationError, match="arrival"):
            validate_processes([{"pid": "P1", "arrival": -1, "burst": 5, "priority": 1}])

    def test_non_integer_burst_raises(self):
        with pytest.raises(ValidationError, match="burst"):
            validate_processes([{"pid": "P1", "arrival": 0, "burst": "abc", "priority": 1}])

    def test_pid_too_long_raises(self):
        with pytest.raises(ValidationError, match="too long"):
            validate_processes([{"pid": "A" * 17, "arrival": 0, "burst": 1, "priority": 1}])

    def test_missing_pid_gets_default(self):
        result = validate_processes([{"arrival": 0, "burst": 5, "priority": 1}])
        assert result[0]["pid"] == "P1"

    def test_string_numbers_are_coerced(self):
        result = validate_processes([{"pid": "P1", "arrival": "0", "burst": "5", "priority": "1"}])
        assert result[0]["arrival"] == 0
        assert result[0]["burst"] == 5


# ---------------------------------------------------------------------------
# validate_sched_algorithms
# ---------------------------------------------------------------------------

class TestValidateSchedAlgorithms:
    def test_valid_single(self):
        assert validate_sched_algorithms(["fcfs"]) == ["fcfs"]

    def test_valid_multiple(self):
        result = validate_sched_algorithms(["fcfs", "sjf", "round_robin"])
        assert len(result) == 3

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_sched_algorithms([])

    def test_unknown_algorithm_raises(self):
        with pytest.raises(ValidationError, match="Unknown"):
            validate_sched_algorithms(["fcfs", "banana"])

    def test_not_a_list_raises(self):
        with pytest.raises(ValidationError):
            validate_sched_algorithms("fcfs")


# ---------------------------------------------------------------------------
# validate_sync_algorithms
# ---------------------------------------------------------------------------

class TestValidateSyncAlgorithms:
    def test_valid(self):
        assert validate_sync_algorithms(["mutex"]) == ["mutex"]

    def test_multiple_valid(self):
        result = validate_sync_algorithms(["mutex", "monitor", "binary_semaphore"])
        assert len(result) == 3

    def test_unknown_raises(self):
        with pytest.raises(ValidationError, match="Unknown"):
            validate_sync_algorithms(["mutex", "not_real"])

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_sync_algorithms([])


# ---------------------------------------------------------------------------
# validate_quantum
# ---------------------------------------------------------------------------

class TestValidateQuantum:
    def test_valid_integer(self):
        assert validate_quantum(2) == 2

    def test_string_integer_coerced(self):
        assert validate_quantum("4") == 4

    def test_zero_raises(self):
        with pytest.raises(ValidationError):
            validate_quantum(0)

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            validate_quantum(-1)

    def test_too_large_raises(self):
        with pytest.raises(ValidationError):
            validate_quantum(101)

    def test_non_numeric_raises(self):
        with pytest.raises(ValidationError):
            validate_quantum("abc")


# ---------------------------------------------------------------------------
# validate_sync_config
# ---------------------------------------------------------------------------

class TestValidateSyncConfig:
    def test_none_returns_empty_dict(self):
        assert validate_sync_config(None) == {}

    def test_valid_config(self):
        cfg = {"processes": 3, "iterations": 3, "buffer_size": 5, "items": 4, "slots": 2}
        result = validate_sync_config(cfg)
        assert result["processes"] == 3
        assert result["iterations"] == 3
        assert result["buffer_size"] == 5
        assert result["items"] == 4

    def test_corrected_bool_preserved(self):
        result = validate_sync_config({"corrected": True})
        assert result["corrected"] is True

    def test_out_of_range_raises(self):
        with pytest.raises(ValidationError, match="iterations"):
            validate_sync_config({"iterations": 0})

    def test_not_a_dict_raises(self):
        with pytest.raises(ValidationError):
            validate_sync_config("bad")

    def test_unknown_keys_ignored(self):
        result = validate_sync_config({"iterations": 2, "unknown_key": 99})
        assert "unknown_key" not in result
