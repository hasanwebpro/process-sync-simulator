"""
scheduler.py — CPU Scheduling Algorithms
==========================================

Implements five classical CPU scheduling algorithms as discrete-event
simulations.  Each algorithm produces:

    gantt    — ordered list of {pid, start, end} segments (the Gantt chart)
    metrics  — per-process {CT, TAT, WT, RT} table
    timeline — gantt enriched with duration and colour (for the UI canvas)

Key metric formulae (Silberschatz §6.1)
----------------------------------------
    CT  = Completion Time    — clock tick when the process finishes
    TAT = Turnaround Time    = CT − Arrival Time
    WT  = Waiting Time       = TAT − Burst Time
    RT  = Response Time      = first_CPU_tick − Arrival Time
    Throughput               = n / (last CT − first Arrival)

Algorithm classification
-------------------------
    Non-preemptive — FCFS, SJF, Priority
        Once a process starts, it runs to completion.
        No context switches mid-burst → fewer races, less overhead.

    Preemptive — SRTF, Round Robin
        The CPU can be taken from a running process.
        Enables fairness and responsiveness at the cost of context-switch overhead.
        Preemption is the necessary condition for exposing race conditions in Phase 2.
"""

from __future__ import annotations

from typing import Any

from .constants import VALID_SCHED_ALGORITHMS


