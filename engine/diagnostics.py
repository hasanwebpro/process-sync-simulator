"""
diagnostics.py — Phase 2: Unsynchronized Problem Detection + Technique Evaluation
====================================================================================

Purpose
-------
Replays the CPU scheduling trace from Phase 1 against a SHARED RESOURCE with
NO synchronization, then measures which classical OS synchronization problems
become observable.  The same workload is then analysed with each synchronization
technique to quantify how well each one resolves the detected problems.

Methodological principle (Silberschatz §6.1)
--------------------------------------------
The CPU scheduler is the INDEPENDENT VARIABLE.
Synchronization problems are the DEPENDENT VARIABLE.

    Scheduling → determines execution interleaving
    Interleaving → determines which shared-access problems surface

Non-preemptive (FCFS, SJF, Priority):
    Each process runs contiguously.  No other process accesses the shared
    resource while one is running → few or no race conditions / CS violations.

Preemptive (Round Robin, SRTF):
    Frequent context switches interleave process execution windows.
    Multiple processes can be mid-read-modify-write simultaneously →
    race conditions, CS violations, deadlock surface clearly.

What CAN be detected from a scheduling trace
--------------------------------------------
    Race condition     — overlapping read-modify-write windows (model approximation)
    CS violation       — same as above; "what if no lock existed"
    Deadlock           — hold-and-wait on two resources for the first two processes
    Starvation         — a process waits far longer than its peers

What CANNOT be detected from a generic scheduling trace
-------------------------------------------------------
    Livelock           — requires voluntary-yield retry code (no such code exists in scheduler)
    Producer-Consumer  — requires explicit producer/consumer role designation
    Readers-Writers    — requires explicit reader/writer role designation
    Dining Philosophers— requires ring-topology fork-acquisition protocol
    Sleeping Barber    — models I/O service queues, not CPU scheduling

The five non-detectable problems are correctly demonstrated in Phase 3 via
dedicated synchronization simulations.

Technique evaluation
--------------------
After detection, each synchronization technique is evaluated against the
detected problems using the _capability() function (textbook-grounded
capability matrix) and a performance model (overhead, waiting time, fairness).
Techniques are scored 0-100 and ranked.
"""

from __future__ import annotations

from typing import Any

from .scheduler import CPUScheduler


# ─────────────────────────────────────────────────────────────────────────────
#  Problem catalogue
# ─────────────────────────────────────────────────────────────────────────────

PROBLEM_META: dict[str, dict[str, str]] = {
    # ── Detectable from CPU scheduling traces ─────────────────────────────────
    # Race condition and CS violation: derived from interleaving of execution
    # windows; directionally correct — preemptive schedules expose more overlap.
    "race_condition": {"name": "Race Condition",             "category": "sync"},
    "cs_violation":   {"name": "Critical Section Violation", "category": "sync"},
    # Deadlock: hold-and-wait on 2 resources modelled over the first 2 processes
    # (Silberschatz §8.3 — circular wait). Category is sync, not scheduling.
    "deadlock":       {"name": "Deadlock",                   "category": "sync"},
    # Starvation: process waits far longer than peers — computed from real WT
    # values produced by the scheduler (Silberschatz §6.6).
    "starvation":     {"name": "Starvation",                 "category": "sync"},
    # ── Not detectable from generic scheduling traces ─────────────────────────
    # These problems require explicit role assignment (producer/consumer,
    # reader/writer) or specific resource-topology information that a generic
    # CPU scheduling trace does not provide. They are demonstrated in Phase 3.
    "livelock":            {"name": "Livelock",                  "category": "sync"},
    "producer_consumer":   {"name": "Producer–Consumer",         "category": "sync"},
    "readers_writers":     {"name": "Readers–Writers Conflict",  "category": "sync"},
    "dining_philosophers": {"name": "Dining Philosophers",       "category": "sync"},
    "sleeping_barber":     {"name": "Sleeping Barber",           "category": "sync"},
}


# ─────────────────────────────────────────────────────────────────────────────
#  Synchronization techniques
#  Each profile drives BOTH capability (what it can prevent) and a relative
#  performance/overhead model. Values are deliberately simple and monotone so
#  the comparison is explainable in a viva.
# ─────────────────────────────────────────────────────────────────────────────

TECHNIQUE_META: dict[str, dict[str, Any]] = {
    "mutex": {
        "name": "Mutex Lock",
        "desc": "Ownership lock; blocks waiters in a FIFO queue.",
        "ovh": 2, "blocks": True, "busy_wait": False, "concurrency": 1,
        "structured": False, "signaling": False, "two_proc_only": False,
        "cpu_efficiency": 0.95, "fairness": 0.90,
    },
    "binary_semaphore": {
        "name": "Binary Semaphore",
        "desc": "P/V on a 0/1 counter; signalling but no ownership.",
        "ovh": 2, "blocks": True, "busy_wait": False, "concurrency": 1,
        "structured": False, "signaling": True, "two_proc_only": False,
        "cpu_efficiency": 0.94, "fairness": 0.85,
    },
    "counting_semaphore": {
        "name": "Counting Semaphore",
        "desc": "P/V on an N counter; allows N concurrent holders.",
        "ovh": 2, "blocks": True, "busy_wait": False, "concurrency": 2,
        "structured": False, "signaling": True, "two_proc_only": False,
        "cpu_efficiency": 0.93, "fairness": 0.88,
    },
    "monitor": {
        "name": "Monitor",
        "desc": "Structured lock + condition variables; auto release.",
        "ovh": 1, "blocks": True, "busy_wait": False, "concurrency": 1,
        "structured": True, "signaling": True, "two_proc_only": False,
        "cpu_efficiency": 0.97, "fairness": 0.95,
    },
    "peterson": {
        "name": "Peterson's Algorithm",
        "desc": "Software mutual exclusion; busy-wait, two processes only.",
        "ovh": 3, "blocks": False, "busy_wait": True, "concurrency": 1,
        "structured": False, "signaling": False, "two_proc_only": True,
        "cpu_efficiency": 0.60, "fairness": 0.80,
    },
    "dekker": {
        "name": "Dekker's Algorithm",
        "desc": "First software ME solution; turn-based, two processes only.",
        "ovh": 3, "blocks": False, "busy_wait": True, "concurrency": 1,
        "structured": False, "signaling": False, "two_proc_only": True,
        "cpu_efficiency": 0.58, "fairness": 0.78,
    },
    "spinlock": {
        "name": "Spinlock",
        "desc": "Busy-wait lock; no queue, burns CPU under contention.",
        "ovh": 1, "blocks": False, "busy_wait": True, "concurrency": 1,
        "structured": False, "signaling": False, "two_proc_only": False,
        "cpu_efficiency": 0.55, "fairness": 0.55,
    },
    "condition_variable": {
        "name": "Condition Variables",
        "desc": "wait()/signal() with a mutex; clean blocking + ordering.",
        "ovh": 1, "blocks": True, "busy_wait": False, "concurrency": 1,
        "structured": True, "signaling": True, "two_proc_only": False,
        "cpu_efficiency": 0.96, "fairness": 0.93,
    },
}

