"""Analysis and intelligence engine — rule-based with optional OpenAI."""

from __future__ import annotations

import os
from typing import Any

from .constants import SYNC_ALGORITHM_NAMES


class AnalysisEngine:
    """Compares sync/scheduling results and generates explanations."""

    SYNC_RULES = {
        "peterson": {
            "strengths": ["Deadlock-free for two processes", "No hardware support needed", "Fair turn-taking"],
            "weaknesses": ["Limited to two processes", "Busy-wait in some implementations", "Not used in modern kernels"],
            "use_case": "Teaching mutual exclusion; historical interest",
            "score": 78,
        },
        "dekker": {
            "strengths": ["First software solution for two processes", "Correct mutual exclusion"],
            "weaknesses": ["Complex logic", "Busy waiting", "Only two processes"],
            "use_case": "Historical algorithms course",
            "score": 72,
        },
        "mutex": {
            "strengths": ["Simple API", "Strict mutual exclusion", "Eliminates race conditions"],
            "weaknesses": ["Can cause contention", "Improper use leads to deadlock", "No built-in ordering"],
            "use_case": "Protecting shared data structures in multi-threaded apps",
            "score": 92,
        },
        "binary_semaphore": {
            "strengths": ["Classic P/V semantics", "Efficient for binary resources", "Well-understood"],
            "weaknesses": ["Easy to misuse (wrong ordering)", "No ownership semantics"],
            "use_case": "Mutex-like exclusion, signaling between threads",
            "score": 88,
        },
        "counting_semaphore": {
            "strengths": ["Controls resource pools", "Flexible concurrency level"],
            "weaknesses": ["Starvation possible without fairness policy", "Complex debugging"],
            "use_case": "Connection pools, limited I/O slots",
            "score": 85,
        },
        "producer_consumer": {
            "strengths": ["Models real pipelines", "Decouples production/consumption rates"],
            "weaknesses": ["Buffer overflow/underflow if misconfigured", "Multiple semaphores to coordinate"],
            "use_case": "Message queues, print spoolers, streaming pipelines",
            "score": 90,
        },
        "readers_writers": {
            "strengths": ["Maximizes read concurrency", "Protects writes"],
            "weaknesses": ["Writer starvation possible", "Reader starvation with writer priority"],
            "use_case": "Databases, caches, config files",
            "score": 86,
        },
        "monitor": {
            "strengths": ["Structured synchronization", "Condition variables avoid busy wait", "Modern and maintainable"],
            "weaknesses": ["Language/runtime support required", "Must follow monitor discipline"],
            "use_case": "Java synchronized blocks, pthread condition variables",
            "score": 94,
        },
        "race_condition": {
            "strengths": ["Demonstrates why sync matters"],
            "weaknesses": ["Unsafe mode shows incorrect results by design"],
            "use_case": "Debugging concurrent bugs",
            "score": 50,
        },
        "deadlock_demo": {
            "strengths": ["Clear visualization of circular wait"],
            "weaknesses": ["System halts without recovery"],
            "use_case": "Deadlock prevention training",
            "score": 40,
        },
    }

    SCHED_RULES = {
        "fcfs": {"best_for": "Simple batch systems", "fairness": "Fair in arrival order", "overhead": "Low"},
        "sjf": {"best_for": "Minimizing average waiting time", "fairness": "Can starve long jobs", "overhead": "Medium"},
        "srtf": {"best_for": "Optimal average waiting (preemptive)", "fairness": "Starvation risk", "overhead": "High"},
        "round_robin": {"best_for": "Time-sharing interactive systems", "fairness": "Very fair", "overhead": "Context switch cost"},
        "priority": {"best_for": "Real-time / importance-based tasks", "fairness": "Low-priority starvation", "overhead": "Low"},
    }

    def analyze_sync(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Compare sync technique runs using real simulation metrics only —
        no hardcoded scores. All values derived from actual step data.
        """
        if not results:
            return {"error": "No results to analyze"}

        scored = []
        for r in results:
            algo    = r.get("algorithm", "")
            steps   = r.get("steps", [])
            summary = r.get("summary", {})
            total   = max(len(steps), 1)

            # ── Real metrics from simulation steps ────────────────────────
            wait_events = sum(
                1 for s in steps
                if s.get("action") in ("blocked", "wait", "block", "waiting", "write_block")
            )
            busy_wait_steps = sum(
                1 for s in steps
                if s.get("action") == "busy_wait"
                or ("busy" in s.get("message", "").lower() and s.get("action") == "wait")
            )
            cs_entries = sum(1 for s in steps if s.get("action") == "enter_cs")

            mutual_exclusion = summary.get("mutual_exclusion", True)
            deadlock_free    = not summary.get("deadlock", False)
            race_detected    = summary.get("race_detected", False)

            # Counter correctness: final == expected (if both present)
            final    = summary.get("final_counter")
            expected = summary.get("expected_counter", final)
            if final is not None and expected is not None and expected > 0:
                correctness = 1.0 if final == expected else max(
                    0.0, 1.0 - abs(final - expected) / expected
                )
            else:
                correctness = 1.0 if mutual_exclusion else 0.4

            # ── Score: computed entirely from simulation ───────────────────
            # Mutual exclusion maintained            → 40 pts (binary)
            # Deadlock free                          → 25 pts (binary)
            # Counter correctness                    → 20 pts (continuous)
            # Efficiency: penalty for wait+busy-wait → -15 pts max
            wait_ratio      = (wait_events + busy_wait_steps) / total
            busy_ratio      = busy_wait_steps / total
            efficiency_pen  = min(15.0, wait_ratio * 20 + busy_ratio * 20)

            score = round(
                40.0 * (1.0 if mutual_exclusion else 0.0) +
                25.0 * (1.0 if deadlock_free    else 0.0) +
                20.0 * correctness -
                efficiency_pen +
                (0.0 if race_detected else 0.0),   # already captured in ME
                1,
            )
            score = max(0.0, min(100.0, score))

            rules = self.SYNC_RULES.get(algo, {})
            scored.append({
                "algorithm": algo,
                "name": next(
                    (a["name"] for a in SYNC_ALGORITHM_NAMES if a["id"] == algo), algo
                ),
                "score": score,
                "metrics": {
                    "total_steps":      total,
                    "cs_entries":       cs_entries,
                    "wait_events":      wait_events,
                    "busy_wait_steps":  busy_wait_steps,
                    "mutual_exclusion": mutual_exclusion,
                    "deadlock_free":    deadlock_free,
                    "correctness":      round(correctness, 2),
                },
                "summary":    summary,
                "strengths":  rules.get("strengths", []),
                "weaknesses": rules.get("weaknesses", []),
                "use_case":   rules.get("use_case", ""),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        best  = scored[0]
        worst = scored[-1]

        deadlock   = any(r.get("summary", {}).get("deadlock")      for r in results)
        starvation = any(r.get("summary", {}).get("starvation")     for r in results)

        return {
            "rankings":           scored,
            "best":               best,
            "worst":              worst,
            "deadlock_detected":  deadlock,
            "starvation_detected": starvation,
            "explanation":        self._sync_explanation(best, worst, scored),
            "recommendation":     self._sync_recommendation(best),
        }

    def analyze_scheduling(self, comparison: dict[str, Any]) -> dict[str, Any]:
        """Compare scheduling algorithm results."""
        if not comparison:
            return {"error": "No scheduling data"}

        ranked = []
        for algo, data in comparison.items():
            avgs = data.get("averages", {})
            rules = self.SCHED_RULES.get(algo, {})
            ranked.append({
                "algorithm": algo,
                "name": algo.upper().replace("_", " "),
                "avg_turnaround": avgs.get("avg_turnaround", 0),
                "avg_waiting": avgs.get("avg_waiting", 0),
                "avg_response": avgs.get("avg_response", 0),
                "throughput": avgs.get("throughput", 0),
                "fairness": rules.get("fairness", ""),
                "best_for": rules.get("best_for", ""),
            })

        ranked.sort(key=lambda x: x["avg_waiting"])
        best = ranked[0]
        worst = ranked[-1]

        return {
            "rankings": ranked,
            "best": best,
            "worst": worst,
            "explanation": (
                f"{best['name']} achieved the lowest average waiting time "
                f"({best['avg_waiting']}) for the given workload. "
                f"{worst['name']} had the highest average waiting ({worst['avg_waiting']}). "
                f"Round Robin is recommended for interactive fairness; "
                f"SJF/SRTF for batch throughput optimization."
            ),
            "recommendation": f"Use {best['name']} when minimizing waiting time is the primary goal.",
        }

    def explain_with_ai(self, context: str) -> dict[str, Any]:
        """Optional OpenAI explanation; falls back to rule-based."""
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return {"source": "rule_based", "text": None}
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "OS tutor. Reply in 2-3 short sentences. "
                            "Name best scheduler and best sync algorithm with numbers. "
                            "One clear recommendation. No fluff."
                        ),
                    },
                    {"role": "user", "content": f"Analyze and recommend:\n{context}"},
                ],
                max_tokens=120,
            )
            text = response.choices[0].message.content or context
            return {"source": "openai", "text": text}
        except Exception as e:
            return {"source": "rule_based", "text": context, "error": str(e)}

    def build_llm_context(self, phase1: dict, phase2: dict) -> str:
        lines = ["=== CPU SCHEDULING ==="]
        for algo, data in phase1.get("comparisons", {}).items():
            avgs = data.get("averages", {})
            lines.append(
                f"{algo.upper()}: avg_WT={avgs.get('avg_waiting')}, "
                f"avg_TAT={avgs.get('avg_turnaround')}, throughput={avgs.get('throughput')}"
            )
        lines.append(f"Primary schedule: {phase1.get('primary_algorithm', '').upper()}")
        lines.append("\n=== SYNCHRONIZATION ===")
        for r in phase2.get("sync_comparison", {}).get("rankings", []):
            lines.append(
                f"{r.get('name')}: score={r.get('score')}, "
                f"strengths={', '.join((r.get('strengths') or [])[:2])}"
            )
        best = phase2.get("sync_comparison", {}).get("best", {})
        if best:
            lines.append(f"Best sync: {best.get('name')} ({best.get('score')}/100)")
        return "\n".join(lines)

    def generate_multi_conclusion(self, phase1: dict, phase2: dict) -> dict[str, Any]:
        sched_analysis = (
            self.analyze_scheduling(phase1["comparisons"])
            if phase1.get("comparisons") else None
        )
        sync_comparison = phase2.get("sync_comparison", {})
        best_sync = sync_comparison.get("best", {})
        worst_sync = sync_comparison.get("worst", {})
        best_sched = (sched_analysis or {}).get("best", {})
        worst_sched = (sched_analysis or {}).get("worst", {})
        n_sched = len(phase1.get("sched_algorithms", []))
        n_sync = len(phase2.get("sync_algorithms", []))

        sched_name = best_sched.get("name", phase1.get("primary_algorithm", "FCFS"))
        sync_name = best_sync.get("name", "Mutex")

        executive = (
            f"Compared {n_sched} scheduling algorithm(s) and {n_sync} synchronization method(s). "
            f"{sched_name} gave the lowest average waiting time "
            f"(AWT={best_sched.get('avg_waiting', '—')}, ATAT={best_sched.get('avg_turnaround', '—')}). "
            f"{sync_name} scored highest at {best_sync.get('score', '—')}/100 "
            f"for safe shared resource access."
        )

        sched_summary = (
            f"{sched_name} achieved the best average waiting time "
            f"({best_sched.get('avg_waiting', '—')}) and turnaround "
            f"({best_sched.get('avg_turnaround', '—')}). "
            f"{worst_sched.get('name', 'Another algorithm')} was weakest on waiting time "
            f"({worst_sched.get('avg_waiting', '—')}). "
            f"Execution order on CPU: {' → '.join(phase1.get('execution_order', []))}."
        )

        sync_summary = self._sync_explanation(
            best_sync, worst_sync, sync_comparison.get("rankings", [])
        )

        rec_bullets = [
            f"For CPU scheduling in this workload, prefer {sched_name} to reduce waiting time.",
            f"For protecting shared variables, use {sync_name}-style mutual exclusion.",
            "Always pair scheduling with synchronization when processes share memory or files.",
            f"Context switches observed: {phase1.get('context_switches', '—')} — more switches can mean higher overhead.",
        ]
        if sync_comparison.get("deadlock_detected"):
            rec_bullets.append("Deadlock risk was detected - review lock ordering and circular wait.")
        if sync_comparison.get("starvation_detected"):
            rec_bullets.append("Starvation or deadlock risk was detected — review queue fairness and lock ordering.")

        detailed_rec = (
            f"Recommended stack: {sched_name} for CPU ordering + {sync_name} for critical sections. "
            f"{best_sync.get('use_case', 'Monitor and mutex patterns suit most application code.')}"
        )

        return {
            "phase": 3,
            "complete": True,
            "title": "ANALYSIS REPORT",
            "executive_summary": executive,
            "conclusion": executive,
            "sched_summary": sched_summary,
            "sync_summary": sync_summary,
            "recommendation": detailed_rec,
            "detailed_recommendation": detailed_rec,
            "recommendation_bullets": rec_bullets,
            "findings": [
                f"{sync_name} best for shared resources (score {best_sync.get('score')})",
                f"{sched_name} best for CPU ordering (AWT {best_sched.get('avg_waiting')})",
            ],
            "sched_analysis": sched_analysis,
            "sync_analysis": sync_comparison,
            "metrics": {
                "execution_order": phase1.get("execution_order", []),
                "primary_sched": phase1.get("primary_algorithm"),
                "primary_sync": phase2.get("primary_sync_algorithm"),
                **phase1.get("scheduling", {}).get("averages", {}),
            },
            "sync_score": best_sync.get("score", 75),
        }

    def generate_conclusion(self, phase1: dict, phase2: dict) -> dict[str, Any]:
        if not phase1 or not phase2:
            raise ValueError("Phases 1 and 2 must complete first")
        if phase2.get("sync_comparison") or phase1.get("comparisons"):
            return self.generate_multi_conclusion(phase1, phase2)

    def _sync_explanation(self, best: dict, worst: dict, all_ranked: list) -> str:
        lines = [
            f"**{best['name']}** performed best (score {best['score']}/100) "
            f"due to: {', '.join(best.get('strengths', [])[:2]) or 'strong mutual exclusion'}.",
            f"**{worst['name']}** ranked lowest (score {worst['score']}/100) "
            f"because: {', '.join(worst.get('weaknesses', [])[:2]) or 'higher risk in concurrent access'}.",
        ]
        if any(r.get("summary", {}).get("race_detected") for r in all_ranked):
            lines.append(
                "Race conditions were detected in unsafe runs — mutex or semaphore "
                "protection is required for shared counters."
            )
        if any(r.get("summary", {}).get("deadlock") for r in all_ranked):
            lines.append(
                "Deadlock was demonstrated — break circular wait with ordering or timeouts."
            )
        return " ".join(lines)

    def _sync_recommendation(self, best: dict) -> str:
        return (
            f"For production systems, prefer **{best['name']}**-style approaches: "
            f"{best.get('use_case', 'monitor or mutex-based designs')}. "
            f"Mutex-based synchronization performed best due to strict mutual exclusion "
            f"and elimination of race conditions in shared resource access."
        )

