"""
validators.py — Input sanitisation layer
=========================================

All user-supplied data passes through these functions before reaching any
simulation engine.  Raising ValidationError (a subclass of ValueError) keeps
error handling uniform: Flask routes catch it and return a 400 JSON response
with a student-friendly message.

Why validate at the boundary?
    The simulation engines assume clean data (integer burst times, unique PIDs,
    etc.).  Validating once here means every engine function can skip defensive
    checks and focus on algorithmic logic.
"""

from __future__ import annotations

from typing import Any

from .constants import (
    PROCESS_CONSTRAINTS as PC,
    VALID_SCHED_ALGORITHMS,
    VALID_SYNC_ALGORITHMS,
)


class ValidationError(ValueError):
    """
    Raised when user-supplied input fails a validation rule.

    Inherits from ValueError so callers that catch ValueError also catch this,
    but the distinct type lets us write specific except clauses in Flask routes.
    """


# ---------------------------------------------------------------------------
# Process table validation
# ---------------------------------------------------------------------------

def validate_processes(processes: Any) -> list[dict]:
    """
    Validate and normalise a JSON array of process descriptors.

    Each process must supply:
        pid      — unique string identifier (e.g. "P1")
        arrival  — integer arrival time  ≥ 0  (when the process enters the ready queue)
        burst    — integer burst time    ≥ 1  (total CPU time the process needs)
        priority — integer priority      ≥ 1  (lower number = higher urgency)

    Returns a cleaned list of dicts or raises ValidationError.

    Design note: PIDs are deduplicated here because duplicate PIDs would cause
    dict-key collisions in the scheduler's completion/first_run tables.
    """
    if not isinstance(processes, list):
        raise ValidationError("'processes' must be a JSON array.")

    if len(processes) < PC["min_processes"]:
        raise ValidationError(
            f"At least {PC['min_processes']} process is required."
        )
    if len(processes) > PC["max_processes"]:
        raise ValidationError(
            f"Maximum {PC['max_processes']} processes allowed; got {len(processes)}."
        )

    seen_pids: set[str] = set()
    cleaned:   list[dict] = []

    for i, p in enumerate(processes):
        if not isinstance(p, dict):
            raise ValidationError(f"Process at index {i} must be a JSON object.")

        # ── PID ──────────────────────────────────────────────────────────────
        pid = str(p.get("pid", f"P{i + 1}")).strip()
        if not pid:
            pid = f"P{i + 1}"                     # fill blank with a default
        if len(pid) > 16:
            raise ValidationError(f"PID '{pid}' is too long (max 16 characters).")
        if pid in seen_pids:
            raise ValidationError(f"Duplicate PID '{pid}' at index {i}.")
        seen_pids.add(pid)

        # ── Arrival time ─────────────────────────────────────────────────────
        try:
            arrival = int(p.get("arrival", 0))
        except (TypeError, ValueError):
            raise ValidationError(f"Process '{pid}': arrival time must be an integer.")
        if not (PC["arrival_min"] <= arrival <= PC["arrival_max"]):
            raise ValidationError(
                f"Process '{pid}': arrival {arrival} out of range "
                f"[{PC['arrival_min']}, {PC['arrival_max']}]."
            )

        # ── Burst time ───────────────────────────────────────────────────────
        # Burst ≥ 1 is enforced because a burst of 0 would produce a zero-
        # division in normalised-TAT = TAT / BT (used in fairness calculations).
        try:
            burst = int(p.get("burst", 1))
        except (TypeError, ValueError):
            raise ValidationError(f"Process '{pid}': burst time must be an integer.")
        if not (PC["burst_min"] <= burst <= PC["burst_max"]):
            raise ValidationError(
                f"Process '{pid}': burst {burst} out of range "
                f"[{PC['burst_min']}, {PC['burst_max']}]."
            )

        # ── Priority ─────────────────────────────────────────────────────────
        # Convention follows Silberschatz §6.3.3: lower integer = higher urgency.
        # Priority 1 is the most urgent; Priority 100 is the least urgent.
        try:
            priority = int(p.get("priority", i + 1))
        except (TypeError, ValueError):
            raise ValidationError(f"Process '{pid}': priority must be an integer.")
        if not (PC["priority_min"] <= priority <= PC["priority_max"]):
            raise ValidationError(
                f"Process '{pid}': priority {priority} out of range "
                f"[{PC['priority_min']}, {PC['priority_max']}]."
            )

        cleaned.append({
            "pid":      pid,
            "arrival":  arrival,
            "burst":    burst,
            "priority": priority,
        })

    return cleaned


