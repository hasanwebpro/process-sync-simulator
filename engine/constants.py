"""Shared constants — avoids circular imports between engine modules."""

from __future__ import annotations

SYNC_ALGORITHM_NAMES: list[dict[str, str]] = [
    {"id": "peterson", "name": "Peterson's Solution"},
    {"id": "dekker", "name": "Dekker's Algorithm"},
    {"id": "mutex", "name": "Mutex Lock"},
    {"id": "binary_semaphore", "name": "Binary Semaphore"},
    {"id": "counting_semaphore", "name": "Counting Semaphore"},
    {"id": "producer_consumer", "name": "Producer–Consumer"},
    {"id": "readers_writers", "name": "Readers–Writers"},
    {"id": "monitor", "name": "Monitor"},
    {"id": "race_condition", "name": "Race Condition"},
    {"id": "deadlock_demo", "name": "Deadlock Demo"},
]

VALID_SCHED_ALGORITHMS = frozenset({"fcfs", "sjf", "srtf", "round_robin", "priority"})
VALID_SYNC_ALGORITHMS = frozenset(
    {m["id"] for m in SYNC_ALGORITHM_NAMES}
)

PROCESS_CONSTRAINTS = {
    "burst_min": 1,
    "burst_max": 100,
    "arrival_min": 0,
    "arrival_max": 1000,
    "priority_min": 1,
    "priority_max": 100,
    "max_processes": 20,
    "min_processes": 1,
}