ALL_TECHNIQUES = list(TECHNIQUE_META.keys())


def _capability(technique: str, problem: str, n_processes: int) -> str:
    """
    Return 'prevents' | 'partial' | 'no' for a (technique, problem) pair.

    All mappings are grounded in Silberschatz "Operating System Concepts" 10th ed.
    and Tanenbaum "Modern Operating Systems" 4th ed.

    Key corrections vs. naive mappings:
      * Deadlock — NO primitive prevents deadlock automatically. Monitor/CV
        provide the tools but require programmer discipline (Silberschatz §6.7,
        Lister 1977 nested-monitor deadlock). All are at best "partial".
      * Starvation — standard POSIX mutex/semaphore do NOT guarantee FIFO
        wake-up ordering (Silberschatz §6.5.2). Only structured primitives
        (monitor, condition_variable) with explicit FIFO condition queues
        provide bounded waiting.
      * Dining Philosophers — a bare mutex on each fork is the TEXTBOOK EXAMPLE
        of how deadlock arises (Silberschatz §7.1.3). Mutex alone is "partial"
        (provides mutual exclusion on forks, but does not prevent circular wait).
      * Livelock — blocking primitives avoid voluntary-yield loops ("partial"),
        but livelock cannot occur in a single-CPU sequential model at all.
    """
    t = TECHNIQUE_META[technique]
    blocks   = t["blocks"]
    signals  = t["signaling"]
    counting = t["concurrency"] > 1
    two_only = t["two_proc_only"]
    busy     = t["busy_wait"]
    structured = t["structured"]

    # ── Mutual-exclusion problems ─────────────────────────────────────────────
    if problem in ("race_condition", "cs_violation"):
        if two_only and n_processes > 2:
            return "no"      # Peterson/Dekker: limited to 2 processes
        return "prevents"    # every correct lock enforces ME (Silberschatz §6.1)

    # ── Deadlock ──────────────────────────────────────────────────────────────
    # No primitive prevents deadlock automatically (Silberschatz §8.1).
    # Monitors/CV provide tools for correct ordering, but programmer must apply
    # them — deadlock is still possible with incorrect monitor usage (Lister 1977).
    # Busy-wait primitives (spinlock, Peterson) offer no deadlock avoidance.
    if problem == "deadlock":
        if structured:          # monitor / condition_variable
            return "partial"    # best tools, but no automatic guarantee
        if blocks and not busy:
            return "partial"    # mutex / semaphore: discipline required (ABBA pattern)
        return "no"             # spinlock / Peterson: no resource-ordering support

    # ── Starvation ────────────────────────────────────────────────────────────
    # Standard POSIX mutex/semaphore wake-up order is implementation-defined
    # (Silberschatz §6.5.2). Only structured CV-based primitives with FIFO
    # condition queues provide formal bounded-waiting guarantees.
    if problem == "starvation":
        if busy and not blocks:
            return "no"          # spinlock/Peterson: no fair queue
        if two_only and n_processes > 2:
            return "no"
        if structured:
            return "prevents"    # monitor/CV: explicit FIFO condition queue
        return "partial"         # mutex/semaphore: depends on implementation

    # ── Livelock ─────────────────────────────────────────────────────────────
    # Livelock requires voluntary-yield retry loops; blocking primitives break
    # those loops (process blocks instead of retrying). Non-blocking busy-wait
    # primitives can participate in livelock retry loops.
    if problem == "livelock":
        if blocks:
            return "prevents"    # blocking replaces retry with sleep
        return "no"              # busy-wait can fuel retry loops

    # ── Producer–Consumer (bounded buffer) ────────────────────────────────────
    # Requires two counting semaphores (empty, full) + mutex for the buffer.
    # A mutex alone can protect the buffer but cannot block on full/empty.
    if problem == "producer_consumer":
        if counting or (signals and blocks):
            return "prevents"    # counting semaphore or CV-capable primitive
        if technique == "mutex":
            return "partial"     # protects buffer, but no slot-count blocking
        return "no"

    # ── Readers–Writers ───────────────────────────────────────────────────────
    # Requires either a counting semaphore (read_count) + mutex (write_lock),
    # or a monitor with condition variables.
    if problem == "readers_writers":
        if counting or technique in ("monitor", "condition_variable"):
            return "prevents"
        if technique in ("mutex", "binary_semaphore"):
            return "partial"     # serialises all access; correct but loses read concurrency
        return "no"

    # ── Dining Philosophers ───────────────────────────────────────────────────
    # A mutex on each fork is the CLASSIC example of deadlock-via-circular-wait
    # (Silberschatz §7.1.3). Mutex = partial (ME on forks, but naive acquisition
    # deadlocks). Monitor/CV with Hoare's solution = prevents.
    if problem == "dining_philosophers":
        if technique in ("monitor", "condition_variable"):
            return "prevents"    # Hoare's monitor solution (Silberschatz §6.7.2)
        if technique in ("counting_semaphore", "mutex", "binary_semaphore"):
            return "partial"     # provides ME on forks; deadlock needs extra logic
        return "no"

    if problem == "sleeping_barber":
        if counting or technique in ("condition_variable", "monitor"):
            return "prevents"
        if technique in ("mutex", "binary_semaphore"):
            return "partial"
        return "no"

    return "no"


