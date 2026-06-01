"""
Diagnostics engine — shows which synchronization problems arise from concurrent
unsynchronized access, and how each synchronization technique resolves them.

Design (OS-rigorous, single CPU):
    Scheduling itself does NOT directly create synchronization problems.
    It determines which process runs next and controls preemption points.
    Synchronization problems arise because processes share resources WITHOUT
    proper synchronization — scheduling only exposes them by interleaving:

      * FCFS / non-preemptive  -> contiguous execution -> few interleaving
                                  opportunities -> problems less likely to surface
      * Round Robin / SRTF     -> frequent preemption -> processes interleave
                                  mid critical-section -> problems surface clearly

    Race condition: concurrent read-modify-write without synchronization;
    final result depends on timing.
    Critical section violation: more than one process inside the critical
    section at the same time.
    Deadlock: circular wait — each process holds a resource the other needs.
    Starvation: a process is indefinitely delayed by the scheduler.

    We replay a shared-resource workload over the Gantt trace without any
    synchronization to surface these problems, then evaluate each technique.
"""

from __future__ import annotations

from typing import Any

from .scheduler import CPUScheduler


# ─────────────────────────────────────────────────────────────────────────────
#  Problem catalogue
# ─────────────────────────────────────────────────────────────────────────────

PROBLEM_META: dict[str, dict[str, str]] = {
    "race_condition":      {"name": "Race Condition",          "category": "schedule"},
    "cs_violation":        {"name": "Critical Section Violation", "category": "schedule"},
    "deadlock":            {"name": "Deadlock",                "category": "schedule"},
    "starvation":          {"name": "Starvation",             "category": "schedule"},
    "livelock":            {"name": "Livelock",               "category": "classic"},
    "producer_consumer":   {"name": "Producer–Consumer",      "category": "classic"},
    "readers_writers":     {"name": "Readers–Writers Conflict", "category": "classic"},
    "dining_philosophers": {"name": "Dining Philosophers",    "category": "classic"},
    "sleeping_barber":     {"name": "Sleeping Barber",        "category": "classic"},
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

    Grounded in OS theory:
      * Mutual exclusion (race / CS violation) — any real lock prevents it,
        but Peterson is limited to two processes.
      * Deadlock / starvation — need a fair queue and/or ordering discipline;
        busy-wait primitives (spinlock, Peterson) fall short.
      * Ordering problems (producer-consumer, readers-writers, dining, barber)
        — need signalling / counting; a bare mutex only partially helps and
        busy-wait primitives cannot express condition waiting.
    """
    t = TECHNIQUE_META[technique]
    blocks   = t["blocks"]
    signals  = t["signaling"]
    counting = t["concurrency"] > 1
    two_only = t["two_proc_only"]
    busy     = t["busy_wait"]

    # Mutual-exclusion problems
    if problem in ("race_condition", "cs_violation"):
        if two_only and n_processes > 2:
            return "no"          # Peterson can't scale past 2 processes
        return "prevents"        # every lock enforces mutual exclusion

    if problem == "deadlock":
        if technique in ("monitor", "condition_variable"):
            return "prevents"    # structured encapsulation enforces ordering discipline
        if technique in ("mutex", "counting_semaphore"):
            # A mutex/semaphore alone does NOT prevent deadlock — two mutexes
            # acquired in opposite order by two threads still deadlock (ABBA
            # pattern). Prevention requires ordered acquisition enforced by the
            # programmer, not by the primitive itself.
            return "partial"
        if technique == "binary_semaphore":
            return "partial"     # same reasoning — discipline required
        return "no"              # spinlock / Peterson don't address 2-resource wait

    if problem == "starvation":
        if busy and not blocks:
            return "no"          # no fair wait queue -> can starve
        if two_only and n_processes > 2:
            return "no"
        return "prevents"        # FIFO blocking queue bounds waiting

    if problem == "livelock":
        return "prevents" if blocks else "no"   # blocking avoids symmetric retry

    if problem == "producer_consumer":
        if counting or (signals and blocks):
            return "prevents"
        if technique == "mutex":
            return "partial"     # protects buffer but can't block on full/empty
        return "no"

    if problem == "readers_writers":
        if counting or technique in ("monitor", "condition_variable"):
            return "prevents"
        if technique in ("mutex", "binary_semaphore"):
            return "partial"     # correct but serialises readers (no concurrency)
        return "no"

    if problem == "dining_philosophers":
        if technique in ("monitor", "condition_variable", "counting_semaphore", "mutex"):
            return "prevents"
        if technique == "binary_semaphore":
            return "partial"
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
        base_metrics = self._base_metrics(gantt, norm, averages)

        # ── detection (unsynchronized baseline) ──
        problems = []
        problems.append(self._detect_race_and_cs(cpu_trace, norm))     # 2 entries
        problems.append(self._detect_deadlock(cpu_trace, norm, preemptive))
        problems.append(self._detect_starvation(sched, norm))
        problems.extend(self._classic_problems())
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

    def _base_metrics(self, gantt: list[dict], procs: list[dict], averages: dict) -> dict:
        makespan = max((seg["end"] for seg in gantt), default=0)
        busy = sum(seg["end"] - seg["start"] for seg in gantt if seg["pid"] != "IDLE")
        cpu_util = round(100 * busy / makespan, 1) if makespan else 0.0
        return {
            "makespan": makespan,
            "cpu_util": cpu_util,
            "throughput": averages.get("throughput", 0),
            "avg_waiting": averages.get("avg_waiting", 0),
            "avg_turnaround": averages.get("avg_turnaround", 0),
            "avg_response": averages.get("avg_response", 0),
            "fairness": self._jain([p["burst"] for p in procs]),
        }

    def _rmw_count(self, burst: int) -> int:
        """How many read-modify-write increments a process performs."""
        return max(1, burst // 2)

    def _total_critical_sections(self, procs: list[dict]) -> int:
        return sum(self._rmw_count(p["burst"]) for p in procs)

    # ── schedule-driven detection ────────────────────────────────────────────
    def _detect_race_and_cs(self, trace: list[str | None], procs: list[dict]) -> list[dict]:
        """
        Replay an unsynchronized shared-accumulator workload over the CPU trace.

        Each process performs a read-modify-write: it READS the shared counter at
        its first CPU tick, works during its burst, and WRITES (read_value +
        its increments) at its last CPU tick. The read→write window is its
        critical section. If another process WRITES inside that window, the first
        process overwrites with a stale value -> LOST UPDATE (race condition).
        Two processes whose windows overlap -> CRITICAL SECTION VIOLATION.

        Because the window spans the whole burst, ANY preemption that lets another
        process run in between triggers the race — so the effect tracks the
        scheduler's preemption behaviour, not the quantum size.
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
            "category": "schedule",
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
            "category": "schedule",
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
        Overlay a two-resource hold-and-wait scenario on the first two processes.

        A acquires R1 (first RMW) then needs R2 (last op); B acquires R2 then
        needs R1. If the schedule interleaves them so both grab their first
        resource before either gets the second -> circular wait -> deadlock.
        Contiguous (non-preemptive) execution lets the first finish and release,
        so no deadlock.
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
            "category": "schedule",
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
        """A process starves if its waiting time is far above the average."""
        metrics = sched["metrics"]
        if not metrics:
            return self._no_problem("starvation", "No processes to evaluate.")
        waits = [(m["pid"], m["waiting"]) for m in metrics]
        avg = sum(w for _, w in waits) / len(waits)
        max_pid, max_wait = max(waits, key=lambda x: x[1])
        # starvation: clearly worse than peers and non-trivial
        starved = [
            pid for pid, w in waits
            if w > max(2 * avg, avg + 1) and w >= 2 and len(waits) > 1
        ]
        occurred = bool(starved) and max_wait > avg + 1
        events = [f"{pid} waited {w} ticks (avg {avg:.1f})" for pid, w in waits if pid in starved][:6]
        return {
            "id": "starvation",
            "name": PROBLEM_META["starvation"]["name"],
            "category": "schedule",
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

    # ── classic concurrency scenarios (canonical demonstrations) ─────────────
    def _classic_problems(self) -> list[dict]:
        return [
            {
                "id": "livelock", "name": PROBLEM_META["livelock"]["name"], "category": "classic",
                "occurred": True, "severity": "medium",
                "metrics": {"Retries": 8, "Progress": 0},
                "events": [
                    "Both threads detect a conflict and back off simultaneously",
                    "Both retry at the same time — conflict again",
                    "Processes keep changing state but neither makes progress",
                ],
                "explanation": "Livelock: processes continuously respond to each other "
                               "by backing off and retrying. They are not blocked (unlike "
                               "deadlock) but make no progress — active yet stuck.",
            },
            {
                "id": "producer_consumer", "name": PROBLEM_META["producer_consumer"]["name"], "category": "classic",
                "occurred": True, "severity": "high",
                "metrics": {"Buffer size": 5, "Overflow": 2, "Underflow": 1},
                "events": [
                    "Producer writes to a full buffer — item overwritten (overflow)",
                    "Consumer reads from an empty buffer — invalid data (underflow)",
                    "No semaphore counting empty/full slots to gate access",
                ],
                "explanation": "Producer-Consumer problem: a producer adds data to a "
                               "bounded buffer and a consumer removes it. Without counting "
                               "semaphores for empty and full slots, overflow and underflow "
                               "occur, corrupting shared data.",
            },
            {
                "id": "readers_writers", "name": PROBLEM_META["readers_writers"]["name"], "category": "classic",
                "occurred": True, "severity": "high",
                "metrics": {"Readers": 3, "Writers": 2, "Conflicts": 3},
                "events": [
                    "Writer modifies shared data while readers are still reading",
                    "Readers observe a partially-written, inconsistent value",
                    "No write-lock to exclude readers during a write",
                ],
                "explanation": "Readers-Writers problem: multiple readers may read "
                               "concurrently, but a writer needs exclusive access. Without "
                               "synchronization a writer can corrupt data that readers are "
                               "actively reading.",
            },
            {
                "id": "dining_philosophers", "name": PROBLEM_META["dining_philosophers"]["name"], "category": "classic",
                "occurred": True, "severity": "high",
                "metrics": {"Philosophers": 5, "Forks held": 5, "Eating": 0},
                "events": [
                    "All 5 philosophers pick up their left fork simultaneously",
                    "Each waits for the right fork — held by their neighbour",
                    "Circular wait around the table — deadlock, no one eats",
                ],
                "explanation": "Dining Philosophers: each philosopher holds one fork and "
                               "waits for the other. This creates a circular wait — a "
                               "classic deadlock scenario where no process can proceed.",
            },
            {
                "id": "sleeping_barber", "name": PROBLEM_META["sleeping_barber"]["name"], "category": "classic",
                "occurred": True, "severity": "medium",
                "metrics": {"Chairs": 3, "Customers lost": 4, "Missed wakeups": 2},
                "events": [
                    "Customer arrives while barber is asleep — no signal sent",
                    "Barber misses the customer; customer leaves (lost wakeup)",
                    "Race on chair count: customer sees full chairs due to bad timing",
                ],
                "explanation": "Sleeping Barber: the barber sleeps when there are no "
                               "customers; customers wake the barber or wait in chairs. "
                               "Without proper signalling, wakeups are lost and customers "
                               "are dropped.",
            },
        ]

    def _no_problem(self, pid: str, why: str) -> dict:
        return {
            "id": pid, "name": PROBLEM_META[pid]["name"],
            "category": PROBLEM_META[pid]["category"],
            "occurred": False, "severity": "none",
            "metrics": {}, "events": [], "explanation": why,
        }

    # ── technique evaluation ─────────────────────────────────────────────────
    def _contention(self, trace: list[str | None], procs: list[dict], preemptive: bool) -> float:
        """0..1 — how much processes compete (drives overhead)."""
        n = len(procs)
        base = (n - 1) / n if n else 0.0
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
        """Min-max normalise across techniques, then weighted composite 0..100."""
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
        """Jain's fairness index (1.0 = perfectly fair)."""
        vals = [v for v in values if v is not None]
        if not vals:
            return 1.0
        s = sum(vals)
        sq = sum(v * v for v in vals)
        n = len(vals)
        if sq == 0:
            return 1.0
        return round((s * s) / (n * sq), 2)


def list_techniques() -> list[dict[str, str]]:
    return [
        {"id": k, "name": v["name"], "description": v["desc"]}
        for k, v in TECHNIQUE_META.items()
    ]


def list_problems() -> list[dict[str, str]]:
    return [
        {"id": k, "name": v["name"], "category": v["category"]}
        for k, v in PROBLEM_META.items()
    ]
