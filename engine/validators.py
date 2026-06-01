"""Input validation helpers for the simulation engine."""

from __future__ import annotations

from typing import Any

from .constants import (
    PROCESS_CONSTRAINTS as PC,
    VALID_SCHED_ALGORITHMS,
    VALID_SYNC_ALGORITHMS,
)


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""


def validate_processes(processes: Any) -> list[dict]:
    """
    Validate and normalise a list of process dicts.

    Returns a clean list or raises ValidationError with a descriptive message.
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
    cleaned: list[dict] = []

    for i, p in enumerate(processes):
        if not isinstance(p, dict):
            raise ValidationError(f"Process at index {i} must be an object.")

        # --- PID ---
        pid = str(p.get("pid", f"P{i + 1}")).strip()
        if not pid:
            pid = f"P{i + 1}"
        if len(pid) > 16:
            raise ValidationError(
                f"PID '{pid}' is too long (max 16 characters)."
            )
        if pid in seen_pids:
            raise ValidationError(f"Duplicate PID '{pid}' at index {i}.")
        seen_pids.add(pid)

        # --- Arrival ---
        try:
            arrival = int(p.get("arrival", 0))
        except (TypeError, ValueError):
            raise ValidationError(
                f"Process '{pid}': arrival time must be an integer."
            )
        if not (PC["arrival_min"] <= arrival <= PC["arrival_max"]):
            raise ValidationError(
                f"Process '{pid}': arrival time {arrival} out of range "
                f"[{PC['arrival_min']}, {PC['arrival_max']}]."
            )

        # --- Burst ---
        try:
            burst = int(p.get("burst", 1))
        except (TypeError, ValueError):
            raise ValidationError(
                f"Process '{pid}': burst time must be an integer."
            )
        if not (PC["burst_min"] <= burst <= PC["burst_max"]):
            raise ValidationError(
                f"Process '{pid}': burst time {burst} out of range "
                f"[{PC['burst_min']}, {PC['burst_max']}]."
            )

        # --- Priority ---
        try:
            priority = int(p.get("priority", i + 1))
        except (TypeError, ValueError):
            raise ValidationError(
                f"Process '{pid}': priority must be an integer."
            )
        if not (PC["priority_min"] <= priority <= PC["priority_max"]):
            raise ValidationError(
                f"Process '{pid}': priority {priority} out of range "
                f"[{PC['priority_min']}, {PC['priority_max']}]."
            )

        cleaned.append(
            {"pid": pid, "arrival": arrival, "burst": burst, "priority": priority}
        )

    return cleaned


def validate_sched_algorithms(algorithms: Any) -> list[str]:
    """Validate a list of scheduling algorithm IDs."""
    if not isinstance(algorithms, list) or not algorithms:
        raise ValidationError("Select at least one scheduling algorithm.")
    invalid = [a for a in algorithms if a not in VALID_SCHED_ALGORITHMS]
    if invalid:
        raise ValidationError(
            f"Unknown scheduling algorithm(s): {', '.join(invalid)}. "
            f"Valid options: {', '.join(sorted(VALID_SCHED_ALGORITHMS))}."
        )
    return algorithms


def validate_sync_algorithms(algorithms: Any) -> list[str]:
    """Validate a list of synchronization algorithm IDs."""
    if not isinstance(algorithms, list) or not algorithms:
        raise ValidationError("Select at least one synchronization algorithm.")
    invalid = [a for a in algorithms if a not in VALID_SYNC_ALGORITHMS]
    if invalid:
        raise ValidationError(
            f"Unknown synchronization algorithm(s): {', '.join(invalid)}. "
            f"Valid options: {', '.join(sorted(VALID_SYNC_ALGORITHMS))}."
        )
    return algorithms


def validate_quantum(quantum: Any) -> int:
    """Validate the Round Robin time quantum."""
    try:
        q = int(quantum)
    except (TypeError, ValueError):
        raise ValidationError("Quantum must be an integer.")
    if not (1 <= q <= 100):
        raise ValidationError(f"Quantum {q} out of range [1, 100].")
    return q


def validate_sync_config(config: Any) -> dict:
    """Validate and sanitise the sync configuration dict."""
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValidationError("'sync_config' must be a JSON object.")

    cleaned: dict = {}

    for key, (lo, hi) in {
        "processes": (1, 20),
        "iterations": (1, 20),
        "buffer_size": (2, 50),
        "items": (1, 200),
        "slots": (1, 20),
        "readers": (1, 10),
        "writers": (1, 10),
        "operations": (1, 20),
        "increments": (1, 50),
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

    if "corrected" in config:
        cleaned["corrected"] = bool(config["corrected"])

    return cleaned
