"""
execution_engine.py — The Simulation Pipeline (Phase 1 → Phase 2/3)
=====================================================================

This module wires Phase 1 (CPU scheduling) to Phase 2/3 (synchronization)
into a single coherent pipeline that the Flask API routes call.

Pipeline overview
-----------------
    Phase 1 — run_phase_scheduling_multi()
        Runs one or more scheduling algorithms on the process table.
        Identifies the PRIMARY algorithm (lowest average waiting time).
        Produces Gantt charts, per-process metrics, and execution order.

    Phase 2/3 — run_phase_synchronization_multi()
        Takes the Phase 1 result as input (same processes, same schedule).
        For each selected sync algorithm:
            1. Runs the SyncSimulator to get synchronization steps.
            2. Remaps generic process IDs (P0, P1, …) to real PIDs
               in the order determined by Phase 1's Gantt chart.
            3. Interleaves the CPU schedule events with sync events into
               a unified timeline that the frontend plays back step-by-step.
        Runs AnalysisEngine.analyze_sync() to score and rank the techniques.

Methodological note
-------------------
The Phase 1 schedule is the INDEPENDENT VARIABLE — it determines the order
and timing of CPU execution.  The Phase 2/3 synchronization happens DURING
those CPU slices.  Each process's sync steps are bound to its CPU time slice,
so the timeline faithfully represents "P3 is on the CPU, and during P3's
slice it acquires the mutex / enters the CS / etc."

This makes the connection between scheduling interleaving and synchronization
behaviour explicit and traceable in the step-by-step playback.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .scheduler  import CPUScheduler
from .sync_engine import SyncSimulator


class ExecutionEngine:
    """
    Orchestrates the Phase 1 → Phase 2/3 simulation pipeline.

    Holds one CPUScheduler and one SyncSimulator instance; both are
    stateless after construction so they can be reused across requests.
    """

    def __init__(self) -> None:
        self.scheduler = CPUScheduler()
        self.sync      = SyncSimulator()

    def run_phase_scheduling(
        self, sched_algorithm: str, processes: list[dict], quantum: int = 2
    ) -> dict[str, Any]:
        """Single-algorithm convenience wrapper — delegates to the multi version."""
        return self.run_phase_scheduling_multi([sched_algorithm], processes, quantum)

    def run_phase_scheduling_multi(
        self, sched_algorithms: list[str], processes: list[dict], quantum: int = 2
    ) -> dict[str, Any]:
        """
        Phase 1: run one or more scheduling algorithms and identify the primary.

        Steps:
        1. Run each selected algorithm on the process table to get a Gantt chart
           and per-process metrics (CT, TAT, WT, RT).
        2. Select the PRIMARY algorithm: the one with the lowest average waiting
           time.  This algorithm drives all subsequent phases.
        3. Extract the execution order: the order in which PIDs first appear in
           the primary Gantt chart.  This order is used by Phase 2/3 to map
           generic sync process IDs (P0, P1, …) to real process PIDs.

        Returns a Phase 1 result dict consumed by Phase 2/3.
        """
        if not sched_algorithms:
            raise ValueError("Select at least one scheduling algorithm")

        # Run every selected algorithm independently on the same process table
        comparisons: dict[str, Any] = {}
        for algo in sched_algorithms:
            comparisons[algo] = self.scheduler.run(algo, processes, quantum)

        # Primary = algorithm with lowest average waiting time (Silberschatz §6.1)
        primary = min(
            sched_algorithms,
            key=lambda a: comparisons[a].get("averages", {}).get("avg_waiting", 9999),
        )
        primary_result = comparisons[primary]
        # Execution order: first appearance of each PID in the primary Gantt chart
        order = self._execution_order(primary_result["gantt"], processes)

        return {
            "phase":             1,
            "complete":          True,
            "sched_algorithms":  sched_algorithms,
            "comparisons":       comparisons,      # all algorithms' full results
            "scheduling":        primary_result,   # primary algorithm's result
            "primary_algorithm": primary,
            "execution_order":   order,            # PID order for Phase 2/3 remapping
            "processes":         processes,
            "context_switches":  self._count_context_switches(primary_result["gantt"]),
            "next":              "synchronization",
        }

    def run_phase_synchronization(
        self,
        sync_algorithm: str,
        phase1: dict[str, Any],
        sync_config: dict | None = None,
    ) -> dict[str, Any]:
        """Single-algorithm convenience wrapper — delegates to the multi version."""
        return self.run_phase_synchronization_multi([sync_algorithm], phase1, sync_config)

    def run_phase_synchronization_multi(
        self,
        sync_algorithms: list[str],
        phase1: dict[str, Any],
        sync_config: dict | None = None,
    ) -> dict[str, Any]:
        """
        Phase 2/3: run synchronization algorithms on the Phase 1 workload.

        For each sync algorithm:
        1. Run SyncSimulator to produce synchronization steps (enter_cs, blocked, …).
        2. Remap generic PIDs (P0, P1, …) to real PIDs using Phase 1's execution order.
        3. Build an integrated timeline that interleaves CPU schedule events
           (cpu_dispatch, cpu_release) with synchronization events, bound to
           each process's CPU time slice.

        The best sync algorithm (by score) becomes the PRIMARY for the frontend.
        All runs are returned so the UI can compare techniques.

        Phase 1 result is passed through unchanged to downstream phases so that
        Phase 4's report can show the full scheduling context alongside sync results.
        """
        if not phase1 or not phase1.get("scheduling"):
            raise ValueError("Phase 1 (CPU scheduling) must complete first")
        if not sync_algorithms:
            raise ValueError("Select at least one synchronization algorithm")

        from .analyzer import AnalysisEngine

        runs = [self._run_one_sync(algo, phase1, sync_config) for algo in sync_algorithms]
        sync_comparison = AnalysisEngine().analyze_sync(
            [r["synchronization"] for r in runs]
        )
        primary_algo = sync_comparison.get("best", {}).get("algorithm", sync_algorithms[0])
        primary_run = next(
            (r for r in runs if r["sync_algorithm"] == primary_algo), runs[0]
        )

        return {
            "phase": 2,
            "complete": True,
            "sync_algorithms": sync_algorithms,
            "runs": runs,
            "sync_comparison": sync_comparison,
            "primary_sync_algorithm": primary_algo,
            "synchronization": primary_run["synchronization"],
            "integrated_steps": primary_run["integrated_steps"],
            "execution_model": "sync_during_scheduled_cpu_slices",
            "state_table": primary_run["state_table"],
            "execution_order": phase1["execution_order"],
            "scheduling": phase1["scheduling"],
            "primary_sched_algorithm": phase1.get("primary_algorithm"),
            "next": "conclusion",
        }

    def _run_one_sync(
        self,
        sync_algorithm: str,
        phase1: dict[str, Any],
        sync_config: dict | None,
    ) -> dict[str, Any]:
        """
        Run a single synchronization algorithm and integrate it with the Phase 1 schedule.

        Steps:
        1. Run SyncSimulator with the same number of processes as Phase 1.
        2. Remap generic PIDs (P0, P1, …) → real PIDs in execution order.
        3. Build an interleaved timeline (schedule events + sync events).
        4. Build a state table (flat list of {tick, pid, state, action, in_cs}).
        """
        processes    = phase1["processes"]
        sched_result = phase1["scheduling"]
        order        = phase1["execution_order"]

        # Inject the process count and iteration defaults into the sync config
        sync_config = {
            **(sync_config or {}),
            "processes":  len(processes),
            "iterations": (sync_config or {}).get("iterations", 2),
        }

        sync_result = self.sync.run(sync_algorithm, sync_config)
        # Replace generic PIDs with the real PIDs from Phase 1's execution order
        sync_result = self._remap_sync_processes(sync_result, order)
        merged = self._build_interleaved_timeline(sched_result, sync_result, order, processes)

        return {
            "sync_algorithm":   sync_algorithm,
            "synchronization":  sync_result,        # raw sync simulation result
            "integrated_steps": merged,             # woven schedule + sync timeline
            "state_table":      self._build_state_table(merged),
        }

    def _remap_sync_processes(self, sync_result: dict, order: list[str]) -> dict:
        """
        Replace generic sync PIDs (P0, P1, …) with real process PIDs.

        The SyncSimulator uses generic names because it is algorithm-agnostic.
        This function maps those generics to the actual PIDs in the execution
        order produced by Phase 1's Gantt chart, so the integrated timeline
        shows "P3 acquires mutex" rather than "P0 acquires mutex."

        Mapping: generic PIDs sorted by length then lexicographically →
                 execution order from Phase 1.
        """
        result  = deepcopy(sync_result)
        generic = sorted(
            {k for step in result["steps"] for k in step.get("processes", {})},
            key=lambda x: (len(x), x),
        )
        # Build a stable bijection: generic[i] → order[i]
        mapping = {g: order[i] if i < len(order) else g for i, g in enumerate(generic)}

        def remap_pid(pid: str) -> str:
            return mapping.get(pid, pid)

        for step in result["steps"]:
            step["processes"]        = {remap_pid(k): v for k, v in step.get("processes",        {}).items()}
            step["critical_section"] = [remap_pid(p)    for p in    step.get("critical_section", [])]
            step["waiting_queue"]    = [remap_pid(p)    for p in    step.get("waiting_queue",    [])]
        return result

    def _execution_order(self, gantt: list[dict], processes: list[dict]) -> list[str]:
        """
        Derive process execution order from the Gantt chart.

        Returns PIDs in the order they FIRST appeared on the CPU.
        Processes that never ran (arrived too late in a short simulation) are
        appended at the end to ensure the mapping covers all processes.
        """
        seen: list[str] = []
        for seg in gantt:
            pid = seg["pid"]
            if pid != "IDLE" and pid not in seen:
                seen.append(pid)
        # Append any processes that never ran (e.g. arrived after simulation end)
        for p in processes:
            if p["pid"] not in seen:
                seen.append(p["pid"])
        return seen

    def _build_interleaved_timeline(
        self,
        sched: dict,
        sync: dict,
        order: list[str],
        processes: list[dict],
    ) -> list[dict]:
        """
        Weave the CPU schedule and sync steps into a single ordered timeline.

        For each Gantt segment:
          1. Emit a cpu_dispatch step  (PID goes RUNNING)
          2. Pull sync steps that belong to this PID's CPU slice
          3. Emit each sync step tagged with the active CPU process
          4. Emit a cpu_release step   (slice ends)

        This produces the integrated playback the frontend animates — each
        step is labelled with its phase (scheduling | sync_during_execution)
        so the UI can colour-code CPU events vs synchronization events.
        """
        burst_map   = {p["pid"]: p["burst"]   for p in processes}
        arrival_map = {p["pid"]: p["arrival"] for p in processes}
        gantt       = sched.get("gantt", [])
        sync_steps  = list(sync["steps"])
        merged:     list[dict] = []
        tick        = 0
        sync_idx    = 0

        # Step 0: announce the schedule plan so the student sees the execution order first
        merged.append({
            "phase": "scheduling",
            "tick": tick,
            "action": "schedule_plan",
            "message": (
                f"{sched['algorithm'].upper()} CPU order: {' → '.join(order)}. "
                f"Sync runs during each process CPU slice."
            ),
            "processes": {pid: "READY" for pid in order},
            "critical_section": [],
            "waiting_queue": [],
        })
        tick += 1

        for seg in gantt:
            pid = seg["pid"]
            cpu = {"start": seg["start"], "end": seg["end"], "duration": seg["end"] - seg["start"]}

            if pid == "IDLE":
                merged.append({
                    "phase": "scheduling",
                    "tick": tick,
                    "global_tick": tick,
                    "action": "cpu_idle",
                    "message": f"CPU idle t={cpu['start']}–{cpu['end']}",
                    "processes": {p: "READY" for p in order},
                    "critical_section": [],
                    "waiting_queue": [],
                    "cpu_interval": cpu,
                    "active_cpu": None,
                })
                tick += 1
                continue

            procs_state = {p: "READY" for p in order}
            procs_state[pid] = "RUNNING"
            merged.append({
                "phase": "scheduling",
                "tick": tick,
                "global_tick": tick,
                "action": "cpu_dispatch",
                "message": (
                    f"{pid} on CPU [t={cpu['start']}–{cpu['end']}]. "
                    f"Sync during this slice."
                ),
                "processes": dict(procs_state),
                "critical_section": [],
                "waiting_queue": [],
                "cpu_interval": cpu,
                "active_cpu": pid,
                "scheduled_process": pid,
                "burst_time": burst_map.get(pid, 0),
                "arrival_time": arrival_map.get(pid, 0),
            })
            tick += 1

            slice_steps, sync_idx = self._pull_sync_steps_for_cpu_slice(
                sync_steps, sync_idx, pid, order
            )
            for step in slice_steps:
                merged.append({
                    **step,
                    "phase": "sync_during_execution",
                    "tick": tick,
                    "global_tick": tick,
                    "cpu_interval": cpu,
                    "active_cpu": pid,
                    "scheduled_process": pid,
                    "message": f"[{pid} on CPU] {step.get('message', '')}",
                })
                tick += 1

            merged.append({
                "phase": "scheduling",
                "tick": tick,
                "global_tick": tick,
                "action": "cpu_release",
                "message": f"{pid} finished CPU slice",
                "processes": {p: "READY" for p in order},
                "critical_section": [],
                "waiting_queue": [],
                "cpu_interval": cpu,
                "active_cpu": pid,
            })
            tick += 1

        # Flush any remaining sync steps that weren't assigned to a CPU slice
        # (can happen if sync has more steps than Gantt segments)
        while sync_idx < len(sync_steps):
            step = sync_steps[sync_idx]
            sync_idx += 1
            merged.append({**step, "phase": "sync_during_execution", "tick": tick, "global_tick": tick})
            tick += 1

        # Final terminal step marks everything as done
        merged.append({
            "phase":          "complete",
            "tick":           tick,
            "global_tick":    tick,
            "action":         "terminate",
            "message":        "Scheduling and synchronization complete",
            "processes":      {pid: "TERMINATED" for pid in order},
            "critical_section": [],
            "waiting_queue":  [],
        })
        return merged

    def _pull_sync_steps_for_cpu_slice(
        self,
        sync_steps: list[dict],
        start_idx: int,
        cpu_pid: str,
        order: list[str],
    ) -> tuple[list[dict], int]:
        """
        Take sync steps that belong to cpu_pid's current CPU slice.

        A sync step "belongs" to cpu_pid if that PID appears in its active
        processes, critical_section, or waiting_queue lists.  Steps with no
        active involvement (e.g. pure scheduling housekeeping) are also included.

        Stops at a natural sync boundary (exit_cs, release, V_signal, done)
        or when the next step involves a different PID — so each CPU slice gets
        a coherent chunk of sync activity rather than steps from another process.
        """
        if start_idx >= len(sync_steps):
            return [], start_idx

        taken: list[dict] = []
        i = start_idx
        # Budget: distribute sync steps roughly evenly across CPU slices
        max_per_slice = max(4, len(sync_steps) // max(len(order), 1))

        while i < len(sync_steps) and len(taken) < max_per_slice:
            step = sync_steps[i]
            i += 1
            # Identify which PIDs are actively involved in this sync step
            involved = {
                pid
                for pid, state in step.get("processes", {}).items()
                if state not in ("READY", "TERMINATED")
            }
            involved.update(step.get("critical_section", []))
            involved.update(step.get("waiting_queue",    []))

            if cpu_pid in involved or not involved:
                taken.append(step)
                # Stop at a natural end-of-CS-cycle boundary
                if step.get("action") in ("exit_cs", "release", "V_signal", "exit_monitor", "done"):
                    break
            elif taken:
                # Next step belongs to a different PID — stop the slice here
                break

        # Guarantee at least one step per slice so no sync steps are skipped
        if not taken and start_idx < len(sync_steps):
            taken.append(sync_steps[start_idx])
            i = start_idx + 1

        return taken, i

    def _build_state_table(self, steps: list[dict]) -> list[dict]:
        """
        Flatten the integrated timeline into a per-tick per-process state table.

        Each row records {tick, pid, state, action, in_cs, phase} — this flat
        format is easy to query for statistics (e.g. "how many ticks was P1 blocked?")
        and is also used to build the before/after state matrix in Phase 4.
        """
        table = []
        for step in steps:
            for pid, state in step.get("processes", {}).items():
                table.append({
                    "tick":   step.get("global_tick", step.get("tick", 0)),
                    "pid":    pid,
                    "state":  state,
                    "action": step.get("action", ""),
                    "in_cs":  pid in step.get("critical_section", []),
                    "phase":  step.get("phase", ""),
                })
        return table

    def _count_context_switches(self, gantt: list[dict]) -> int:
        """
        Count the number of CPU context switches in a Gantt chart.

        A context switch is counted each time the CPU moves from one non-IDLE
        process to a different non-IDLE process.  IDLE segments are transparent
        — an IDLE gap between P1 and P2 is not a context switch.

        Context switch count is an overhead metric: higher values under Round
        Robin compared to FCFS quantify the scheduling overhead cost.
        """
        if len(gantt) < 2:
            return 0
        count = 0
        prev  = gantt[0]["pid"]
        for seg in gantt[1:]:
            if seg["pid"] != prev and seg["pid"] != "IDLE" and prev != "IDLE":
                count += 1
            if seg["pid"] != "IDLE":
                prev = seg["pid"]
        return count