# ─────────────────────────────────────────────────────────────────────────────
#  Diagnostics engine
# ─────────────────────────────────────────────────────────────────────────────

class DiagnosticsEngine:
    """Runs detection on a schedule, then evaluates each sync technique."""

    def __init__(self) -> None:
        self.scheduler = CPUScheduler()

    # ── public entry point ───────────────────────────────────────────────────
    def run(
        self,
        processes: list[dict],
        sched_algorithm: str = "round_robin",
        quantum: int = 2,
        techniques: list[str] | None = None,
    ) -> dict[str, Any]:
        techniques = techniques or ALL_TECHNIQUES
        sched = self.scheduler.run(sched_algorithm, processes, quantum)
        norm = sched["processes"]
        gantt = sched["gantt"]
        averages = sched["averages"]
        preemptive = sched_algorithm in ("round_robin", "srtf")

        cpu_trace = self._expand_gantt(gantt)
        base_metrics = self._base_metrics(gantt, norm, averages, sched.get("metrics"))

        # ── detection (unsynchronized baseline) ──
        problems = []
        problems.append(self._detect_race_and_cs(cpu_trace, norm))     # 2 entries
        problems.append(self._detect_deadlock(cpu_trace, norm, preemptive))
        problems.append(self._detect_starvation(sched, norm))
        problems.append(self._detect_livelock(cpu_trace, norm, preemptive))
        problems.append(self._detect_producer_consumer(cpu_trace, norm))
        problems.append(self._detect_readers_writers(cpu_trace, norm))
        problems.append(self._detect_dining_philosophers(cpu_trace, norm))
        problems.append(self._detect_sleeping_barber(cpu_trace, norm, preemptive))
        # flatten (race_and_cs returns a list)
        flat: list[dict] = []
        for p in problems:
            flat.extend(p) if isinstance(p, list) else flat.append(p)
        problems = flat

        occurred = [p for p in problems if p["occurred"]]

        # ── technique evaluation ──
        contention = self._contention(cpu_trace, norm, preemptive)
        total_cs = self._total_critical_sections(norm)
        evals = [
            self._evaluate_technique(t, occurred, len(norm), base_metrics, contention, total_cs)
            for t in techniques
        ]
        self._score(evals)
        evals.sort(key=lambda e: e["score"], reverse=True)

        recommendation = self._recommend(evals, occurred, sched_algorithm, base_metrics)

        return {
            "scheduler": {
                "algorithm": sched_algorithm,
                "preemptive": preemptive,
                "gantt": gantt,
                "timeline": sched["timeline"],
                "averages": averages,
                "metrics": sched["metrics"],
                "execution_order": self._order(gantt),
            },
            "base_metrics": base_metrics,
            "problems": problems,
            "problems_occurred": [p["id"] for p in occurred],
            "techniques": evals,
            "best": evals[0] if evals else None,
            "recommendation": recommendation,
            "contention": round(contention, 2),
        }

    # ── scheduler helpers ────────────────────────────────────────────────────
    def _expand_gantt(self, gantt: list[dict]) -> list[str | None]:
        """Expand merged Gantt segments into a per-tick list of running PIDs."""
        if not gantt:
            return []
        end = max(seg["end"] for seg in gantt)
        trace: list[str | None] = [None] * end
        for seg in gantt:
            pid = None if seg["pid"] == "IDLE" else seg["pid"]
            for t in range(seg["start"], seg["end"]):
                if 0 <= t < end:
                    trace[t] = pid
        return trace

    def _order(self, gantt: list[dict]) -> list[str]:
        seen: list[str] = []
        for seg in gantt:
            if seg["pid"] != "IDLE" and seg["pid"] not in seen:
                seen.append(seg["pid"])
        return seen

    def _base_metrics(
        self,
        gantt: list[dict],
        procs: list[dict],
        averages: dict,
        sched_metrics: list[dict] | None = None,
    ) -> dict:
        makespan = max((seg["end"] for seg in gantt), default=0)
        busy = sum(seg["end"] - seg["start"] for seg in gantt if seg["pid"] != "IDLE")
        cpu_util = round(100 * busy / makespan, 1) if makespan else 0.0
        # Jain's fairness on waiting times (Silberschatz §6.7):
        # measures whether the scheduler distributed waiting time fairly.
        # Falls back to burst-time uniformity if per-process metrics unavailable.
        if sched_metrics:
            wait_times = [m["waiting"] for m in sched_metrics]
            fairness = self._jain(wait_times)
        else:
            fairness = self._jain([p["burst"] for p in procs])
        return {
            "makespan": makespan,
            "cpu_util": cpu_util,
            "throughput": averages.get("throughput", 0),
            "avg_waiting": averages.get("avg_waiting", 0),
            "avg_turnaround": averages.get("avg_turnaround", 0),
            "avg_response": averages.get("avg_response", 0),
            "fairness": fairness,
        }

    def _rmw_count(self, burst: int) -> int:
        """
        How many read-modify-write (RMW) increments a process performs.

        Approximation: each process performs burst//2 RMW operations on the
        shared counter (half its burst time is "critical section work").
        This proportional mapping means longer processes touch the shared
        resource more, which is realistic for workloads where CS size scales
        with job size.
        """
        return max(1, burst // 2)

    def _total_critical_sections(self, procs: list[dict]) -> int:
        """Total number of critical section entries across all processes (used to model sync overhead)."""
        return sum(self._rmw_count(p["burst"]) for p in procs)

    # ─────────────────────────────────────────────────────────────────────────
    # Detection methods — only race/CS, deadlock, and starvation are derived
    # from real scheduling data.  The other five return _no_problem() stubs
    # with explanations of why they cannot be detected from a generic trace.
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_race_and_cs(self, trace: list[str | None], procs: list[dict]) -> list[dict]:
        """
        Detect race conditions and CS violations from the CPU execution trace.

        Model (educational approximation):
        Each process's "critical section window" spans [first_tick, last_tick]
        across its entire CPU execution.  This is a deliberate simplification:
        in real systems the CS is just the read-modify-write code, not the
        whole burst.  However, this model is directionally correct:

            Non-preemptive (FCFS/SJF/Priority):
                No two processes overlap → no race, no CS violation detected.

            Preemptive (RR/SRTF):
                Processes interleave → windows overlap → races and violations
                are detected, which correctly reflects the increased synchronization
                risk under preemptive scheduling (Silberschatz §6.1).

        Race condition detection:
            Process Pi reads X at first_tick[i].
            Pi writes X + inc[i] at last_tick[i].
            If another process Pj WROTE to X between first_tick[i] and last_tick[i],
            Pi's write uses a stale read value → LOST UPDATE.

        CS violation detection:
            If process Pj's [first_tick, last_tick] window begins while Pi's window
            is still open (open_read[Pi] == True), two processes are "inside the CS"
            simultaneously → MUTUAL EXCLUSION VIOLATED.

        Returns a LIST of two problem dicts: [race_condition, cs_violation].
        """
        inc = {p["pid"]: self._rmw_count(p["burst"]) for p in procs}
        first_tick: dict[str, int] = {}
        last_tick: dict[str, int] = {}
        for t, pid in enumerate(trace):
            if pid is None:
                continue
            first_tick.setdefault(pid, t)
            last_tick[pid] = t

        X = 0
        reg: dict[str, int] = {}
        open_read: dict[str, bool] = {}
        committed = 0
        lost_updates = 0
        overlaps = 0
        race_events: list[str] = []
        cs_events: list[str] = []

        for t, pid in enumerate(trace):
            if pid is None or pid not in inc:
                continue
            # READ at first tick — enter critical section
            if t == first_tick[pid]:
                reg[pid] = X
                open_read[pid] = True
                concurrent = [q for q, o in open_read.items() if o and q != pid]
                if concurrent:
                    overlaps += 1
                    if len(cs_events) < 6:
                        cs_events.append(
                            f"t={t}: {pid} entered the critical section while "
                            f"{concurrent[0]} was still inside"
                        )
            # WRITE at last tick — leave critical section
            if t == last_tick[pid] and open_read.get(pid):
                result = reg[pid] + inc[pid]
                if X != reg[pid]:
                    lost_updates += 1
                    if len(race_events) < 6:
                        race_events.append(
                            f"t={t}: {pid} writes {result} (read X={reg[pid]}) over "
                            f"current X={X} — {X - reg[pid]} update(s) lost"
                        )
                else:
                    committed += 1
                X = result
                open_read[pid] = False

        total_increments = sum(inc.values())
        race_occurred = lost_updates > 0
        cs_occurred = overlaps > 0

        race = {
            "id": "race_condition",
            "name": PROBLEM_META["race_condition"]["name"],
            "category": "sync",
            "occurred": race_occurred,
            "severity": "high" if lost_updates > 1 else ("medium" if race_occurred else "none"),
            "metrics": {
                "Expected counter": total_increments,
                "Actual counter": X,
                "Lost updates": lost_updates,
            },
            "events": race_events,
            "explanation": (
                f"{lost_updates} lost update(s): processes accessed the shared counter "
                f"concurrently without synchronization — the result depends on timing."
                if race_occurred else
                "All read-modify-writes completed without overlap. "
                "No race condition was exposed under this schedule."
            ),
        }
        cs = {
            "id": "cs_violation",
            "name": PROBLEM_META["cs_violation"]["name"],
            "category": "sync",
            "occurred": cs_occurred,
            "severity": "high" if overlaps > 1 else ("medium" if cs_occurred else "none"),
            "metrics": {
                "Overlapping entries": overlaps,
                "Max concurrent in CS": 2 if cs_occurred else 1,
            },
            "events": cs_events,
            "explanation": (
                f"{overlaps} time(s) two processes were inside the critical section "
                f"simultaneously — mutual exclusion was violated because no "
                f"synchronization was protecting the shared resource."
                if cs_occurred else
                "Only one process accessed the critical section at a time. "
                "No violation was exposed under this schedule."
            ),
        }
        return [race, cs]

    def _detect_deadlock(
        self, trace: list[str | None], procs: list[dict], preemptive: bool
    ) -> dict:
        """
        Detect deadlock by overlaying a two-resource hold-and-wait model.

        Reference: Silberschatz §8.3 — Coffman conditions for deadlock.

        Model:
            Process A (procs[0]) acquires R1 on its first operation,
                                  then requests R2 on its last operation.
            Process B (procs[1]) acquires R2 on its first operation,
                                  then requests R1 on its last operation.

        Deadlock occurs when:
            A acquires R1  →  B acquires R2  →  A requests R2 (held by B)  →  BLOCKED
                                               →  B requests R1 (held by A)  →  BLOCKED
            → CIRCULAR WAIT → DEADLOCK (Silberschatz §8.3.1)

        Why preemptive schedules expose deadlock:
        Under FCFS/non-preemptive, A completes (acquires R1, then R2, releases both)
        before B starts — no interleaving, no circular wait.
        Under Round Robin / SRTF, A and B interleave: A may grab R1, B may grab R2
        before either finishes, creating the circular dependency.

        This is academically valid: the model accurately reflects the
        hold-and-wait interleaving that causes real deadlock on multi-resource systems.
        """
        if len(procs) < 2:
            return self._no_problem("deadlock", "Needs at least two processes holding resources.")

        a, b = procs[0]["pid"], procs[1]["pid"]
        prog_len = {p["pid"]: 2 * self._rmw_count(p["burst"]) for p in procs}
        steps = {p["pid"]: 0 for p in procs}
        holds = {a: set(), b: set()}
        # acquisition points: first op -> first resource, last op -> second resource
        first_res = {a: "R1", b: "R2"}
        second_res = {a: "R2", b: "R1"}
        owner = {"R1": None, "R2": None}
        blocked = {a: False, b: False}
        events: list[str] = []

        for t, pid in enumerate(trace):
            if pid not in (a, b):
                continue
            if blocked[pid] or steps[pid] >= prog_len[pid]:
                continue
            steps[pid] += 1
            # acquire first resource on first op
            if steps[pid] == 1:
                r = first_res[pid]
                owner[r] = pid
                holds[pid].add(r)
                if len(events) < 6:
                    events.append(f"t={t}: {pid} acquired {r}")
            # request second resource on last op
            elif steps[pid] == prog_len[pid]:
                r = second_res[pid]
                if owner[r] is None:
                    owner[r] = pid
                    holds[pid].add(r)
                    # release both (finished)
                    for rr in list(holds[pid]):
                        owner[rr] = None
                    holds[pid].clear()
                else:
                    blocked[pid] = True
                    if len(events) < 6:
                        events.append(f"t={t}: {pid} requests {r} held by {owner[r]} — blocks")
            # deadlock check: both blocked, each holding the other's wanted resource
            if blocked[a] and blocked[b]:
                events.append(f"t={t}: circular wait {a}↔{b} — DEADLOCK")
                break

        deadlock = blocked[a] and blocked[b]
        return {
            "id": "deadlock",
            "name": PROBLEM_META["deadlock"]["name"],
            "category": "sync",
            "occurred": deadlock,
            "severity": "high" if deadlock else "none",
            "metrics": {
                "Resources": 2,
                "Blocked processes": 2 if deadlock else 0,
                "Cycle": f"{a}→R2→{b}→R1→{a}" if deadlock else "none",
            },
            "events": events,
            "explanation": (
                f"Circular wait: {a} holds R1 waiting for R2, {b} holds R2 waiting for R1. "
                f"Neither can proceed — deadlock. This was exposed by the interleaving "
                f"of execution without resource-ordering discipline."
                if deadlock else
                "Processes acquired and released resources without a circular wait. "
                "Deadlock was not exposed under this execution order."
            ),
        }

    def _detect_starvation(self, sched: dict, procs: list[dict]) -> dict:
        """
        Detect starvation from real scheduler waiting times.

        Reference: Silberschatz §6.6.

        Starvation: a process is indefinitely (or excessively) delayed because
        the scheduler consistently prefers other processes.  Common in priority
        and SJF scheduling where long or low-priority processes wait much longer
        than their peers.

        Threshold heuristic (finite simulation):
        Real starvation is "indefinite" — impossible to test in a finite run.
        We flag a process as starved if its waiting time exceeds
        max(2 × avg_wait, avg_wait + 1), i.e., it waited more than twice the
        average AND its absolute wait is non-trivial.

        This is a simulation heuristic, not a textbook formula.  It is
        directionally correct: SJF and Priority with unequal bursts will flag
        long processes as starved, while FCFS (which is arrival-order fair)
        will show balanced waiting times.

        Source of waiting times: computed by the scheduler's _build_metrics()
        using WT = TAT − BT = (CT − AT) − BT.  These are REAL computed values,
        not estimates.
        """
        metrics = sched["metrics"]
        if not metrics:
            return self._no_problem("starvation", "No processes to evaluate.")
        waits = [(m["pid"], m["waiting"]) for m in metrics]
        avg = sum(w for _, w in waits) / len(waits)
        max_pid, max_wait = max(waits, key=lambda x: x[1])
        # Flag processes that waited significantly more than their peers.
        # The max(2*avg, avg+1) guard prevents false positives when all
        # waiting times are near-zero (e.g. a 4-process FCFS with all arrivals at 0).
        starved = [
            pid for pid, w in waits
            if w > max(2 * avg, avg + 1) and w >= 2 and len(waits) > 1
        ]
        occurred = bool(starved) and max_wait > avg + 1
        events = [f"{pid} waited {w} ticks (avg {avg:.1f})" for pid, w in waits if pid in starved][:6]
        return {
            "id": "starvation",
            "name": PROBLEM_META["starvation"]["name"],
            "category": "sync",
            "occurred": occurred,
            "severity": "high" if occurred and max_wait > 3 * avg else ("medium" if occurred else "none"),
            "metrics": {
                "Avg waiting": round(avg, 1),
                "Max waiting": max_wait,
                "Starved": ", ".join(starved) if starved else "none",
            },
            "events": events,
            "explanation": (
                f"{', '.join(starved)} waited far longer than average ({max_wait} vs avg "
                f"{avg:.1f}) — the scheduler's preference for shorter/higher-priority "
                f"jobs indefinitely delayed this process."
                if occurred else
                "Waiting times are balanced; no process is starved under this schedule."
            ),
        }

    # ── classic concurrency problems — computed from real trace ─────────────

    def _detect_livelock(
        self, trace: list[str | None], procs: list[dict], preemptive: bool
    ) -> dict:
        """
        Livelock cannot be detected from a CPU scheduling trace.

        Real livelock (Silberschatz §6.6) requires processes to voluntarily yield
        to each other in response to each other's state — an active, state-changing
        cycle with no progress. A CPU scheduler preempting processes is an external
        forced context switch, not a voluntary mutual response. There is no
        mechanism in a generic scheduling simulation where processes detect a
        conflict and retry — which is the defining property of livelock.

        Livelock is demonstrated properly in Phase 3 via a dedicated simulation.
        """
        return self._no_problem(
            "livelock",
            "Livelock requires processes to voluntarily respond to each other's "
            "state in a loop — this cannot be inferred from a CPU scheduling trace. "
            "See Phase 3 for a dedicated livelock demonstration.",
        )

    def _detect_livelock_DISABLED(
        self, trace: list[str | None], procs: list[dict], preemptive: bool
    ) -> dict:
        """Original livelock detection — disabled: was detecting normal RR preemption."""
        if not preemptive or len(procs) < 2:
            return self._no_problem(
                "livelock",
                "Livelock requires preemptive scheduling with concurrent CS access — "
                "not exposed under this non-preemptive schedule.",
            )

        first_tick: dict[str, int] = {}
        last_tick:  dict[str, int] = {}
        for t, pid in enumerate(trace):
            if pid is None:
                continue
            first_tick.setdefault(pid, t)
            last_tick[pid] = t

        alternations = 0
        events: list[str] = []
        prev: str | None = None

        for t, pid in enumerate(trace):
            if pid is None:
                prev = None
                continue
            in_cs = first_tick.get(pid, -1) <= t <= last_tick.get(pid, -1)
            if not in_cs:
                prev = None
                continue
            if prev is not None and prev != pid:
                prev_in_cs = first_tick.get(prev, -1) <= t <= last_tick.get(prev, -1)
                if prev_in_cs:
                    alternations += 1
                    if len(events) < 5:
                        events.append(
                            f"t={t}: CPU switched {prev} → {pid} — "
                            f"both in CS window, neither has finished"
                        )
            prev = pid

        # Livelock requires a sustained cycle of mutual interference:
        # count how many distinct pairs alternate ≥3 times each.
        # A single pair alternating once or twice is normal preemption, not livelock.
        pair_counts: dict[tuple[str, str], int] = {}
        prev2: str | None = None
        for t, pid in enumerate(trace):
            if pid is None:
                prev2 = None
                continue
            in_cs = first_tick.get(pid, -1) <= t <= last_tick.get(pid, -1)
            if not in_cs:
                prev2 = None
                continue
            if prev2 is not None and prev2 != pid:
                prev_in_cs = first_tick.get(prev2, -1) <= t <= last_tick.get(prev2, -1)
                if prev_in_cs:
                    key = (min(prev2, pid), max(prev2, pid))
                    pair_counts[key] = pair_counts.get(key, 0) + 1
            prev2 = pid

        livelock_pairs = {pair: cnt for pair, cnt in pair_counts.items() if cnt >= 3}
        occurred = len(livelock_pairs) > 0

        events = []
        for (pa, pb), cnt in list(livelock_pairs.items())[:3]:
            events.append(
                f"{pa} ↔ {pb} alternated {cnt} time(s) inside overlapping CS windows — "
                f"each preemption leaves the other's CS still open; no progress"
            )

        return {
            "id": "livelock",
            "name": PROBLEM_META["livelock"]["name"],
            "category": "sync",
            "occurred": occurred,
            "severity": "medium" if occurred else "none",
            "metrics": {
                "Alternating pairs": len(livelock_pairs),
                "Max alternations": max(pair_counts.values(), default=0),
                "Progress": 0 if occurred else 1,
            },
            "events": events,
            "explanation": (
                f"{len(livelock_pairs)} process pair(s) alternated inside overlapping CS "
                f"windows 3+ times — each preemption hands control to the other process "
                f"while both CS windows are still open. Neither makes progress: livelock."
                if occurred else
                "No sustained mutual interference detected. Processes completed their "
                "CS windows without repeatedly yielding to each other."
            ),
        }

    def _detect_producer_consumer(
        self, trace: list[str | None], procs: list[dict]
    ) -> dict:
        """
        Producer-Consumer cannot be reliably detected from a generic scheduling trace.

        The bounded-buffer problem (Silberschatz §6.4) requires processes to have
        explicit producer/consumer roles and a shared bounded buffer. A generic CPU
        scheduling trace has no such role information — splitting processes into
        "first half = producers" is methodologically arbitrary and produces results
        that are an artifact of scheduling order, not of buffer coordination failures.
        The problem is correctly demonstrated in Phase 3 via the dedicated simulation.
        """
        return self._no_problem(
            "producer_consumer",
            "Requires explicit producer/consumer role designation — cannot be inferred "
            "from a generic CPU scheduling trace. See Phase 3 Producer–Consumer simulation.",
        )

    def _detect_readers_writers(
        self, trace: list[str | None], procs: list[dict]
    ) -> dict:
        """
        Readers-Writers cannot be reliably detected from a generic scheduling trace.

        The readers-writers problem (Silberschatz §6.4) requires processes to have
        explicit read/write intent on shared data. Assigning roles by index parity
        (even=reader, odd=writer) is arbitrary and produces results that depend on
        input order, not actual data-access patterns. Demonstrated in Phase 3.
        """
        return self._no_problem(
            "readers_writers",
            "Requires explicit reader/writer role designation — cannot be inferred "
            "from a generic CPU scheduling trace. See Phase 3 Readers–Writers simulation.",
        )

    def _detect_dining_philosophers(
        self, trace: list[str | None], procs: list[dict]
    ) -> dict:
        """
        Dining Philosophers cannot be reliably detected from a generic scheduling trace.

        The dining philosophers problem (Dijkstra 1965; Silberschatz §7.1.3) requires
        a ring-topology of 5 processes sharing fork resources with explicit acquisition
        protocol. Inferring fork acquisition from CPU burst timing has no academic
        basis — a process with burst=8 and one with burst=2 behave differently only
        because of their burst lengths, not because of resource contention topology.
        Demonstrated in Phase 3.
        """
        return self._no_problem(
            "dining_philosophers",
            "Requires explicit fork-acquisition protocol in a ring topology — cannot "
            "be inferred from a CPU scheduling trace. See Phase 3 for demonstrations.",
        )

    def _detect_sleeping_barber(
        self, trace: list[str | None], procs: list[dict], preemptive: bool
    ) -> dict:
        """
        Sleeping Barber cannot be reliably detected from a generic scheduling trace.

        The sleeping barber problem (Tanenbaum §2.5.4) models an I/O service system
        where a server (barber) sleeps when idle and customers signal via semaphores.
        CPU scheduling traces contain no information about service-queue semantics,
        wakeup signals, or barber/customer roles. Treating procs[0] as a barber and
        using its appearance in the Gantt chart as a "wakeup" has no textbook basis.
        Demonstrated in Phase 3.
        """
        return self._no_problem(
            "sleeping_barber",
            "Models I/O service queues with semaphore-based wakeup — not applicable "
            "to a CPU scheduling trace. See Phase 3 for demonstrations.",
        )

    def _no_problem(self, pid: str, why: str) -> dict:
        """Return a standard 'not detected / not applicable' result dict."""
        return {
            "id":          pid,
            "name":        PROBLEM_META[pid]["name"],
            "category":    PROBLEM_META[pid]["category"],
            "occurred":    False,
            "severity":    "none",
            "metrics":     {},
            "events":      [],
            "explanation": why,
        }

    # ── technique evaluation ──────────────────────────────────────────────────

    def _contention(self, trace: list[str | None], procs: list[dict], preemptive: bool) -> float:
        """
        Compute a contention score [0.0 – 1.0] from the CPU trace.

        Combines two signals:
          - base: fraction of n processes that could compete (n-1)/n
          - switch_factor: actual context-switch density in the trace

        Higher contention → higher synchronization overhead model.
        Preemptive algorithms get a +0.1 bonus because frequent preemption
        means processes are more likely to be interrupted mid-CS.
        """
        n    = len(procs)
        base = (n - 1) / n if n else 0.0
        # Count ticks where the running PID changed (context switches)
        switches = sum(
            1 for i in range(1, len(trace))
            if trace[i] is not None and trace[i] != trace[i - 1] and trace[i - 1] is not None
        )
        switch_factor = min(1.0, switches / max(len(trace), 1) * 2)
        c = 0.4 * base + 0.6 * switch_factor
        return max(0.1, min(1.0, c + (0.1 if preemptive else 0.0)))

    def _evaluate_technique(
        self,
        technique: str,
        occurred: list[dict],
        n_processes: int,
        base: dict,
        contention: float,
        total_cs: int,
    ) -> dict:
        """
        Analytically model a technique's performance against the detected problems.

        Three dimensions:
          1. Prevention ratio — fraction of detected problems the technique can address
             (from the _capability() matrix; "prevents"=1, "partial"=0.5, "no"=0)
          2. Overhead model  — estimated extra ticks added by lock operations
             base_overhead   = meta["ovh"] × total_cs  (lock/unlock cost per CS entry)
             busy_penalty    = contention × cs × 2     (CPU time wasted by busy-waiting)
             concurrency_relief = cs × 0.5             (counting semaphore concurrent slots)
          3. Performance metrics — throughput, avg_waiting, cpu_util derived from overhead

        Note: these are ANALYTICAL ESTIMATES, not measured from a real lock run.
        They are used in Phase 2 to rank techniques BEFORE Phase 3 runs real simulations.
        Phase 3 replace them with actual measured values from SyncSimulator.
        """
        meta = TECHNIQUE_META[technique]

        # 1) capability against the problems that actually occurred
        prevented, partial, not_prevented = [], [], []
        for prob in occurred:
            cap = _capability(technique, prob["id"], n_processes)
            if cap == "prevents":
                prevented.append(prob["id"])
            elif cap == "partial":
                partial.append(prob["id"])
            else:
                not_prevented.append(prob["id"])
        denom = len(occurred) or 1
        prevention_ratio = (len(prevented) + 0.5 * len(partial)) / denom

        # 2) overhead model (ticks added by lock operations)
        base_overhead = meta["ovh"] * total_cs
        busy_penalty = (contention * total_cs * 2.0) if meta["busy_wait"] else 0.0
        # counting semaphore recovers some cost via concurrency
        concurrency_relief = (total_cs * 0.5) if meta["concurrency"] > 1 else 0.0
        overhead = max(0.0, base_overhead + busy_penalty - concurrency_relief)

        makespan = base["makespan"] + overhead
        work = base["makespan"] * (base["cpu_util"] / 100.0) or base["makespan"]

        # 3) performance metrics
        throughput = round(n_processes / makespan, 4) if makespan else 0.0
        # waiting: blocking frees the CPU (cheaper); busy-wait inflates waiting
        wait_factor = 1.0 if meta["blocks"] else (1.0 + 0.8 * contention)
        added_wait = (overhead / n_processes) * wait_factor if n_processes else 0.0
        avg_waiting = round(base["avg_waiting"] + added_wait, 2)
        avg_turnaround = round(base["avg_turnaround"] + added_wait, 2)
        avg_response = round(
            base["avg_response"] + (added_wait * (0.3 if meta["blocks"] else 0.8)), 2
        )
        # effective CPU utilisation: busy-wait wastes cycles
        useful = work
        wasted = busy_penalty
        cpu_util = round(100 * useful / (useful + wasted + overhead - base_overhead + 1e-9), 1)
        cpu_util = max(10.0, min(100.0, cpu_util * meta["cpu_efficiency"] + (1 - meta["cpu_efficiency"]) * 0))
        cpu_util = round(min(cpu_util, base["cpu_util"]), 1)
        # fairness: profile, reduced if a two-process-only primitive is overloaded
        fairness = meta["fairness"]
        if meta["two_proc_only"] and n_processes > 2:
            fairness *= 0.5
        fairness = round(fairness, 2)

        return {
            "technique": technique,
            "name": meta["name"],
            "desc": meta["desc"],
            "prevented": prevented,
            "partial": partial,
            "not_prevented": not_prevented,
            "prevention_ratio": round(prevention_ratio, 3),
            "metrics": {
                "throughput": throughput,
                "avg_waiting": avg_waiting,
                "avg_response": avg_response,
                "avg_turnaround": avg_turnaround,
                "cpu_util": cpu_util,
                "fairness": fairness,
                "overhead": round(overhead, 1),
            },
            "_raw": {  # used for score normalisation, stripped afterwards
                "throughput": throughput,
                "avg_waiting": avg_waiting,
                "fairness": fairness,
                "overhead": overhead,
                "prevention_ratio": prevention_ratio,
            },
        }

    def _score(self, evals: list[dict]) -> None:
        """
        Score technique evaluations using min-max normalisation across the group.

        Each metric is normalised to [0, 1] relative to the best and worst in
        the current comparison set, then combined with fixed weights:
            40% prevention ratio  — does it stop the detected problems?
            15% throughput        — higher is better
            15% avg waiting       — lower is better (inverted)
            15% fairness          — higher is better
            15% overhead          — lower is better (inverted)

        The _raw dict is removed after scoring to keep the API response clean.
        """
        def col(key: str) -> list[float]:
            return [e["_raw"][key] for e in evals]

        def norm(v: float, lo: float, hi: float, invert: bool = False) -> float:
            if hi - lo < 1e-9:
                base = 1.0
            else:
                base = (v - lo) / (hi - lo)
            return 1 - base if invert else base

        tp, wt = col("throughput"), col("avg_waiting")
        fr, ov = col("fairness"), col("overhead")
        pr = col("prevention_ratio")

        for e in evals:
            r = e["_raw"]
            score = (
                0.40 * r["prevention_ratio"]
                + 0.15 * norm(r["throughput"], min(tp), max(tp))
                + 0.15 * norm(r["avg_waiting"], min(wt), max(wt), invert=True)
                + 0.15 * norm(r["fairness"], min(fr), max(fr))
                + 0.15 * norm(r["overhead"], min(ov), max(ov), invert=True)
            )
            e["score"] = round(100 * score, 1)
            del e["_raw"]

    def _recommend(
        self, evals: list[dict], occurred: list[dict], sched: str, base: dict
    ) -> dict:
        """
        Generate the Phase 2 recommendation text from the ranked technique list.

        Produces a one-paragraph summary and a bullet list suitable for the
        Phase 4 report.  The best technique (evals[0]) and runner-up (evals[1])
        are highlighted.  The text explicitly states that the scheduler exposes
        problems but does not cause them — reinforcing the methodology.
        """
        if not evals:
            return {"summary": "No techniques evaluated.", "bullets": []}
        best = evals[0]
        prob_names = [p["name"] for p in occurred]
        prevented_names = [PROBLEM_META[p]["name"] for p in best["prevented"]]

        summary = (
            f"Running the workload under {sched.upper().replace('_', ' ')} without "
            f"synchronization exposed {len(occurred)} problem(s): "
            f"{', '.join(prob_names) or 'none'}. "
            f"These arise from concurrent unsynchronized access to shared resources — "
            f"not from the scheduler itself. "
            f"{best['name']} is the most effective synchronization technique "
            f"(score {best['score']}/100), preventing {len(best['prevented'])} of them."
        )
        bullets = [
            f"Best synchronization technique: {best['name']} — "
            f"prevents {', '.join(prevented_names) or 'the detected issues'}.",
            f"Performance: throughput {best['metrics']['throughput']}, "
            f"avg waiting {best['metrics']['avg_waiting']}, "
            f"fairness {best['metrics']['fairness']}, "
            f"overhead {best['metrics']['overhead']} ticks.",
            (
                f"{best['name']} blocks waiters in a queue rather than busy-waiting, "
                f"so the CPU is free to run other processes while a lock is held."
                if not TECHNIQUE_META[best["technique"]]["busy_wait"]
                else f"{best['name']} uses busy-waiting — efficient for very short "
                     f"critical sections but wastes CPU cycles under high contention."
            ),
            f"Synchronization protects the critical section — the code that accesses "
            f"shared resources — ensuring at most one process enters at a time.",
        ]
        runner = evals[1] if len(evals) > 1 else None
        if runner:
            bullets.append(
                f"Runner-up: {runner['name']} (score {runner['score']}/100) — "
                f"a solid alternative if {best['name']} cannot be used."
            )
        return {"summary": summary, "bullets": bullets, "best_technique": best["technique"]}

    # ── math ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _jain(values: list[float]) -> float:
        """
        Jain's Fairness Index — measures how evenly values are distributed.

        Formula (Jain 1984):  J = (Σ xᵢ)² / (n · Σ xᵢ²)

        Range: (0, 1].  J = 1.0 means all values are equal (perfectly fair).
        J → 0 means one value dominates all others (maximally unfair).

        Applied here to WAITING TIMES:
            J = 1.0 → every process waited the same amount.
            J < 1.0 → some processes waited much longer than others.

        FCFS example (P1 burst=8, P2 burst=3, P3 burst=5, P4 burst=2):
            WT = [0, 8, 11, 16] → highly unequal → J ≈ 0.71
        Round Robin (same processes):
            WT values are more balanced → J ≈ 0.90

        Edge case: if all values are zero (no waiting), sq=0 → return 1.0
        (all processes waited equally, i.e. zero — perfectly fair).
        """
        vals = [v for v in values if v is not None]
        if not vals:
            return 1.0
        s  = sum(vals)
        sq = sum(v * v for v in vals)
        n  = len(vals)
        if sq == 0:
            return 1.0   # all values are zero → perfectly equal
        return round((s * s) / (n * sq), 2)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level accessors (used by Flask routes)
# ─────────────────────────────────────────────────────────────────────────────

def list_techniques() -> list[dict[str, str]]:
    """Return all synchronization technique profiles (id, name, description)."""
    return [
        {"id": k, "name": v["name"], "description": v["desc"]}
        for k, v in TECHNIQUE_META.items()
    ]


def list_problems() -> list[dict[str, str]]:
    """Return all problem descriptors (id, name, category) from PROBLEM_META."""
    return [
        {"id": k, "name": v["name"], "category": v["category"]}
        for k, v in PROBLEM_META.items()
    ]