# ---------------------------------------------------------------------------
# Algorithm ID validation
# ---------------------------------------------------------------------------

def validate_sched_algorithms(algorithms: Any) -> list[str]:
    """
    Validate a list of scheduling algorithm IDs.

    Accepted IDs: fcfs | sjf | srtf | round_robin | priority
    Returns the validated list or raises ValidationError.
    """
    if not isinstance(algorithms, list) or not algorithms:
        raise ValidationError("Select at least one scheduling algorithm.")
    invalid = [a for a in algorithms if a not in VALID_SCHED_ALGORITHMS]
    if invalid:
        raise ValidationError(
            f"Unknown scheduling algorithm(s): {', '.join(invalid)}. "
            f"Valid: {', '.join(sorted(VALID_SCHED_ALGORITHMS))}."
        )
    return algorithms


def validate_sync_algorithms(algorithms: Any) -> list[str]:
    """
    Validate a list of synchronization algorithm IDs.

    Accepted IDs: peterson | dekker | mutex | binary_semaphore |
                  counting_semaphore | monitor | race_condition |
                  deadlock_demo | livelock_demo | starvation_demo |
                  busy_wait_demo
    """
    if not isinstance(algorithms, list) or not algorithms:
        raise ValidationError("Select at least one synchronization algorithm.")
    invalid = [a for a in algorithms if a not in VALID_SYNC_ALGORITHMS]
    if invalid:
        raise ValidationError(
            f"Unknown synchronization algorithm(s): {', '.join(invalid)}. "
            f"Valid: {', '.join(sorted(VALID_SYNC_ALGORITHMS))}."
        )
    return algorithms


# ---------------------------------------------------------------------------
# Scalar parameter validation
# ---------------------------------------------------------------------------

def validate_quantum(quantum: Any) -> int:
    """
    Validate the Round Robin time quantum.

    The quantum is the maximum number of CPU ticks a process may run before
    being preempted and returned to the tail of the ready queue
    (Silberschatz §6.3.4).  A quantum of 1 gives maximum preemption (pure
    round-robin); a very large quantum degenerates to FCFS.
    """
    try:
        q = int(quantum)
    except (TypeError, ValueError):
        raise ValidationError("Quantum must be an integer.")
    if not (1 <= q <= 100):
        raise ValidationError(f"Quantum {q} out of range [1, 100].")
    return q


def validate_sync_config(config: Any) -> dict:
    """
    Validate and sanitise the synchronisation configuration dictionary.

    Optional keys and their allowed ranges:
        processes   [1–20]   — how many generic processes the sync demo uses
        iterations  [1–20]   — how many CS-entry cycles each demo runs
        slots       [1–20]   — counting semaphore initial slot count
        increments  [1–50]   — increments per process (race condition demo)
        corrected   bool     — True = show mutex-protected (safe) mode
    """
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValidationError("'sync_config' must be a JSON object.")

    cleaned: dict = {}

    # Integer fields: validate each against its specific range.
    for key, (lo, hi) in {
        "processes":  (1,  20),
        "iterations": (1,  20),
        "slots":      (1,  20),
        "increments": (1,  50),
    }.items():
        if key in config:
            try:
                val = int(config[key])
            except (TypeError, ValueError):
                raise ValidationError(f"sync_config.{key} must be an integer.")
            if not (lo <= val <= hi):
                raise ValidationError(
                    f"sync_config.{key} = {val} out of range [{lo}, {hi}]."
                )
            cleaned[key] = val

    # Boolean flag: coerce to Python bool rather than trusting JSON type.
    if "corrected" in config:
        cleaned["corrected"] = bool(config["corrected"])

    return cleaned
