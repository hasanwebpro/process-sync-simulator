"""CPU scheduling simulation module."""

from __future__ import annotations

from typing import Any

from .constants import VALID_SCHED_ALGORITHMS


class CPUScheduler:
    """Discrete-event CPU scheduling simulators."""

    def __init__(self) -> None:
        self._algorithms = {
            "fcfs": self._fcfs,
            "sjf": self._sjf,
            "srtf": self._srtf,
            "round_robin": self._round_robin,
            "priority": self._priority,
        }

    def list_algorithms(self) -> list[dict[str, str]]:
        return [
            {"id": "fcfs", "name": "FCFS", "description": "First Come First Serve (non-preemptive)", "preemptive": False},
            {"id": "sjf", "name": "SJF", "description": "Shortest Job First (non-preemptive)", "preemptive": False},
            {"id": "srtf", "name": "SRTF", "description": "Shortest Remaining Time First (preemptive)", "preemptive": True},
            {"id": "round_robin", "name": "Round Robin", "description": "Time-quantum preemptive", "preemptive": True},
            {"id": "priority", "name": "Priority", "description": "Non-preemptive priority", "preemptive": False},
        ]

    def run(self, algorithm: str, processes: list[dict], quantum: int = 2) -> dict[str, Any]:
        if algorithm not in self._algorithms:
            raise ValueError(f"Unknown scheduling algorithm: {algorithm}")
        normalized = self._normalize(processes)
        gantt, metrics, timeline = self._algorithms[algorithm](normalized, quantum)
        return {
            "algorithm": algorithm,
            "processes": normalized,
            "quantum": quantum if algorithm == "round_robin" else None,
            "gantt": gantt,
            "timeline": timeline,
            "metrics": metrics,
            "averages": self._averages(metrics),
        }

    def _normalize(self, processes: list[dict]) -> list[dict]:
        result = []
        for i, p in enumerate(processes):
            result.append({
                "pid": p.get("pid", f"P{i+1}"),
                "arrival": int(p.get("arrival", 0)),
                "burst": int(p.get("burst", 1)),
                "priority": int(p.get("priority", i + 1)),
            })
        return result

    def _averages(self, metrics: list[dict]) -> dict[str, float]:
        n = len(metrics) or 1
        return {
            "avg_completion": round(sum(m["completion"] for m in metrics) / n, 2),
            "avg_turnaround": round(sum(m["turnaround"] for m in metrics) / n, 2),
            "avg_waiting": round(sum(m["waiting"] for m in metrics) / n, 2),
            "avg_response": round(sum(m["response"] for m in metrics) / n, 2),
            "throughput": round(n / max(m["completion"] for m in metrics), 4) if metrics else 0,
        }

    def _build_metrics(
        self, processes: list[dict], completion: dict[str, int], first_run: dict[str, int]
    ) -> list[dict]:
        out = []
        for p in processes:
            pid = p["pid"]
            ct = completion[pid]
            tat = ct - p["arrival"]
            wt = tat - p["burst"]
            rt = first_run[pid] - p["arrival"]
            out.append({
                "pid": pid,
                "arrival": p["arrival"],
                "burst": p["burst"],
                "priority": p["priority"],
                "completion": ct,
                "turnaround": tat,
                "waiting": wt,
                "response": rt,
            })
        return out

    def _fcfs(self, processes: list[dict], _quantum: int) -> tuple:
        sorted_p = sorted(processes, key=lambda x: (x["arrival"], x["pid"]))
        time = 0
        gantt: list[dict] = []
        completion: dict[str, int] = {}
        first_run: dict[str, int] = {}

        for p in sorted_p:
            if time < p["arrival"]:
                gantt.append({"pid": "IDLE", "start": time, "end": p["arrival"]})
                time = p["arrival"]
            first_run[p["pid"]] = time
            start = time
            time += p["burst"]
            gantt.append({"pid": p["pid"], "start": start, "end": time})
            completion[p["pid"]] = time

        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    def _sjf(self, processes: list[dict], _quantum: int) -> tuple:
        remaining = {p["pid"]: p["burst"] for p in processes}
        arrival = {p["pid"]: p["arrival"] for p in processes}
        done: set[str] = set()
        time = 0
        gantt: list[dict] = []
        completion: dict[str, int] = {}
        first_run: dict[str, int] = {}

        while len(done) < len(processes):
            available = [
                p for p in processes
                if p["pid"] not in done and arrival[p["pid"]] <= time
            ]
            if not available:
                next_arr = min(arrival[p["pid"]] for p in processes if p["pid"] not in done)
                gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                time = next_arr
                continue
            chosen = min(available, key=lambda x: (remaining[x["pid"]], x["arrival"], x["pid"]))
            pid = chosen["pid"]
            if pid not in first_run:
                first_run[pid] = time
            start = time
            time += remaining[pid]
            gantt.append({"pid": pid, "start": start, "end": time})
            completion[pid] = time
            done.add(pid)

        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    def _srtf(self, processes: list[dict], _quantum: int) -> tuple:
        """Shortest Remaining Time First (preemptive SJF).

        Simulates tick-by-tick.  Terminates cleanly when all processes are done
        without relying on an arbitrary max_time guard.
        """
        remaining = {p["pid"]: p["burst"] for p in processes}
        arrival = {p["pid"]: p["arrival"] for p in processes}
        done: set[str] = set()
        time = 0
        gantt: list[dict] = []
        completion: dict[str, int] = {}
        first_run: dict[str, int] = {}
        current: str | None = None

        while len(done) < len(processes):
            available = [
                p for p in processes
                if p["pid"] not in done
                and arrival[p["pid"]] <= time
                and remaining[p["pid"]] > 0
            ]

            if not available:
                # No process has arrived yet — jump to the next arrival time
                undone = [p for p in processes if p["pid"] not in done]
                if not undone:
                    break
                next_arr = min(arrival[p["pid"]] for p in undone)
                if next_arr > time:
                    if gantt and gantt[-1]["pid"] == "IDLE":
                        gantt[-1]["end"] = next_arr
                    else:
                        gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                    time = next_arr
                    current = None
                else:
                    # Safety: advance one tick to avoid an infinite loop on
                    # edge cases where arrival == time but remaining == 0.
                    time += 1
                continue

            chosen = min(
                available,
                key=lambda x: (remaining[x["pid"]], x["arrival"], x["pid"]),
            )
            pid = chosen["pid"]

            if pid not in first_run:
                first_run[pid] = time

            # Extend or start a new Gantt segment
            if current != pid:
                gantt.append({"pid": pid, "start": time, "end": time + 1})
                current = pid
            else:
                gantt[-1]["end"] = time + 1

            remaining[pid] -= 1
            time += 1

            if remaining[pid] == 0:
                completion[pid] = time
                done.add(pid)
                current = None

        gantt = self._merge_gantt(gantt)
        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    def _round_robin(self, processes: list[dict], quantum: int) -> tuple:
        remaining = {p["pid"]: p["burst"] for p in processes}
        arrival = {p["pid"]: p["arrival"] for p in processes}
        ready_queue: list[str] = []
        done: set[str] = set()
        time = 0
        gantt: list[dict] = []
        completion: dict[str, int] = {}
        first_run: dict[str, int] = {}
        n = len(processes)
        arrived: set[str] = set()

        while len(done) < n:
            for p in sorted(processes, key=lambda x: x["arrival"]):
                if p["pid"] not in arrived and p["arrival"] <= time:
                    arrived.add(p["pid"])
                    ready_queue.append(p["pid"])

            if not ready_queue:
                next_arr = min(
                    arrival[p["pid"]] for p in processes if p["pid"] not in arrived
                )
                gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                time = next_arr
                continue

            pid = ready_queue.pop(0)
            if pid not in first_run:
                first_run[pid] = time
            exec_time = min(quantum, remaining[pid])
            start = time
            time += exec_time
            remaining[pid] -= exec_time
            gantt.append({"pid": pid, "start": start, "end": time})

            for p in sorted(processes, key=lambda x: x["arrival"]):
                if (
                    p["pid"] not in arrived
                    and p["arrival"] <= time
                    and p["pid"] != pid
                ):
                    arrived.add(p["pid"])
                    ready_queue.append(p["pid"])

            if remaining[pid] == 0:
                completion[pid] = time
                done.add(pid)
            else:
                ready_queue.append(pid)

        gantt = self._merge_gantt(gantt)
        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    def _priority(self, processes: list[dict], _quantum: int) -> tuple:
        """Non-preemptive priority scheduling (lower number = higher priority).

        At each scheduling decision point we pick the highest-priority process
        that has *already arrived*, not the globally sorted list.  This prevents
        a late-arriving high-priority process from jumping ahead of processes
        that are already running.
        """
        remaining = {p["pid"]: p["burst"] for p in processes}
        arrival = {p["pid"]: p["arrival"] for p in processes}
        done: set[str] = set()
        time = 0
        gantt: list[dict] = []
        completion: dict[str, int] = {}
        first_run: dict[str, int] = {}

        while len(done) < len(processes):
            available = [
                p for p in processes
                if p["pid"] not in done and arrival[p["pid"]] <= time
            ]
            if not available:
                # CPU idle — jump to the next arrival
                next_arr = min(
                    arrival[p["pid"]] for p in processes if p["pid"] not in done
                )
                gantt.append({"pid": "IDLE", "start": time, "end": next_arr})
                time = next_arr
                continue

            # Lower priority number = higher priority; break ties by arrival then PID
            chosen = min(
                available,
                key=lambda x: (x["priority"], x["arrival"], x["pid"]),
            )
            pid = chosen["pid"]
            first_run[pid] = time
            start = time
            time += remaining[pid]
            gantt.append({"pid": pid, "start": start, "end": time})
            completion[pid] = time
            done.add(pid)

        metrics = self._build_metrics(processes, completion, first_run)
        return gantt, metrics, self._timeline(gantt)

    def _merge_gantt(self, gantt: list[dict]) -> list[dict]:
        if not gantt:
            return []
        merged = [gantt[0].copy()]
        for seg in gantt[1:]:
            if seg["pid"] == merged[-1]["pid"] and seg["start"] == merged[-1]["end"]:
                merged[-1]["end"] = seg["end"]
            else:
                merged.append(seg.copy())
        return merged

    def _timeline(self, gantt: list[dict]) -> list[dict]:
        colors = {}
        palette = [
            "#00d4ff", "#7b61ff", "#00ff88", "#ff6b6b",
            "#ffd93d", "#ff9f43", "#a29bfe", "#fd79a8",
        ]
        timeline = []
        for i, seg in enumerate(gantt):
            pid = seg["pid"]
            if pid not in colors:
                colors[pid] = "#444466" if pid == "IDLE" else palette[len(colors) % len(palette)]
            timeline.append({
                **seg,
                "duration": seg["end"] - seg["start"],
                "color": colors[pid],
            })
        return timeline

    def compare_all(self, processes: list[dict], quantum: int = 2) -> dict[str, Any]:
        results = {}
        for algo in self._algorithms:
            results[algo] = self.run(algo, processes, quantum)
        return results