class CPUScheduler:
    """
    Discrete-event simulation of five CPU scheduling algorithms.

    All algorithms share the same output contract:
        run() → { algorithm, processes, gantt, timeline, metrics, averages }

    The internal dispatch table (_algorithms) maps each string ID to its
    implementation method, making it trivial to add new algorithms later.
    """

    def __init__(self) -> None:
        # Dispatch table: algorithm ID → implementation method
        self._algorithms = {
            "fcfs":        self._fcfs,
            "sjf":         self._sjf,
            "srtf":        self._srtf,
            "round_robin": self._round_robin,
            "priority":    self._priority,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────────

    def list_algorithms(self) -> list[dict[str, str]]:
        """Return metadata for all supported algorithms (used by the UI dropdown)."""
        return [
            {"id": "fcfs",        "name": "FCFS",        "description": "First Come First Serve (non-preemptive)", "preemptive": False},
            {"id": "sjf",         "name": "SJF",         "description": "Shortest Job First (non-preemptive)",     "preemptive": False},
            {"id": "srtf",        "name": "SRTF",        "description": "Shortest Remaining Time First (preemptive)", "preemptive": True},
            {"id": "round_robin", "name": "Round Robin", "description": "Time-quantum preemptive",                  "preemptive": True},
            {"id": "priority",    "name": "Priority",    "description": "Non-preemptive priority scheduling",       "preemptive": False},
        ]

    def run(self, algorithm: str, processes: list[dict], quantum: int = 2) -> dict[str, Any]:
        """
        Execute a scheduling algorithm and return the full result.

        Parameters
        ----------
        algorithm  — one of the IDs returned by list_algorithms()
        processes  — list of process dicts (pid, arrival, burst, priority)
        quantum    — time quantum for Round Robin (ignored by other algorithms)

        Returns a dict with: algorithm, processes, gantt, timeline, metrics, averages
        """
        if algorithm not in self._algorithms:
            raise ValueError(f"Unknown scheduling algorithm: {algorithm}")

        # Normalise to guarantee consistent types before passing to algorithms
        normalized = self._normalize(processes)
        gantt, metrics, timeline = self._algorithms[algorithm](normalized, quantum)

        return {
            "algorithm": algorithm,
            "processes": normalized,
            # quantum is only meaningful for Round Robin; show None otherwise
            "quantum":   quantum if algorithm == "round_robin" else None,
            "gantt":     gantt,
            "timeline":  timeline,
            "metrics":   metrics,
            "averages":  self._averages(metrics),
        }

    def compare_all(self, processes: list[dict], quantum: int = 2) -> dict[str, Any]:
        """Run all five algorithms on the same process set and return results keyed by ID."""
        return {algo: self.run(algo, processes, quantum) for algo in self._algorithms}

    # ──────────────────────────────────────────────────────────────────────────
    # Shared helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _normalize(self, processes: list[dict]) -> list[dict]:
        """
        Coerce all process fields to their expected Python types.

        This ensures every algorithm receives clean ints rather than strings
        that might have come in from JSON parsing.
        """
        return [
            {
                "pid":      p.get("pid", f"P{i+1}"),
                "arrival":  int(p.get("arrival",  0)),
                "burst":    int(p.get("burst",    1)),
                "priority": int(p.get("priority", i+1)),
            }
            for i, p in enumerate(processes)
        ]

    def _averages(self, metrics: list[dict]) -> dict[str, float]:
        """
        Compute aggregate performance metrics across all processes.

        Throughput formula (Silberschatz §6.1):
            Throughput = number of processes completed / scheduling span
            where scheduling span = last completion time − first arrival time.

        Using raw completion time as the denominator (the naive approach) would
        underestimate throughput when processes arrive after t=0, because it
        counts idle time before the first process arrives as part of the span.
        """
        n = len(metrics) or 1
        if not metrics:
            return {
                "avg_completion": 0, "avg_turnaround": 0,
                "avg_waiting": 0,    "avg_response": 0,  "throughput": 0,
            }

        last_ct  = max(m["completion"] for m in metrics)
        first_at = min(m["arrival"]    for m in metrics)
        # Span is floored at 1 to prevent ZeroDivisionError when a single
        # process arrives and completes at t=0 (degenerate edge case).
        span = max(last_ct - first_at, 1)

        return {
            "avg_completion": round(sum(m["completion"] for m in metrics) / n, 2),
            "avg_turnaround": round(sum(m["turnaround"] for m in metrics) / n, 2),
            "avg_waiting":    round(sum(m["waiting"]    for m in metrics) / n, 2),
            "avg_response":   round(sum(m["response"]   for m in metrics) / n, 2),
            "throughput":     round(n / span, 4),
        }

    def _build_metrics(
        self,
        processes:  list[dict],
        completion: dict[str, int],
        first_run:  dict[str, int],
    ) -> list[dict]:
        """
        Compute per-process scheduling metrics from completion and first-run maps.

        Formulae (Silberschatz §6.1):
            TAT = CT  − Arrival  (total time process spent in system)
            WT  = TAT − Burst    (time spent waiting, not executing)
            RT  = first_run − Arrival  (time until first CPU assignment)
        """
        out = []
        for p in processes:
            pid = p["pid"]
            ct  = completion[pid]
            tat = ct - p["arrival"]                 # Turnaround Time
            wt  = tat - p["burst"]                  # Waiting Time
            rt  = first_run[pid] - p["arrival"]     # Response Time
            out.append({
                "pid":        pid,
                "arrival":    p["arrival"],
                "burst":      p["burst"],
                "priority":   p["priority"],
                "completion": ct,
                "turnaround": tat,
                "waiting":    wt,
                "response":   rt,
            })
        return out

    # ──────────────────────────────────────────────────────────────────────────
    # Algorithm 1 — FCFS (First Come First Serve)
    # ──────────────────────────────────────────────────────────────────────────

    def _fcfs(self, processes: list[dict], _quantum: int) -> tuple:
        """
        First Come First Serve — the simplest non-preemptive scheduling policy.

        Rule: processes are served in order of arrival time.
        Tie-break: when two processes arrive simultaneously, the one with the
        lexicographically smaller PID runs first.

        Properties (Silberschatz §6.3.1):
        - Non-preemptive: once dispatched, a process runs to completion.
        - Fair in arrival order: no process is skipped.
        - Suffers from the Convoy Effect: a long process holds up all later ones,
          inflating waiting time for short processes behind it.
        - Low overhead: no priority comparisons or preemption bookkeeping.

        Phase 2 significance:
        Because processes run without interruption, their [first_tick, last_tick]
        windows never overlap — FCFS exposes very few (often zero) race conditions
        or CS violations.  This is the baseline that demonstrates non-preemptive
        scheduling "hides" synchronization problems.
        """
        # Sort by arrival time; PID used as a deterministic tie-breaker
        sorted_p = sorted(processes, key=lambda x: (x["arrival"], x["pid"]))
        time = 0
        gantt:      list[dict]       = []
        completion: dict[str, int]   = {}
        first_run:  dict[str, int]   = {}

        for p in sorted_p:
            # If the CPU is idle before this process arrives, insert an IDLE segment
            if time < p["arrival"]:
                gantt.append({"pid": "IDLE", "start": time, "end": p["arrival"]})
                time = p["arrival"]

            first_run[p["pid"]] = time          # record when the process first ran
            start = time
            time += p["burst"]                  # run the process to completion
            gantt.append({"pid": p["pid"], "start": start, "end": time})
            completion[p["pid"]] = time

        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    # ──────────────────────────────────────────────────────────────────────────
    # Algorithm 2 — SJF (Shortest Job First)
    # ──────────────────────────────────────────────────────────────────────────

    def _sjf(self, processes: list[dict], _quantum: int) -> tuple:
        """
        Shortest Job First — non-preemptive variant.

        Rule: at each scheduling decision, pick the arrived process with the
        smallest burst time.  If the CPU is free and multiple processes have
        arrived, the shortest one wins.

        Properties (Silberschatz §6.3.2):
        - Non-preemptive: the currently running process is never interrupted.
        - Optimal average waiting time among non-preemptive algorithms
          (provable by exchange argument: swapping a shorter job earlier always
          reduces the average wait).
        - Starvation risk: long processes may be indefinitely delayed if short
          processes keep arriving (addressed by Ageing in real systems).
        - Requires knowing burst times in advance — impractical in real OSes
          (estimated via exponential averaging in practice).

        Tie-break: (burst, arrival, pid) — earlier arrival wins ties on burst;
        PID used for determinism.
        """
        remaining: dict[str, int] = {p["pid"]: p["burst"]   for p in processes}
        arrival:   dict[str, int] = {p["pid"]: p["arrival"] for p in processes}
        done:      set[str]       = set()
        time = 0
        gantt:      list[dict]     = []
        completion: dict[str, int] = {}
        first_run:  dict[str, int] = {}

        while len(done) < len(processes):
            # Build the ready queue: all arrived and not-yet-completed processes
            available = [
                p for p in processes
                if p["pid"] not in done and arrival[p["pid"]] <= time
            ]

            if not available:
                # No process has arrived yet — jump the clock forward to avoid
                # spinning through idle ticks one at a time
                next_arr = min(arrival[p["pid"]] for p in processes if p["pid"] not in done)
                gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                time = next_arr
                continue

            # Select the shortest available job (with tie-breaks for determinism)
            chosen = min(available, key=lambda x: (remaining[x["pid"]], x["arrival"], x["pid"]))
            pid = chosen["pid"]

            if pid not in first_run:
                first_run[pid] = time           # record first CPU assignment

            start = time
            time += remaining[pid]              # run to completion (non-preemptive)
            gantt.append({"pid": pid, "start": start, "end": time})
            completion[pid] = time
            done.add(pid)

        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    # ──────────────────────────────────────────────────────────────────────────
    # Algorithm 3 — SRTF (Shortest Remaining Time First)
    # ──────────────────────────────────────────────────────────────────────────

    def _srtf(self, processes: list[dict], _quantum: int) -> tuple:
        """
        Shortest Remaining Time First — preemptive variant of SJF.

        Rule: at every clock tick, re-evaluate all arrived processes and run
        the one with the smallest remaining burst time.  If a newly arrived
        process has a shorter remaining time than the currently running process,
        it preempts the CPU immediately.

        Properties (Silberschatz §6.3.2):
        - Preemptive: the currently running process can be interrupted every tick.
        - Optimal average waiting time among ALL scheduling algorithms
          (provable: no other schedule can achieve lower average WT for a given
          process set — this is the online analogue of SJF's optimality).
        - High overhead: requires a preemption check on every tick and on every
          new arrival.
        - Starvation risk for long processes — same concern as SJF.

        Implementation note:
        The simulation advances one tick at a time.  To keep the Gantt chart
        readable, consecutive ticks on the same process are merged into a single
        segment by `_merge_gantt()`.

        Phase 2 significance:
        Frequent preemptions produce many context switches.  These create
        overlapping execution windows, which is the mechanism by which race
        conditions and CS violations are exposed in Phase 2.
        """
        remaining: dict[str, int]  = {p["pid"]: p["burst"]   for p in processes}
        arrival:   dict[str, int]  = {p["pid"]: p["arrival"] for p in processes}
        done:      set[str]        = set()
        time = 0
        gantt:      list[dict]     = []
        completion: dict[str, int] = {}
        first_run:  dict[str, int] = {}
        current:    str | None     = None      # PID currently on the CPU

        while len(done) < len(processes):
            # Ready queue: arrived, not done, still has remaining burst
            available = [
                p for p in processes
                if p["pid"] not in done
                and arrival[p["pid"]] <= time
                and remaining[p["pid"]] > 0
            ]

            if not available:
                # Idle gap: jump the clock to the next arriving process
                undone = [p for p in processes if p["pid"] not in done]
                if not undone:
                    break
                next_arr = min(arrival[p["pid"]] for p in undone)
                if next_arr > time:
                    # Extend an existing IDLE segment or start a new one
                    if gantt and gantt[-1]["pid"] == "IDLE":
                        gantt[-1]["end"] = next_arr
                    else:
                        gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                    time = next_arr
                    current = None
                else:
                    # Safety advance: prevents infinite loop when arrival==time
                    # but all matching processes already have remaining==0
                    time += 1
                continue

            # Preemption decision: pick process with smallest remaining time
            chosen = min(
                available,
                key=lambda x: (remaining[x["pid"]], x["arrival"], x["pid"]),
            )
            pid = chosen["pid"]

            # Record the very first tick this process ran (for Response Time)
            if pid not in first_run:
                first_run[pid] = time

            # Extend the current Gantt segment if the same process continues,
            # or start a new segment if the CPU switched to a different process
            if current != pid:
                gantt.append({"pid": pid, "start": time, "end": time + 1})
                current = pid
            else:
                gantt[-1]["end"] = time + 1     # extend the running segment

            remaining[pid] -= 1                 # consume one tick of burst
            time += 1

            # Process completes when its remaining burst reaches zero
            if remaining[pid] == 0:
                completion[pid] = time
                done.add(pid)
                current = None                  # CPU is free at next tick

        # Merge adjacent segments of the same PID before returning
        gantt   = self._merge_gantt(gantt)
        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    # ──────────────────────────────────────────────────────────────────────────
    # Algorithm 4 — Round Robin
    # ──────────────────────────────────────────────────────────────────────────

    def _round_robin(self, processes: list[dict], quantum: int) -> tuple:
        """
        Round Robin — time-sharing preemptive scheduling.

        Rule: each process in the FIFO ready queue gets a fixed time slice
        (quantum).  If it does not finish within the quantum, it is preempted
        and re-enqueued at the tail.

        Properties (Silberschatz §6.3.4):
        - Preemptive: every process is guaranteed CPU time within
          (n-1)*quantum ticks of entering the ready queue.
        - Best for time-sharing and interactive systems (fair responsiveness).
        - Performance depends heavily on quantum size:
            quantum → ∞  degenerates to FCFS (large batch processing)
            quantum → 1  gives maximum preemption (pure round-robin, high overhead)
            Rule of thumb: set quantum > 80% of burst times to limit switches.
        - Higher average TAT than SJF because all processes wait for all others.

        Arrival handling:
        Processes arriving during a quantum are added to the tail of the ready
        queue BEFORE the preempted process is re-enqueued — following the
        Silberschatz convention that new arrivals join behind the current process.

        Phase 2 significance:
        The frequent context switches caused by the quantum boundary are the
        primary mechanism for exposing race conditions and CS violations in Phase 2.
        """
        remaining:   dict[str, int] = {p["pid"]: p["burst"]   for p in processes}
        arrival:     dict[str, int] = {p["pid"]: p["arrival"] for p in processes}
        ready_queue: list[str]      = []        # FIFO ready queue (stores PIDs)
        done:        set[str]       = set()
        arrived:     set[str]       = set()     # tracks which processes have ever joined the queue
        time = 0
        n    = len(processes)
        gantt:      list[dict]     = []
        completion: dict[str, int] = {}
        first_run:  dict[str, int] = {}

        while len(done) < n:
            # Enqueue all processes that have arrived by the current time
            for p in sorted(processes, key=lambda x: x["arrival"]):
                if p["pid"] not in arrived and p["arrival"] <= time:
                    arrived.add(p["pid"])
                    ready_queue.append(p["pid"])

            if not ready_queue:
                # No process ready: advance clock to the next arrival
                next_arr = min(
                    arrival[p["pid"]] for p in processes if p["pid"] not in arrived
                )
                gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                time = next_arr
                continue

            # Dequeue the head process and run it for min(quantum, remaining)
            pid       = ready_queue.pop(0)
            if pid not in first_run:
                first_run[pid] = time
            exec_time = min(quantum, remaining[pid])
            start     = time
            time     += exec_time
            remaining[pid] -= exec_time
            gantt.append({"pid": pid, "start": start, "end": time})

            # Enqueue processes that arrived during this quantum (excluding current pid)
            # They join the tail before the preempted process is re-enqueued
            for p in sorted(processes, key=lambda x: x["arrival"]):
                if (
                    p["pid"] not in arrived
                    and p["arrival"] <= time
                    and p["pid"] != pid
                ):
                    arrived.add(p["pid"])
                    ready_queue.append(p["pid"])

            if remaining[pid] == 0:
                # Process completed within this quantum
                completion[pid] = time
                done.add(pid)
            else:
                # Preempted — re-enqueue at the tail (round-robin rotation)
                ready_queue.append(pid)

        gantt   = self._merge_gantt(gantt)
        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    # ──────────────────────────────────────────────────────────────────────────
    # Algorithm 5 — Priority Scheduling
    # ──────────────────────────────────────────────────────────────────────────

    def _priority(self, processes: list[dict], _quantum: int) -> tuple:
        """
        Non-preemptive Priority Scheduling.

        Rule: at each scheduling decision, pick the arrived process with the
        lowest priority number.  Lower number = higher urgency (Silberschatz §6.3.3).
        Once dispatched, the process runs to completion without preemption.

        Properties:
        - Non-preemptive: a running process cannot be interrupted by a higher-
          priority arrival.  The new process must wait for the next decision point.
        - Can be used to model real-time soft deadlines (assign shorter-deadline
          processes a higher priority number, i.e. lower number value).
        - Starvation: low-priority processes may never run if high-priority
          processes keep arriving.  Ageing (gradually increasing priority with
          wait time) is the standard remedy (Silberschatz §6.3.3).

        Tie-break: (priority, arrival, pid) — earlier arrival wins among equal
        priorities; PID used for full determinism.

        Design choice: availability is checked at each decision point (not at
        arrival time), so a high-priority process arriving after the CPU is
        already dispatched must wait for the current process to complete —
        this is the defining characteristic of the non-preemptive variant.
        """
        remaining: dict[str, int] = {p["pid"]: p["burst"]   for p in processes}
        arrival:   dict[str, int] = {p["pid"]: p["arrival"] for p in processes}
        done:      set[str]       = set()
        time = 0
        gantt:      list[dict]     = []
        completion: dict[str, int] = {}
        first_run:  dict[str, int] = {}

        while len(done) < len(processes):
            # Ready queue: processes that have arrived and not yet completed
            available = [
                p for p in processes
                if p["pid"] not in done and arrival[p["pid"]] <= time
            ]

            if not available:
                # CPU idle: advance to the next arrival event
                next_arr = min(
                    arrival[p["pid"]] for p in processes if p["pid"] not in done
                )
                gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                time = next_arr
                continue

            # Select the highest-priority arrived process
            # Tie-break: (priority_number, arrival, pid) for full determinism
            chosen = min(
                available,
                key=lambda x: (x["priority"], x["arrival"], x["pid"]),
            )
            pid = chosen["pid"]
            first_run[pid] = time               # record first CPU assignment
            start = time
            time += remaining[pid]              # run to completion
            gantt.append({"pid": pid, "start": start, "end": time})
            completion[pid] = time
            done.add(pid)

        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    # ──────────────────────────────────────────────────────────────────────────
    # Gantt chart helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _merge_gantt(self, gantt: list[dict]) -> list[dict]:
        """
        Collapse adjacent segments that belong to the same process.

        SRTF and Round Robin build Gantt charts one tick at a time, producing
        many tiny consecutive segments for the same PID.  Merging them gives a
        cleaner chart and reduces the number of canvas draw calls.

        Example:
            [{P1, 0→1}, {P1, 1→2}, {P2, 2→3}]
            → [{P1, 0→2}, {P2, 2→3}]
        """
        if not gantt:
            return []
        merged = [gantt[0].copy()]
        for seg in gantt[1:]:
            # Merge only if the same PID and the segments are contiguous
            if seg["pid"] == merged[-1]["pid"] and seg["start"] == merged[-1]["end"]:
                merged[-1]["end"] = seg["end"]
            else:
                merged.append(seg.copy())
        return merged

    def _timeline(self, gantt: list[dict]) -> list[dict]:
        """
        Enrich Gantt segments with a duration field and a display colour.

        Each process is assigned a consistent colour from a fixed palette so it
        looks the same across all algorithm comparisons.  IDLE segments use a
        neutral dark colour.  The timeline list is consumed directly by the
        canvas drawing functions in the frontend.
        """
        colors: dict[str, str] = {}
        palette = [
            "#00d4ff", "#7b61ff", "#00ff88", "#ff6b6b",
            "#ffd93d", "#ff9f43", "#a29bfe", "#fd79a8",
        ]
        timeline = []
        for seg in gantt:
            pid = seg["pid"]
            if pid not in colors:
                # IDLE gets a fixed neutral colour; processes get palette colours
                colors[pid] = "#444466" if pid == "IDLE" else palette[len(colors) % len(palette)]
            timeline.append({
                **seg,
                "duration": seg["end"] - seg["start"],
                "color":    colors[pid],
            })
        return timeline
