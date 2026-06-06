"""
constants.py — Shared enumerations and constraint tables
=========================================================

Centralising these values avoids circular imports between modules and gives a
single place to update limits without touching simulation logic.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Synchronization algorithm registry
# ---------------------------------------------------------------------------
# Each entry maps a string ID (used in API calls and URL parameters) to a
# human-readable name.  The ID is what the SyncSimulator dispatcher uses;
# the name is what the UI shows to students.
#
# Algorithms are grouped by type:
#   - Software-only ME solutions  : peterson, dekker
#   - Hardware-assisted primitives: mutex, binary_semaphore, counting_semaphore
#   - Structured high-level       : monitor
#   - Classic OS problems         : producer_consumer, readers_writers
#   - Demonstration scenarios     : race_condition, deadlock_demo
SYNC_ALGORITHM_NAMES: list[dict[str, str]] = [
    {"id": "peterson",           "name": "Peterson's Solution"},
    {"id": "dekker",             "name": "Dekker's Algorithm"},
    {"id": "mutex",              "name": "Mutex Lock"},
    {"id": "binary_semaphore",   "name": "Binary Semaphore"},
    {"id": "counting_semaphore", "name": "Counting Semaphore"},
    {"id": "producer_consumer",  "name": "Producer–Consumer"},
    {"id": "readers_writers",    "name": "Readers–Writers"},
    {"id": "monitor",            "name": "Monitor"},
    {"id": "race_condition",     "name": "Race Condition"},
    {"id": "deadlock_demo",      "name": "Deadlock Demo"},
]

# ---------------------------------------------------------------------------
# Valid algorithm ID sets (used by validators for fast O(1) membership tests)
# ---------------------------------------------------------------------------
VALID_SCHED_ALGORITHMS: frozenset[str] = frozenset({
    "fcfs",          # First Come First Serve  — non-preemptive
    "sjf",           # Shortest Job First      — non-preemptive
    "srtf",          # Shortest Remaining Time — preemptive SJF
    "round_robin",   # Round Robin             — preemptive, time-quantum based
    "priority",      # Priority Scheduling     — non-preemptive, lower number = higher priority
})

VALID_SYNC_ALGORITHMS: frozenset[str] = frozenset(
    m["id"] for m in SYNC_ALGORITHM_NAMES
)

# ---------------------------------------------------------------------------
# Process parameter constraints
# ---------------------------------------------------------------------------
# These limits prevent nonsensical input (e.g. burst=0 would divide-by-zero in
# normalised-TAT calculations) and keep the visualisation readable on screen.
PROCESS_CONSTRAINTS: dict[str, int] = {
    "burst_min":     1,     # A process must execute for at least 1 tick
    "burst_max":     100,   # Cap prevents Gantt charts from being unreadably wide
    "arrival_min":   0,     # Processes may arrive at simulation start (t=0)
    "arrival_max":   1000,  # Upper bound keeps total simulation time manageable
    "priority_min":  1,     # Convention: lower number = higher urgency (Silberschatz §6.3.3)
    "priority_max":  100,
    "max_processes": 20,    # Beyond ~8 the Gantt chart and state table become cluttered
    "min_processes": 1,
}
