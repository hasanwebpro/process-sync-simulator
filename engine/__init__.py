"""
engine — Process Synchronization Simulator core package
========================================================

Module structure
----------------
constants        — shared enumerations and constraint tables
validators       — input sanitisation before any simulation runs
scheduler        — CPU scheduling algorithms (FCFS, SJF, SRTF, RR, Priority)
sync_engine      — synchronization algorithm simulations (mutex, semaphore,
                   monitor, Peterson, Dekker, producer-consumer, etc.)
diagnostics      — Phase 2: detect synchronization problems from a CPU trace
analyzer         — Phase 3/4: score techniques and generate recommendations
execution_engine — pipeline that wires Phase 1 (scheduling) to Phase 2/3 (sync)

Design principle
----------------
Scheduling and synchronization are intentionally separated:

    Phase 1  →  CPU scheduler produces an execution trace (Gantt chart).
    Phase 2  →  That trace is replayed without locks to expose race conditions,
                deadlock, and starvation (Silberschatz §6.1).
    Phase 3  →  The same trace is replayed with each synchronization primitive
                to show how mutual exclusion resolves those problems.
    Phase 4  →  Analysis engine compares techniques and recommends the best one.

The scheduler is the *independent variable*; the synchronization problems are
the *dependent variable*.  Changing the scheduler changes the interleaving, which
changes which problems surface — this is the core pedagogical claim.
"""

from .sync_engine      import SyncSimulator
from .scheduler        import CPUScheduler
from .analyzer         import AnalysisEngine
from .execution_engine import ExecutionEngine
from .diagnostics      import DiagnosticsEngine, list_techniques, list_problems
from .constants        import (
    SYNC_ALGORITHM_NAMES,
    VALID_SCHED_ALGORITHMS,
    VALID_SYNC_ALGORITHMS,
)
from .validators import (
    ValidationError,
    validate_processes,
    validate_quantum,
    validate_sched_algorithms,
    validate_sync_algorithms,
    validate_sync_config,
)

__all__ = [
    "SyncSimulator",
    "CPUScheduler",
    "AnalysisEngine",
    "ExecutionEngine",
    "DiagnosticsEngine",
    "list_techniques",
    "list_problems",
    "SYNC_ALGORITHM_NAMES",
    "VALID_SCHED_ALGORITHMS",
    "VALID_SYNC_ALGORITHMS",
    "ValidationError",
    "validate_processes",
    "validate_quantum",
    "validate_sched_algorithms",
    "validate_sync_algorithms",
    "validate_sync_config",
]
