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

Problem scope — GENERIC synchronization problems only
------------------------------------------------------
This simulator covers the five problems that arise naturally in any
concurrent system: race condition, critical section problem, mutual
exclusion violation, deadlock, and starvation (indefinite blocking).
Role-based textbook models
(producer-consumer, readers-writers, dining philosophers, sleeping barber)
and scheduling-specific effects (convoy effect, priority inversion) are
intentionally out of scope.

What CAN be detected from a scheduling trace
--------------------------------------------
    Race condition      — overlapping read-modify-write windows (model approximation)
    Critical section    — concurrent contention for the shared resource with no entry protocol
    Mutual exclusion    — two processes simultaneously inside the CS; "what if no lock existed"
    Deadlock            — hold-and-wait on two resources for the first two processes
    Starvation          — a process waits far longer than its peers

Spin-based lock penalties (busy waiting) are still modelled analytically
in the technique evaluation — blocking primitives score higher because
they free the CPU while waiters sleep.

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
    # Race condition, CS problem and ME violation: derived from interleaving of
    # execution windows; directionally correct — preemptive schedules expose more overlap.
    "race_condition":   {"name": "Race Condition",              "category": "sync"},
    # Critical section problem: ≥2 processes contend for the shared resource
    # with no entry protocol (Silberschatz §6.2 — the structural problem).
    "critical_section": {"name": "Critical Section Problem",    "category": "sync"},
    # Mutual exclusion violation: ≥2 processes simultaneously INSIDE the CS
    # (the observable consequence of the unsolved CS problem).
    "mutual_exclusion": {"name": "Mutual Exclusion Violation",  "category": "sync"},
    # Deadlock: hold-and-wait on 2 resources modelled over the first 2 processes
    # (Silberschatz §8.3 — circular wait). Category is sync, not scheduling.
    "deadlock":         {"name": "Deadlock",                    "category": "sync"},
    # Starvation: process waits far longer than peers — computed from real WT
    # values produced by the scheduler (Silberschatz §6.6).
    "starvation":       {"name": "Starvation (Indefinite Blocking)", "category": "sync"},
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
    """
    t = TECHNIQUE_META[technique]
    blocks   = t["blocks"]
    signals  = t["signaling"]
    counting = t["concurrency"] > 1
    two_only = t["two_proc_only"]
    busy     = t["busy_wait"]
    structured = t["structured"]

    # ── Mutual-exclusion problems ─────────────────────────────────────────────
    # Race condition, the critical-section problem and ME violations are all
    # solved by any CORRECT lock protocol (Silberschatz §6.1-6.2).
    if problem in ("race_condition", "critical_section", "mutual_exclusion"):
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
        problems.append(self._detect_race_and_cs(cpu_trace, norm))     # 3 entries
        problems.append(self._detect_deadlock(cpu_trace, norm, preemptive))
        problems.append(self._detect_starvation(sched, norm))
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
    # Detection methods — race condition, critical section problem, mutual
    # exclusion violation, deadlock, and starvation derived from real
    # scheduling data.
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_race_and_cs(self, trace: list[str | None], procs: list[dict]) -> list[dict]:
        """
        Detect the race condition, critical section problem, and mutual
        exclusion violation from the CPU execution trace.

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

        Critical section problem detection (Silberschatz §6.2):
            If two processes' CS windows OVERLAP in time, they are contending
            for the same shared resource with no entry protocol — the
            critical-section problem has arisen (structural cause).

        Mutual exclusion violation detection:
            If process Pj's [first_tick, last_tick] window begins while Pi's window
            is still open (open_read[Pi] == True), two processes are "inside the CS"
            simultaneously → MUTUAL EXCLUSION VIOLATED (observable consequence).

        Returns a LIST of three problem dicts:
            [race_condition, critical_section, mutual_exclusion].
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
        me_occurred = overlaps > 0

        # ── Critical section problem: do any two CS windows overlap in time? ──
        # This is the STRUCTURAL problem (contention without an entry protocol);
        # the ME violation below is its observable consequence.
        pids = list(first_tick.keys())
        contending_pairs: list[str] = []
        overlap_ticks = 0
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                a, b = pids[i], pids[j]
                lo = max(first_tick[a], first_tick[b])
                hi = min(last_tick[a], last_tick[b])
                if lo <= hi:
                    contending_pairs.append(f"{a}↔{b}")
                    overlap_ticks += hi - lo + 1
        cs_occurred = len(contending_pairs) > 0

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
        cs_problem = {
            "id": "critical_section",
            "name": PROBLEM_META["critical_section"]["name"],
            "category": "sync",
            "occurred": cs_occurred,
            "severity": "high" if len(contending_pairs) > 1 else ("medium" if cs_occurred else "none"),
            "metrics": {
                "Contending pairs": len(contending_pairs),
                "Overlap ticks": overlap_ticks,
                "Pairs": ", ".join(contending_pairs[:4]) if contending_pairs else "none",
            },
            "events": [
                f"{pair}: critical-section windows overlap — both need an entry protocol"
                for pair in contending_pairs[:6]
            ],
            "explanation": (
                f"{len(contending_pairs)} process pair(s) contend for the same shared "
                f"resource with NO entry protocol (no mutual exclusion, progress, or "
                f"bounded-waiting guarantee) — the critical-section problem has arisen."
                if cs_occurred else
                "Process execution windows never overlapped — no contention for the "
                "shared resource arose under this schedule."
            ),
        }
        me_violation = {
            "id": "mutual_exclusion",
            "name": PROBLEM_META["mutual_exclusion"]["name"],
            "category": "sync",
            "occurred": me_occurred,
            "severity": "high" if overlaps > 1 else ("medium" if me_occurred else "none"),
            "metrics": {
                "Overlapping entries": overlaps,
                "Max concurrent in CS": 2 if me_occurred else 1,
            },
            "events": cs_events,
            "explanation": (
                f"{overlaps} time(s) two processes were inside the critical section "
                f"simultaneously — mutual exclusion was violated because no "
                f"synchronization was protecting the shared resource."
                if me_occurred else
                "Only one process accessed the critical section at a time. "
                "No violation was exposed under this schedule."
            ),
        }
        return [race, cs_problem, me_violation]

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

    def _no_problem(self, pid: str, why: str) -> dict:
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
