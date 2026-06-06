"""
sync_engine.py — Process Synchronization Algorithm Simulations
===============================================================

Implements ten synchronization scenarios as discrete, step-by-step
simulations.  Each simulation produces a list of "steps" — snapshots of
the system state at every meaningful event — which the frontend plays back
as an animated walkthrough.

Algorithms
----------
Software-only mutual exclusion (no hardware atomics):
    peterson          — Peterson's two-process ME solution (Silberschatz §6.3.1)
    dekker            — Dekker's algorithm, the first software ME solution (Tanenbaum §2.3.3)

Hardware-assisted primitives:
    mutex             — acquire()/release() with FIFO wait queue (Silberschatz §6.5)
    binary_semaphore  — P()/V() on a 0/1 counter (Silberschatz §6.6)
    counting_semaphore— P()/V() on an N counter, models resource pools (Silberschatz §6.6)

Classic OS problems (solved with semaphores/monitors):
    producer_consumer — bounded buffer with mutex + empty/full semaphores (Silberschatz §6.4)
    readers_writers   — first readers-writers problem, readers-preference (Silberschatz §7.1.2)
    monitor           — monitor with condition variables, signal-and-continue (Silberschatz §6.7)

Demonstration scenarios (show what happens WITHOUT synchronization):
    race_condition    — unsafe read-modify-write interleaving vs mutex-protected (Silberschatz §6.1)
    deadlock_demo     — classic circular wait on two resources (Silberschatz §8.3.1)

Step format
-----------
Each step is a dict:
    tick             — logical step counter
    processes        — {pid: state} map (READY | RUNNING | WAITING | BLOCKED | TERMINATED)
    action           — short action label (enter_cs, blocked, V_signal, …)
    message          — human-readable explanation for the student
    critical_section — list of PIDs currently inside the CS
    waiting_queue    — list of PIDs waiting for the lock/semaphore
    resources        — lock/semaphore state values
    shared_vars      — shared variable values (counter, buffer, flag arrays, etc.)

All mutable objects in a step are deep-copied so that later mutations
to live data structures do not retroactively change recorded step state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


# Valid process state labels (Silberschatz §3.2 process state diagram)
STATES = ("READY", "RUNNING", "WAITING", "BLOCKED", "TERMINATED")


class SyncSimulator:
    """
    Produces step-by-step synchronization simulations for educational playback.

    Each algorithm returns (steps, summary):
        steps   — ordered list of state snapshots (see module docstring)
        summary — final outcome metrics (counters, flags, detected problems)
    """

    def __init__(self) -> None:
        # Dispatch table: algorithm ID → implementation method
        self._algorithms = {
            "peterson":           self._peterson,
            "dekker":             self._dekker,
            "mutex":              self._mutex,
            "binary_semaphore":   self._binary_semaphore,
            "counting_semaphore": self._counting_semaphore,
            "producer_consumer":  self._producer_consumer,
            "readers_writers":    self._readers_writers,
            "monitor":            self._monitor,
            "race_condition":     self._race_condition,
            "deadlock_demo":      self._deadlock_demo,
        }

    def list_algorithms(self) -> list[dict[str, str]]:
        """Return metadata for all algorithms (populates the Phase 3 UI dropdown)."""
        meta = {
            "peterson":           ("Peterson's Solution",    "Two-process mutual exclusion without hardware locks."),
            "dekker":             ("Dekker's Algorithm",     "First software ME solution; turn-based fairness."),
            "mutex":              ("Mutex Lock",             "Strict mutual exclusion via acquire/release."),
            "binary_semaphore":   ("Binary Semaphore",       "P()/V() operations on a 0/1 counter."),
            "counting_semaphore": ("Counting Semaphore",     "P()/V() on an N counter; models resource pools."),
            "producer_consumer":  ("Producer–Consumer",      "Bounded buffer with mutex + empty/full semaphores."),
            "readers_writers":    ("Readers–Writers",        "Shared read, exclusive write (readers-preference)."),
            "monitor":            ("Monitor",                "Condition variables with signal-and-continue semantics."),
            "race_condition":     ("Race Condition",         "Unsafe shared counter vs mutex-protected (demo)."),
            "deadlock_demo":      ("Deadlock Demo",          "Circular wait on two resources (demo)."),
        }
        return [{"id": k, "name": v[0], "description": v[1]} for k, v in meta.items()]

    def run(self, algorithm: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute a synchronization simulation and return all steps.

        Parameters
        ----------
        algorithm — one of the IDs from list_algorithms()
        config    — optional parameter dict (iterations, buffer_size, slots, …)

        Returns
        -------
        dict with: algorithm, config, steps (list), summary (dict), total_ticks
        """
        config = config or {}
        if algorithm not in self._algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        steps, summary = self._algorithms[algorithm](config)
        return {
            "algorithm":   algorithm,
            "config":      config,
            "steps":       steps,
            "summary":     summary,
            "total_ticks": len(steps),
        }

    def _step(
        self,
        tick: int,
        processes: dict[str, str],
        action: str,
        message: str,
        *,
        critical_section: list[str] | None = None,
        waiting_queue:    list[str] | None = None,
        resources:        dict[str, Any] | None = None,
        shared_vars:      dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a single simulation step snapshot.

        Why deep-copy?
        Callers hold live references to lists/dicts (flag arrays, buffer, etc.)
        and continue mutating them after this step is recorded.  Without
        deep-copying, every recorded step would alias the same live object and
        show its *final* state rather than its state at the moment it was recorded.
        This is a correctness requirement, not just a style choice.
        """
        return {
            "tick":             tick,
            "processes":        deepcopy(processes),
            "action":           action,
            "message":          message,
            "critical_section": list(critical_section) if critical_section else [],
            "waiting_queue":    list(waiting_queue)    if waiting_queue    else [],
            "resources":        deepcopy(resources)    if resources        else {},
            "shared_vars":      deepcopy(shared_vars)  if shared_vars      else {},
        }

    def _peterson(self, config: dict) -> tuple[list, dict]:
        """
        Peterson's Solution — software-only mutual exclusion for exactly 2 processes.

        Reference: Silberschatz §6.3.1 / Peterson 1981.

        Shared variables
        ----------------
        flag[i]  — True when process i wants to enter the critical section.
        turn     — the process that must defer when both want CS simultaneously.

        Protocol for process Pi (i=0 or 1, j = 1-i)
        ---------------------------------------------
        Entry:   flag[i] = True          # "I want to enter"
                 turn = j                # "but I'll let you go first"
                 while flag[j] and turn == j:
                     busy-wait           # yield CPU until the other leaves
        CS body: ...access shared resource...
        Exit:    flag[i] = False         # "I'm done, you may proceed"
                 (no turn assignment on exit — turn is only set in entry)

        Three correctness properties (Silberschatz §6.2):
        1. Mutual exclusion — only one process in CS at a time.
        2. Progress          — if no process is in CS and one wants to enter,
                               it will enter in finite time.
        3. Bounded waiting   — each process waits at most 1 full turn.

        Limitation: two-process only.  The flag/turn mechanism does not
        generalise to n processes without Lamport's Bakery algorithm.

        Simulation note:
        Both processes set their flags simultaneously to show the contention
        scenario.  P0 sets turn=1 (defer to P1), then P1 sets turn=0 (defer to
        P0) — the last write wins (turn=0), so P0 enters CS first.
        """
        iterations = int(config.get("iterations", 3))
        steps: list[dict] = []
        tick = 0
        flag = [False, False]
        turn = 0
        counter = 0
        procs = {"P0": "READY", "P1": "READY"}

        def emit(action: str, msg: str, cs: list[str], wq: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=wq,
                    shared_vars={"flag": flag[:], "turn": turn, "counter": counter},
                )
            )
            tick += 1

        emit("init", "Peterson: flag=[False,False], turn=0. Both processes will compete for CS.", [], [])

        for iteration in range(iterations):
            # Both processes signal intent simultaneously (shows contention)
            flag[0] = True
            flag[1] = True
            procs["P0"] = "RUNNING"
            procs["P1"] = "RUNNING"
            emit("request_cs", f"Iteration {iteration+1}: P0 and P1 both set flag=True (both want CS)", [], ["P0", "P1"])

            # P0 sets turn=1 (defers to P1), P1 sets turn=0 (defers to P0)
            # Last write wins — turn ends up as 0 (P1 wrote last, giving turn to P0)
            turn = 1   # P0 sets turn=1
            emit("set_turn", "P0: turn=1 (I defer to P1)", [], ["P0", "P1"])
            turn = 0   # P1 sets turn=0 (last write wins)
            emit("set_turn", "P1: turn=0 (I defer to P0) — last write wins, turn=0", [], ["P0", "P1"])

            # P1 must wait: flag[0]==True AND turn==0
            procs["P1"] = "WAITING"
            emit("wait", "P1 waits: flag[0]=True AND turn==0 → busy-wait", [], ["P1"])

            # P0 can enter: flag[1]==True but turn==0 (not 0's turn to defer)
            procs["P0"] = "RUNNING"
            emit("enter_cs", "P0 enters CS: flag[1]=True but turn=0 ≠ 1, so P0 proceeds", ["P0"], ["P1"])
            counter += 1
            emit("critical_section", f"P0 in CS — counter={counter}", ["P0"], ["P1"])

            # P0 exits CS
            flag[0] = False
            procs["P0"] = "READY"
            emit("exit_cs", "P0: flag[0]=False — releases CS", [], ["P1"])

            # P1 can now enter: flag[0]==False, busy-wait condition false
            procs["P1"] = "RUNNING"
            emit("enter_cs", "P1 enters CS: flag[0]=False → busy-wait exits", ["P1"], [])
            counter += 1
            emit("critical_section", f"P1 in CS — counter={counter}", ["P1"], [])

            # P1 exits CS — Peterson exit: only clear own flag (Silberschatz §6.3.1)
            # No turn assignment in exit section; turn is set only in entry protocol.
            flag[1] = False
            procs["P1"] = "READY"
            emit("exit_cs", "P1: flag[1]=False — releases CS (Peterson exit: flag only)", [], [])

        procs = {k: "TERMINATED" for k in procs}
        emit("done", f"Peterson complete. counter={counter} (expected {iterations*2}). Mutual exclusion maintained.", [], [])
        return steps, {"final_counter": counter, "mutual_exclusion": True, "deadlock_free": True}

    def _dekker(self, config: dict) -> tuple[list, dict]:
        """
        Dekker's Algorithm — the first published software solution for ME.

        Reference: Dijkstra 1965 (credited to Dekker); Tanenbaum §2.3.3.

        Shared variables
        ----------------
        flag[i]  — True when process i wants to enter the CS.
        turn     — whose turn it is to enter when BOTH want CS simultaneously.

        Protocol for process Pi (i=0 or 1, j = 1-i)
        ---------------------------------------------
        Entry:   flag[i] = True
                 while flag[j]:              # contention check
                     if turn != i:           # NOT my turn
                         flag[i] = False     # temporarily withdraw
                         while turn != i:    # busy-wait for turn
                             pass
                         flag[i] = True      # retry
        CS body: ...
        Exit:    flag[i] = False
                 turn = j                    # hand turn to the other process

        How it differs from Peterson:
        - Dekker uses a DEFERRAL pattern: the non-favoured process WITHDRAWS
          its flag, waits for turn, then RETRIES the outer while.
        - Peterson uses a simpler COURTESY pattern: set turn=other, then
          wait while the other both wants CS AND has the turn.
        - Both provide mutual exclusion, progress, and bounded waiting for n=2.

        Simulation note:
        The turn alternates each iteration so both the deferral path (one process
        waiting) and the fast path (turn matches, enter directly) are shown.
        """
        iterations = int(config.get("iterations", 3))
        steps: list[dict] = []
        tick = 0
        flag = [False, False]
        turn = 0          # whose turn it is to enter CS when both want it
        counter = 0
        procs = {"P0": "READY", "P1": "READY"}

        def emit(action: str, msg: str, cs: list[str], wq: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=wq,
                    shared_vars={"flag": flag[:], "turn": turn, "counter": counter},
                )
            )
            tick += 1

        emit("init", "Dekker: flag=[False,False], turn=0. Both processes will compete simultaneously each iteration.", [], [])

        for iteration in range(iterations):
            # --- Step 1: both signal intent simultaneously (shows contention) ---
            flag[0] = True
            flag[1] = True
            procs["P0"] = "RUNNING"
            procs["P1"] = "RUNNING"
            emit(
                "flag_on",
                f"Iteration {iteration+1}: P0 sets flag[0]=True, P1 sets flag[1]=True — both want CS simultaneously.",
                [], [],
            )

            # --- Step 2: both check the other's flag — both see True → contention ---
            emit(
                "contend",
                f"P0 checks flag[1]=True; P1 checks flag[0]=True — contention detected. "
                f"turn={turn}: P{turn} may enter, P{1-turn} must defer.",
                [], [],
            )

            # The process whose turn it is NOT defers (clears flag, busy-waits)
            defer_pid = 1 - turn        # this process must defer
            enter_pid = turn            # this process may enter immediately

            # --- Step 3: deferring process clears its flag and busy-waits ---
            flag[defer_pid] = False
            procs[f"P{defer_pid}"] = "WAITING"
            emit(
                "defer",
                f"P{defer_pid}: turn={turn} ≠ {defer_pid} → NOT my turn. "
                f"P{defer_pid} clears flag[{defer_pid}]=False and enters busy-wait.",
                [], [f"P{defer_pid}"],
            )
            emit(
                "busy_wait",
                f"P{defer_pid}: busy-waiting for turn=={defer_pid} (currently turn={turn}). "
                f"CPU cycles consumed while waiting.",
                [], [f"P{defer_pid}"],
            )

            # --- Step 4: favoured process sees flag[other]=False → enters CS ---
            procs[f"P{enter_pid}"] = "RUNNING"
            emit(
                "enter_cs",
                f"P{enter_pid}: flag[{defer_pid}]=False (deferred) AND turn={turn}=={enter_pid} → enters CS.",
                [f"P{enter_pid}"], [f"P{defer_pid}"],
            )
            counter += 1
            emit(
                "critical_section",
                f"P{enter_pid} in CS — counter={counter}. P{defer_pid} still busy-waiting.",
                [f"P{enter_pid}"], [f"P{defer_pid}"],
            )

            # --- Step 5: favoured process exits CS, clears flag, passes turn ---
            flag[enter_pid] = False
            turn = defer_pid            # give turn to the process that deferred
            procs[f"P{enter_pid}"] = "READY"
            emit(
                "exit_cs",
                f"P{enter_pid} exits CS: flag[{enter_pid}]=False, turn={turn} "
                f"(turn given to P{turn} that was waiting).",
                [], [f"P{defer_pid}"],
            )

            # --- Step 6: deferred process sees turn changed → retries ---
            emit(
                "retry",
                f"P{defer_pid}: turn=={defer_pid} now! Retries: sets flag[{defer_pid}]=True.",
                [], [f"P{defer_pid}"],
            )
            flag[defer_pid] = True
            procs[f"P{defer_pid}"] = "RUNNING"

            # flag[enter_pid] is now False → deferred process can enter
            emit(
                "enter_cs",
                f"P{defer_pid}: checks flag[{enter_pid}]=False → busy-wait exits. Enters CS.",
                [f"P{defer_pid}"], [],
            )
            counter += 1
            emit(
                "critical_section",
                f"P{defer_pid} in CS — counter={counter}.",
                [f"P{defer_pid}"], [],
            )

            # --- Step 7: deferred process exits, passes turn back ---
            flag[defer_pid] = False
            turn = enter_pid
            procs[f"P{defer_pid}"] = "READY"
            emit(
                "exit_cs",
                f"P{defer_pid} exits CS: flag[{defer_pid}]=False, turn={turn}.",
                [], [],
            )

        procs = {k: "TERMINATED" for k in procs}
        emit(
            "done",
            f"Dekker complete. counter={counter} (expected {iterations*2}). "
            f"Deferral exercised every iteration — mutual exclusion maintained.",
            [], [],
        )
        return steps, {"final_counter": counter, "mutual_exclusion": True}

    def _mutex(self, config: dict) -> tuple[list, dict]:
        """
        Mutex Lock — hardware-assisted mutual exclusion.

        Reference: Silberschatz §6.5.

        A mutex (mutual exclusion object) is a binary lock with ownership semantics.
        Only one process may hold it at a time; all others block in a FIFO queue.

        acquire() — also called lock() or wait():
            if lock is free  → set lock=True, enter CS
            if lock is held  → block (add to wait queue)

        release() — also called unlock() or signal():
            if wait queue non-empty → wake next waiter (hand-off)
            else                    → set lock=False

        Key properties:
        - Mutual exclusion: exactly one process in CS at any time.
        - No busy-waiting: blocked processes sleep, freeing the CPU.
        - Ownership: the process that acquired must release (prevents misuse).
        - Does NOT prevent deadlock: two mutexes acquired in opposite order
          (ABBA pattern) still deadlock (Silberschatz §8.3).

        Comparison with semaphore:
        - Mutex has OWNERSHIP (only acquirer can release).
        - Binary semaphore has no ownership: any process can call V().
        """
        n = int(config.get("processes", 3))
        iterations = int(config.get("iterations", 2))
        steps: list[dict] = []
        tick = 0
        lock = False
        counter = 0
        procs = {f"P{i}": "READY" for i in range(n)}
        queue: list[str] = []

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=list(queue),
                    resources={"mutex_locked": lock},
                    shared_vars={"counter": counter},
                )
            )
            tick += 1

        emit("init", "Mutex lock available (unlocked)", [])

        for _ in range(iterations):
            for pid in sorted(procs.keys()):
                procs[pid] = "RUNNING"
                emit("request_lock", f"{pid} calls acquire(mutex)", [])

                if lock:
                    # Mutex is held — block this process
                    procs[pid] = "BLOCKED"
                    queue.append(pid)
                    emit("blocked", f"{pid} blocked — mutex held by another process", [])
                    # In sequential sim: previous holder already released, so unblock now
                    queue.remove(pid)
                    procs[pid] = "RUNNING"
                    emit("unblocked", f"{pid} unblocked — mutex now available", [])

                # Acquire the mutex
                lock = True
                emit("acquire", f"{pid} acquired mutex — lock=True", [pid])

                # Critical section
                counter += 1
                emit("critical_section", f"{pid} in CS — counter={counter}", [pid])

                # Release the mutex
                lock = False
                procs[pid] = "READY"
                if queue:
                    emit("release", f"{pid} released mutex — waking {queue[0]}", [])
                else:
                    emit("release", f"{pid} released mutex — lock=False", [])

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", f"Mutex simulation done. counter={counter}", [])
        return steps, {"final_counter": counter, "mutual_exclusion": True}

    def _binary_semaphore(self, config: dict) -> tuple[list, dict]:
        """
        Binary Semaphore — P()/V() with a 0/1 counter.

        Reference: Silberschatz §6.6 / Dijkstra 1968.

        A binary semaphore is equivalent in power to a mutex but WITHOUT
        ownership semantics: any process may call V(), not just the one
        that called P().  This makes it suitable for SIGNALLING patterns
        (e.g. one process signals another to proceed) as well as ME.

        P(s) — also called wait() or down():
            if s > 0  → s = s − 1, proceed
            else      → block (join wait queue)

        V(s) — also called signal() or up():
            if wait queue non-empty → wake one blocked process
            else                    → s = s + 1

        Binary semaphore (initial=1): one slot → mutual exclusion.
        Counting semaphore (initial=N): N slots → resource pool.
        """
        return self._semaphore_impl(config, initial=1, name="Binary Semaphore")

    def _counting_semaphore(self, config: dict) -> tuple[list, dict]:
        """
        Counting Semaphore — P()/V() with an initial value of N.

        Reference: Silberschatz §6.6.

        Models a pool of N identical resources.  Up to N processes may hold
        the resource simultaneously (sem > 0).  When sem reaches 0, further
        P() calls block until a holder calls V().

        Use cases: database connection pools, I/O device slots, thread pools.
        The counting semaphore is the correct primitive for the
        Producer-Consumer empty/full tracking semaphores.
        """
        slots = int(config.get("slots", 2))
        return self._semaphore_impl(config, initial=slots, name="Counting Semaphore")

    def _semaphore_impl(self, config: dict, initial: int, name: str) -> tuple[list, dict]:
        """Delegate to the shared contention-model implementation."""
        return self._semaphore_contention_impl(config, initial, name)

    def _semaphore_contention_impl(self, config: dict, initial: int, name: str) -> tuple[list, dict]:
        """
        Shared P()/V() simulation — blocked processes wake only after V().

        Contention scenario: all processes call P() simultaneously.
        Processes that find sem=0 are BLOCKED and join the wait queue.
        When a holder calls V(), it either transfers its slot to the first
        waiter (sem stays the same) or increments sem if no one is waiting.

        This faithfully models the two-phase semantics:
            Phase 1: all processes try P() → some block
            Phase 2: holders enter CS, then V() unblocks waiters in FIFO order
        """
        n = int(config.get("processes", 4))
        iterations = int(config.get("iterations", 2))
        steps: list[dict] = []
        tick = 0
        sem = initial
        counter = 0
        procs = {f"P{i}": "READY" for i in range(n)}
        queue: list[str] = []

        def emit(action: str, msg: str, cs: list[str], holders: list[str] | None = None) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick,
                    procs,
                    action,
                    msg,
                    critical_section=cs,
                    waiting_queue=list(queue),
                    resources={"semaphore": sem, "holders": list(holders or [])},
                    shared_vars={"counter": counter},
                )
            )
            tick += 1

        emit("init", f"{name}: sem={sem} (initial slots={initial})", [])
        pids = sorted(procs.keys())

        for iteration in range(iterations):
            holders: list[str] = []
            emit("round_start", f"Iteration {iteration + 1}: processes contend for {name}", [], holders)

            for pid in pids:
                procs[pid] = "RUNNING"
                emit("P_wait", f"{pid}: P() - sem={sem}", [], holders)

                if sem == 0:
                    procs[pid] = "BLOCKED"
                    queue.append(pid)
                    emit("block", f"{pid} blocked - semaphore=0, joins wait queue", [], holders)
                    continue

                sem -= 1
                holders.append(pid)
                procs[pid] = "READY"
                emit("acquire", f"{pid} acquired resource - sem->{sem}", [], holders)

            while holders:
                pid = holders.pop(0)
                procs[pid] = "RUNNING"
                emit("enter_cs", f"{pid} enters critical section/resource use", [pid], holders + [pid])
                counter += 1
                emit("critical_section", f"{pid} in CS/resource use - counter={counter}", [pid], holders + [pid])

                if queue:
                    next_p = queue.pop(0)
                    procs[pid] = "READY"
                    procs[next_p] = "READY"
                    emit(
                        "V_signal",
                        f"{pid}: V() - transfers released slot to {next_p}; sem stays {sem}",
                        [],
                        holders,
                    )
                    holders.append(next_p)
                    emit("wakeup", f"{next_p} wakes because {pid} executed V()", [], holders)
                else:
                    sem += 1
                    procs[pid] = "READY"
                    emit("V_signal", f"{pid}: V() - sem->{sem} (no waiters)", [], holders)

                emit("exit_cs", f"{pid} left critical section", [], holders)

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", f"Semaphore done. counter={counter}", [])
        return steps, {"final_counter": counter, "initial_slots": initial, "mutual_exclusion": initial == 1}

    def _producer_consumer(self, config: dict) -> tuple[list, dict]:
        """
        Producer-Consumer (Bounded Buffer) Problem.

        Reference: Silberschatz §6.4 / Dijkstra 1968.

        Problem statement:
        A producer and consumer share a bounded buffer of size N.
        Without synchronization: the producer may write to a full buffer
        (overflow) or the consumer may read from an empty one (underflow).

        Solution uses THREE semaphores:
            mutex  (initial=1) — binary semaphore protecting buffer access.
                                 Ensures at most one process modifies the
                                 buffer at a time (mutual exclusion).
            empty  (initial=N) — counts available empty slots.
                                 Producer waits on this before writing.
            full   (initial=0) — counts filled slots.
                                 Consumer waits on this before reading.

        Producer protocol:                Consumer protocol:
            P(empty)   ← wait for slot        P(full)    ← wait for item
            P(mutex)   ← enter CS             P(mutex)   ← enter CS
            add item                           remove item
            V(mutex)   ← exit CS              V(mutex)   ← exit CS
            V(full)    ← signal item ready     V(empty)   ← signal slot free

        Critical ordering rule (Silberschatz §6.4):
        P(empty)/P(full) MUST come BEFORE P(mutex).
        Reversing the order (P(mutex) first) risks deadlock: the producer
        holds mutex and waits on empty; the consumer is blocked on mutex
        and cannot call V(empty) → circular wait.
        """
        buffer_size = int(config.get("buffer_size", 5))
        items = int(config.get("items", 6))
        steps: list[dict] = []
        tick = 0
        buffer: list[int] = []
        procs = {"Producer": "READY", "Consumer": "READY"}
        mutex = 1  # Binary semaphore for buffer protection
        empty_slots = buffer_size
        full_slots = 0
        produced = consumed = 0

        def emit(action: str, msg: str, active: str | None = None) -> None:
            nonlocal tick
            cs = [active] if active else []
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs,
                    resources={"mutex": mutex, "empty": empty_slots, "full": full_slots},
                    shared_vars={"buffer": buffer[:], "produced": produced, "consumed": consumed},
                )
            )
            tick += 1

        emit("init", f"Producer-Consumer: buffer_size={buffer_size}, items={items}. mutex=1, empty={buffer_size}, full=0", None)

        item_id = 0
        while consumed < items:
            # --- Producer ---
            if produced < items and empty_slots > 0:
                procs["Producer"] = "RUNNING"
                procs["Consumer"] = "READY"

                # P(empty) — wait for empty slot
                emit("P_empty", f"Producer: P(empty) — empty_slots={empty_slots}→{empty_slots-1}", "Producer")
                empty_slots -= 1

                # P(mutex) — enter critical section
                if mutex == 0:
                    emit("P_mutex_wait", "Producer: P(mutex) — waiting (mutex=0)", None)
                mutex = 0  # Acquire mutex
                emit("P_mutex", f"Producer: P(mutex) — acquired lock, mutex=0 (locked)", "Producer")

                # Produce item and add to buffer
                item_id += 1
                buffer.append(item_id)
                produced += 1
                emit("produce", f"Producer: added item {item_id} to buffer={buffer}", "Producer")

                # V(mutex) — release mutex
                mutex = 1
                emit("V_mutex", f"Producer: V(mutex) — released lock, mutex=1 (unlocked)", "Producer")

                # V(full) — signal item available
                full_slots += 1
                emit("V_full", f"Producer: V(full) — full_slots={full_slots}", None)
                procs["Producer"] = "READY"

            # --- Consumer ---
            if full_slots > 0 and consumed < produced:
                procs["Consumer"] = "RUNNING"
                procs["Producer"] = "READY"

                # P(full) — wait for item
                emit("P_full", f"Consumer: P(full) — full_slots={full_slots}→{full_slots-1}", "Consumer")
                full_slots -= 1

                # P(mutex) — enter critical section
                if mutex == 0:
                    emit("P_mutex_wait", "Consumer: P(mutex) — waiting (mutex=0)", None)
                mutex = 0  # Acquire mutex
                emit("P_mutex", f"Consumer: P(mutex) — acquired lock, mutex=0 (locked)", "Consumer")

                # Consume item from buffer
                item = buffer.pop(0)
                consumed += 1
                emit("consume", f"Consumer: removed item {item} from buffer={buffer}", "Consumer")

                # V(mutex) — release mutex
                mutex = 1
                emit("V_mutex", f"Consumer: V(mutex) — released lock, mutex=1 (unlocked)", "Consumer")

                # V(empty) — signal slot available
                empty_slots += 1
                emit("V_empty", f"Consumer: V(empty) — empty_slots={empty_slots}", None)
                procs["Consumer"] = "READY"

        procs = {k: "TERMINATED" for k in procs}
        emit("done", f"Producer-Consumer complete. Produced={produced}, Consumed={consumed}", None)
        return steps, {
            "produced": produced,
            "consumed": consumed,
            "buffer_size": buffer_size,
            "mutual_exclusion": True,
        }

    def _readers_writers(self, config: dict) -> tuple[list, dict]:
        """
        First Readers-Writers Problem (readers-preference variant).

        Reference: Silberschatz §7.1.2 / Courtois et al. 1971.

        Problem statement:
        Multiple readers may access shared data concurrently (reading does not
        modify the data, so concurrent reads are safe).  A writer needs EXCLUSIVE
        access: no reader or other writer may be active while it writes.

        Shared variables:
            read_count  — number of currently active readers
            write_lock  — binary semaphore; held by readers (as a group) or a writer

        Reader protocol:
            acquire(mutex)          ← protect read_count update
            read_count += 1
            if read_count == 1: P(write_lock)   ← first reader locks out writers
            release(mutex)
            --- read shared data ---
            acquire(mutex)
            read_count -= 1
            if read_count == 0: V(write_lock)   ← last reader releases writers
            release(mutex)

        Writer protocol:
            P(write_lock)           ← exclusive access
            --- write shared data ---
            V(write_lock)

        Readers-preference (first problem): readers are never blocked by waiting
        writers — as long as a reader holds write_lock, new readers may join.
        This can cause WRITER STARVATION (Silberschatz §7.1.2).

        The second readers-writers problem gives writers priority to avoid starvation.
        """
        return self._readers_writers_contention(config)

    def _readers_writers_contention(self, config: dict) -> tuple[list, dict]:
        """
        Simulate the first readers-writers problem: readers share, writers wait.

        The simulation shows a group of readers entering together (concurrent
        reads are allowed), with writers blocked until all readers finish.
        """
        readers = int(config.get("readers", 2))
        writers = int(config.get("writers", 2))
        ops = int(config.get("operations", 2))
        steps: list[dict] = []
        tick = 0
        read_count = 0
        write_lock = False
        procs: dict[str, str] = {}
        for i in range(readers):
            procs[f"R{i}"] = "READY"
        for i in range(writers):
            procs[f"W{i}"] = "READY"
        waiting: list[str] = []

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick,
                    procs,
                    action,
                    msg,
                    critical_section=cs,
                    waiting_queue=list(waiting),
                    shared_vars={"read_count": read_count, "write_lock": write_lock},
                )
            )
            tick += 1

        emit("init", "Readers-Writers: readers share access; writers require exclusive access", [])

        for operation in range(ops):
            active_readers: list[str] = []
            emit("round_start", f"Operation {operation + 1}: reader group arrives before writers", [])

            for i in range(readers):
                pid = f"R{i}"
                procs[pid] = "RUNNING"
                emit("read_request", f"{pid} wants to read", active_readers)
                if read_count == 0:
                    write_lock = True
                    emit("read_lock", f"{pid} is first reader - acquires write_lock against writers", active_readers)
                read_count += 1
                active_readers.append(pid)
                procs[pid] = "RUNNING"
                emit("reading", f"{pid} starts reading with {read_count} active reader(s)", active_readers)

            for i in range(writers):
                pid = f"W{i}"
                procs[pid] = "BLOCKED"
                waiting.append(pid)
                emit("write_block", f"{pid} blocked - readers active, write_lock=True", active_readers)

            while active_readers:
                pid = active_readers.pop(0)
                read_count -= 1
                procs[pid] = "READY"
                if read_count == 0:
                    write_lock = False
                    emit("read_release", f"{pid} is last reader - releases write_lock", active_readers)
                else:
                    emit("read_done", f"{pid} finishes; {read_count} reader(s) still active", active_readers)

            while waiting:
                pid = waiting.pop(0)
                procs[pid] = "RUNNING"
                write_lock = True
                emit("writing", f"{pid} writes exclusively - no readers active", [pid])
                write_lock = False
                procs[pid] = "READY"
                emit("write_release", f"{pid} releases write_lock", [])

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", "Readers-Writers complete", [])
        return steps, {"readers": readers, "writers": writers, "reader_sharing": True}

    def _monitor(self, config: dict) -> tuple[list, dict]:
        """
        Monitor with Condition Variables — signal-and-continue semantics.

        Reference: Silberschatz §6.7 / Hoare 1974 / Hansen 1973.

        A monitor is a high-level synchronization construct that encapsulates:
            - shared data
            - the procedures that operate on it
            - a mutex that is automatically acquired on procedure entry and
              released on procedure exit

        Condition variables allow processes inside the monitor to wait for a
        specific condition without holding the monitor lock:

            wait(cv)   — releases the monitor lock and suspends the process.
                         The process joins a FIFO condition queue.

            signal(cv) — wakes the first process waiting on cv.

        Signal semantics used here: SIGNAL-AND-CONTINUE (Brinch Hansen)
            The signalling process CONTINUES running; the woken process waits
            until the signaller exits the monitor.
            (Alternative: SIGNAL-AND-WAIT — Hoare semantics — signaller gives
            up the monitor to the woken process immediately.)

        Simulation scenario:
            Phase 1: P1..Pn-1 enter, find data=0 (condition not met), call wait(cv)
                     → each releases the monitor lock and joins the condition queue.
            Phase 2: P0 enters, sets data=1, calls broadcast(cv) to wake all waiters.
            Phase 3: Woken processes re-enter the monitor, re-check condition, proceed.

        Note: broadcast(cv) is used here (equivalent to Java's notifyAll()).
        In the standard textbook example, individual signal() calls are used.
        """
        n = int(config.get("processes", 3))
        steps: list[dict] = []
        tick = 0
        monitor_lock = False
        condition_queue: list[str] = []
        shared_data = 0
        procs = {f"P{i}": "READY" for i in range(n)}

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs, waiting_queue=list(condition_queue),
                    resources={"monitor_locked": monitor_lock},
                    shared_vars={"data": shared_data},
                )
            )
            tick += 1

        emit("init", "Monitor initialized — condition variable cv, shared data=0", [])

        # Phase 1: P1..Pn-1 enter, find data==0, call wait()
        for i in range(1, n):
            pid = f"P{i}"
            procs[pid] = "RUNNING"
            monitor_lock = True
            emit("enter_monitor", f"{pid} enters monitor — acquires monitor lock", [pid])
            emit("monitor_cs", f"{pid} checks condition: data={shared_data} (need data>0)", [pid])
            # Condition not met — call wait()
            procs[pid] = "WAITING"
            condition_queue.append(pid)
            monitor_lock = False
            emit("wait_cv", f"{pid}: wait(cv) — releases monitor lock, joins condition queue", [])

        # Phase 2: P0 enters, updates data, signals all waiters
        pid0 = "P0"
        procs[pid0] = "RUNNING"
        monitor_lock = True
        emit("enter_monitor", f"{pid0} enters monitor — acquires monitor lock", [pid0])
        shared_data += 1
        emit("update", f"{pid0} updates data={shared_data}", [pid0])

        # Broadcast to all waiting processes (signal_all / notifyAll).
        # Each individual signal(cv) wakes exactly ONE waiter; calling it in a
        # loop until the queue is empty is equivalent to broadcast(cv) /
        # notifyAll() in Java. Labelled correctly here to distinguish from a
        # single signal() call.
        while condition_queue:
            wake = condition_queue.pop(0)
            emit("signal_all", f"{pid0}: broadcast(cv) / signal_all — waking {wake} ({len(condition_queue)} still queued)", [pid0])
            procs[wake] = "WAITING"
            # Woken process re-enters monitor after P0 exits (signal-and-continue)
            emit("wakeup", f"{wake} woken — will compete for monitor lock after {pid0} exits (signal-and-continue)", [pid0])

        monitor_lock = False
        procs[pid0] = "READY"
        emit("exit_monitor", f"{pid0} exits monitor — releases monitor lock", [])

        # Phase 3: woken processes re-enter, check condition, proceed
        for i in range(1, n):
            pid = f"P{i}"
            procs[pid] = "RUNNING"
            monitor_lock = True
            emit("enter_monitor", f"{pid} re-enters monitor after being signalled", [pid])
            emit("monitor_cs", f"{pid} re-checks condition: data={shared_data} ✓", [pid])
            shared_data += 1
            emit("update", f"{pid} updates data={shared_data}", [pid])
            monitor_lock = False
            procs[pid] = "READY"
            emit("exit_monitor", f"{pid} exits monitor", [])

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit("done", f"Monitor complete. data={shared_data}", [])
        return steps, {"final_data": shared_data}

    def _race_condition(self, config: dict) -> tuple[list, dict]:
        """
        Race Condition Demonstration — the Lost-Update Problem.

        Reference: Silberschatz §6.1.

        A race condition occurs when the final result of a concurrent operation
        depends on the scheduling order of the participating processes.  The
        classic manifestation is the LOST UPDATE on a shared counter.

        UNSAFE mode (corrected=False) — no synchronization:
            All processes execute the read-modify-write sequence concurrently.
            Classic interleaving:
                P0 reads X=5    P1 reads X=5    ← both see the same stale value
                P0 computes 6   P1 computes 6
                P0 writes X=6   P1 writes X=6   ← second write OVERWRITES the first
            Result: counter increased by 1 instead of 2 → LOST UPDATE.

            With n processes and increments rounds, the expected final value is
            n × increments, but each round only adds 1 (last write wins).
            Final counter = increments (not n × increments).

        SAFE mode (corrected=True) — mutex-protected:
            The mutex ensures each read-modify-write is atomic (indivisible).
            No interleaving is possible inside the critical section.
            Final counter = n × increments (correct).

        Why this matters:
        The race condition is the fundamental problem that ALL synchronization
        primitives are designed to prevent.  The critical section (CS) is the
        code between acquiring and releasing the lock.
        """
        unsafe = config.get("corrected", False) is False
        n = int(config.get("processes", 2))  # Use 2 processes for clear demo
        increments = int(config.get("increments", 3))
        steps: list[dict] = []
        tick = 0
        counter = 0
        procs = {f"P{i}": "READY" for i in range(n)}
        lock = False
        wait_queue: list[str] = []

        def emit(action: str, msg: str, cs: list[str]) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=cs,
                    waiting_queue=list(wait_queue),
                    shared_vars={"counter": counter, "unsafe_mode": unsafe},
                    resources={"lock": lock},
                )
            )
            tick += 1

        mode = "UNSAFE (no synchronization)" if unsafe else "SAFE (mutex protected)"
        emit("init", f"Race condition demo — {mode}. {n} processes, {increments} increments each.", [])

        expected = n * increments

        for round_num in range(increments):
            emit("round_start", f"--- Round {round_num + 1} of {increments} ---", [])

            # In unsafe mode: simulate the classic interleaved lost-update scenario
            if unsafe and n >= 2:
                # Both processes read the current value simultaneously
                for i in range(n):
                    pid = f"P{i}"
                    procs[pid] = "RUNNING"
                emit("read_phase", f"All processes read counter={counter} simultaneously", [])

                # Store what each process "saw" locally
                local_values = {f"P{i}": counter for i in range(n)}

                # Each process computes its new value
                for i in range(n):
                    pid = f"P{i}"
                    emit("compute", f"{pid}: local_copy={local_values[pid]}, computes local+1={local_values[pid]+1}", [])

                # Now the writes happen — last write wins, causing lost updates
                for i in range(n):
                    pid = f"P{i}"
                    # Each writes what they computed, overwriting others
                    counter = local_values[pid] + 1
                    emit("write", f"{pid} writes counter={counter} (overwrites previous!)", [])
                    procs[pid] = "READY"

                # Demonstrate the lost update: all N processes incremented, but counter only went up by 1
                emit("lost_update", f"LOST UPDATE: {n} processes tried to increment, counter only increased by 1", [])

            else:
                # SAFE mode: mutex protects the critical section
                for i in range(n):
                    pid = f"P{i}"
                    procs[pid] = "RUNNING"
                    emit("request_lock", f"{pid} requests mutex", [])

                    if lock:
                        # Another process holds the lock — must wait
                        procs[pid] = "BLOCKED"
                        wait_queue.append(pid)
                        emit("blocked", f"{pid} blocked — mutex held by another process", [])
                        # In sequential sim, the holder will release before we proceed
                        wait_queue.remove(pid)
                        procs[pid] = "RUNNING"
                        emit("unblocked", f"{pid} acquired mutex after waiting", [])

                    lock = True
                    emit("enter_cs", f"{pid} enters critical section — lock=True", [pid])

                    # Read-modify-write inside CS
                    old_val = counter
                    emit("read", f"{pid} reads counter={old_val}", [pid])
                    counter = old_val + 1
                    emit("write", f"{pid} writes counter={counter}", [pid])

                    # Release lock
                    lock = False
                    procs[pid] = "READY"
                    emit("exit_cs", f"{pid} exits critical section — lock=False", [])

        # Calculate what we expect vs what we got
        if unsafe and n >= 2:
            # In unsafe mode with interleaving, we lose (n-1) increments per round
            # So final counter = increments (each round only adds 1 instead of n)
            final_counter = increments
            race_detected = True
        else:
            final_counter = expected
            race_detected = False

        # Update counter to reflect the actual outcome
        counter = final_counter

        for pid in procs:
            procs[pid] = "TERMINATED"
        emit(
            "done",
            f"Final counter={counter}, expected={expected} ({n} processes × {increments} increments). "
            f"{'⚠ RACE CONDITION DETECTED — lost updates occurred!' if race_detected else '✓ Correct — mutual exclusion prevented race'}",
            [],
        )
        return steps, {
            "final_counter":    counter,
            "expected":         expected,
            "race_detected":    race_detected,
            # mutual_exclusion is False in unsafe mode — the race condition demo
            # explicitly violates ME; the analyzer must not award ME points for it.
            "mutual_exclusion": not unsafe,
            "corrected":        not unsafe,
            "lost_updates":     expected - counter if race_detected else 0,
        }

    def _deadlock_demo(self, config: dict) -> tuple[list, dict]:
        """
        Deadlock Demonstration — Circular Wait on Two Resources.

        Reference: Silberschatz §8.3.1.

        Deadlock occurs when ALL four Coffman conditions hold simultaneously:
            1. Mutual exclusion  — resources are non-shareable.
            2. Hold and wait     — a process holds at least one resource
                                   while waiting for another.
            3. No preemption     — resources cannot be forcibly taken.
            4. Circular wait     — P0 waits for R2 held by P1;
                                   P1 waits for R1 held by P0.

        Scenario:
            P0 acquires R1, then requests R2.
            P1 acquires R2, then requests R1.
            Neither can proceed → DEADLOCK.

        Resource-allocation graph (Silberschatz §8.3):
            P0 → R2 → P1 → R1 → P0   (cycle = deadlock)

        Recovery options (Silberschatz §8.7):
            - Process termination: abort one or both processes.
            - Resource preemption: forcibly take R2 from P1 and give to P0.
            - Prevention: enforce a global resource ordering
              (P0 and P1 must both acquire in order R1 → R2, breaking hold-and-wait).
        """
        steps: list[dict] = []
        tick = 0
        resources = {"R1": "P0", "R2": None}
        procs = {"P0": "RUNNING", "P1": "RUNNING"}

        def emit(action: str, msg: str, deadlock: bool = False) -> None:
            nonlocal tick
            steps.append(
                self._step(
                    tick, procs, action, msg,
                    critical_section=[],
                    waiting_queue=["P1"] if deadlock else [],
                    resources={"R1": resources["R1"], "R2": resources["R2"]},
                    shared_vars={"deadlock": deadlock},
                )
            )
            tick += 1

        emit("init", "P0 holds R1, wants R2; P1 holds R2, wants R1", False)
        resources = {"R1": "P0", "R2": "P1"}
        emit("hold_wait", "P0 holds R1, requests R2", False)
        emit("hold_wait", "P1 holds R2, requests R1", False)
        procs["P0"] = "BLOCKED"
        procs["P1"] = "BLOCKED"
        emit("deadlock", "DEADLOCK: circular wait — P0↔P1", True)
        emit("starvation", "Processes cannot proceed without external intervention", True)
        procs = {k: "BLOCKED" for k in procs}
        emit("done", "Deadlock demonstration complete", True)
        return steps, {"deadlock": True, "recovery": "Break circular wait or preempt resources"}
