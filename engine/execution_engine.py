"""Execution Engine — scheduling + synchronization during CPU slices."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .scheduler import CPUScheduler
from .sync_engine import SyncSimulator


class ExecutionEngine:
    """
    CPU scheduling decides which process runs on the CPU and when.
    Synchronization runs during those CPU execution slices.
    """

    def __init__(self) -> None:
        self.scheduler = CPUScheduler()
        self.sync = SyncSimulator()

    def run_phase_scheduling(
        self, sched_algorithm: str, processes: list[dict], quantum: int = 2
    ) -> dict[str, Any]:
        return self.run_phase_scheduling_multi([sched_algorithm], processes, quantum)

    def run_phase_scheduling_multi(
        self, sched_algorithms: list[str], processes: list[dict], quantum: int = 2
    ) -> dict[str, Any]:
        if not sched_algorithms:
            raise ValueError("Select at least one scheduling algorithm")

        comparisons: dict[str, Any] = {}
        for algo in sched_algorithms:
            comparisons[algo] = self.scheduler.run(algo, processes, quantum)

        primary = min(
            sched_algorithms,
            key=lambda a: comparisons[a].get("averages", {}).get("avg_waiting", 9999),
        )
        primary_result = comparisons[primary]
        order = self._execution_order(primary_result["gantt"], processes)

        return {
            "phase": 1,
            "complete": True,
            "sched_algorithms": sched_algorithms,
            "comparisons": comparisons,
            "scheduling": primary_result,
            "primary_algorithm": primary,
            "execution_order": order,
            "processes": processes,
            "context_switches": self._count_context_switches(primary_result["gantt"]),
            "next": "synchronization",
        }

    def run_phase_synchronization(
        self,
        sync_algorithm: str,
        phase1: dict[str, Any],
        sync_config: dict | None = None,
    ) -> dict[str, Any]:
        return self.run_phase_synchronization_multi([sync_algorithm], phase1, sync_config)

    def run_phase_synchronization_multi(
        self,
        sync_algorithms: list[str],
        phase1: dict[str, Any],
        sync_config: dict | None = None,
    ) -> dict[str, Any]:
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
        processes = phase1["processes"]
        sched_result = phase1["scheduling"]
        order = phase1["execution_order"]
        sync_config = sync_config or {}
        sync_config = {
            **sync_config,
            "processes": len(processes),
            "iterations": sync_config.get("iterations", 2),
        }
        sync_result = self.sync.run(sync_algorithm, sync_config)
        sync_result = self._remap_sync_processes(sync_result, order)
        merged = self._build_interleaved_timeline(
            sched_result, sync_result, order, processes
        )
        return {
            "sync_algorithm": sync_algorithm,
            "synchronization": sync_result,
            "integrated_steps": merged,
            "state_table": self._build_state_table(merged),
        }

    def _remap_sync_processes(self, sync_result: dict, order: list[str]) -> dict:
        result = deepcopy(sync_result)
        generic = sorted(
            {k for step in result["steps"] for k in step.get("processes", {})},
            key=lambda x: (len(x), x),
        )
        mapping = {g: order[i] if i < len(order) else g for i, g in enumerate(generic)}

        def remap_pid(pid: str) -> str:
            return mapping.get(pid, pid)

        for step in result["steps"]:
            step["processes"] = {remap_pid(k): v for k, v in step.get("processes", {}).items()}
            step["critical_section"] = [remap_pid(p) for p in step.get("critical_section", [])]
            step["waiting_queue"] = [remap_pid(p) for p in step.get("waiting_queue", [])]
        return result

    def _execution_order(self, gantt: list[dict], processes: list[dict]) -> list[str]:
        seen: list[str] = []
        for seg in gantt:
            pid = seg["pid"]
            if pid != "IDLE" and pid not in seen:
                seen.append(pid)
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
        burst_map = {p["pid"]: p["burst"] for p in processes}
        arrival_map = {p["pid"]: p["arrival"] for p in processes}
        gantt = sched.get("gantt", [])
        sync_steps = list(sync["steps"])
        merged: list[dict] = []
        tick = 0
        sync_idx = 0

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

        while sync_idx < len(sync_steps):
            step = sync_steps[sync_idx]
            sync_idx += 1
            merged.append({**step, "phase": "sync_during_execution", "tick": tick, "global_tick": tick})
            tick += 1

        merged.append({
            "phase": "complete",
            "tick": tick,
            "global_tick": tick,
            "action": "terminate",
            "message": "Scheduling and synchronization complete",
            "processes": {pid: "TERMINATED" for pid in order},
            "critical_section": [],
            "waiting_queue": [],
        })
        return merged

    def _pull_sync_steps_for_cpu_slice(
        self,
        sync_steps: list[dict],
        start_idx: int,
        cpu_pid: str,
        order: list[str],
    ) -> tuple[list[dict], int]:
        if start_idx >= len(sync_steps):
            return [], start_idx

        taken: list[dict] = []
        i = start_idx
        max_per_slice = max(4, len(sync_steps) // max(len(order), 1))

        while i < len(sync_steps) and len(taken) < max_per_slice:
            step = sync_steps[i]
            i += 1
            involved = {
                pid
                for pid, state in step.get("processes", {}).items()
                if state not in ("READY", "TERMINATED")
            }
            involved.update(step.get("critical_section", []))
            involved.update(step.get("waiting_queue", []))
            if cpu_pid in involved or not involved:
                taken.append(step)
                if step.get("action") in ("exit_cs", "release", "V_signal", "exit_monitor", "done"):
                    break
            elif taken:
                break

        if not taken and start_idx < len(sync_steps):
            taken.append(sync_steps[start_idx])
            i = start_idx + 1

        return taken, i

    def _build_state_table(self, steps: list[dict]) -> list[dict]:
        table = []
        for step in steps:
            for pid, state in step.get("processes", {}).items():
                table.append({
                    "tick": step.get("global_tick", step.get("tick", 0)),
                    "pid": pid,
                    "state": state,
                    "action": step.get("action", ""),
                    "in_cs": pid in step.get("critical_section", []),
                    "phase": step.get("phase", ""),
                })
        return table

    def _count_context_switches(self, gantt: list[dict]) -> int:
        if len(gantt) < 2:
            return 0
        count = 0
        prev = gantt[0]["pid"]
        for seg in gantt[1:]:
            if seg["pid"] != prev and seg["pid"] != "IDLE" and prev != "IDLE":
                count += 1
            if seg["pid"] != "IDLE":
                prev = seg["pid"]
        return count
