"""
app.py — Flask REST API for the Process Synchronization Simulator
==================================================================

All simulation logic lives in the engine/ package.  This file wires each
engine function to an HTTP endpoint and handles:
    - JSON request parsing
    - Input validation (via engine/validators.py)
    - Uniform error responses ({"success": False, "error": "…"})
    - Uniform success responses ({"success": True, …result fields…})

API endpoint map
----------------
GET  /                         — Serve the single-page application (index.html)

GET  /api/scheduler/algorithms — List all scheduling algorithms + metadata
POST /api/scheduler/run        — Run a single scheduling algorithm (standalone)

GET  /api/sync/algorithms      — List all synchronization algorithms + metadata
POST /api/sync/run             — Run a single sync simulation (standalone)

POST /api/pipeline/phase1      — Phase 1: CPU scheduling (one or more algorithms)
POST /api/pipeline/phase2      — Phase 2/3: sync simulation on Phase 1 workload
POST /api/pipeline/phase3      — Phase 4: generate analysis report and conclusions
POST /api/pipeline/full        — All phases in a single call (for automated tests)

GET  /api/diagnostics/techniques — List sync technique profiles
GET  /api/diagnostics/problems   — List detectable synchronization problems
POST /api/diagnostics/run        — Phase 2 detection: unsynchronized problem analysis

Error handling
--------------
All routes catch ValidationError (bad user input) and ValueError (engine errors)
and return a 400 JSON response.  Unhandled exceptions propagate to Flask's
default error handler (500 in production, debug traceback in development).

Engine instances
----------------
Each engine object is instantiated once at startup and reused across requests.
All engines are stateless (they store no request data), so this is safe.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from engine import (
    AnalysisEngine,
    CPUScheduler,
    DiagnosticsEngine,
    ExecutionEngine,
    SyncSimulator,
    list_problems,
    list_techniques,
)
from engine.validators import (
    ValidationError,
    validate_processes,
    validate_quantum,
    validate_sched_algorithms,
    validate_sync_algorithms,
    validate_sync_config,
)

# Load environment variables from .env (PORT, FLASK_DEBUG, OPENAI_API_KEY)
load_dotenv()

app = Flask(__name__)

# Singleton engine instances — all are stateless, safe to reuse across requests
sync_sim    = SyncSimulator()
scheduler   = CPUScheduler()
analyzer    = AnalysisEngine()
execution   = ExecutionEngine()
diagnostics = DiagnosticsEngine()


def _err(msg: str, status: int = 400):
    """Return a uniform JSON error response."""
    return jsonify({"success": False, "error": msg}), status


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the single-page application."""
    return render_template("index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Synchronization algorithm endpoints (standalone, not part of pipeline)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/sync/algorithms")
def sync_algorithms():
    """List all synchronization algorithms with their IDs and descriptions."""
    return jsonify(sync_sim.list_algorithms())


@app.route("/api/sync/run", methods=["POST"])
def sync_run():
    """
    Run a single synchronization simulation.

    Request body:
        algorithm  — sync algorithm ID (default: "mutex")
        config     — optional simulation config dict

    Response: { success, algorithm, steps, summary, total_ticks }
    """
    data = request.get_json() or {}
    try:
        algorithms = validate_sync_algorithms([data.get("algorithm", "mutex")])
        config     = validate_sync_config(data.get("config", {}))
        result     = sync_sim.run(algorithms[0], config)
        return jsonify({"success": True, **result})
    except (ValidationError, ValueError) as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Scheduling algorithm endpoints (standalone)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/scheduler/algorithms")
def sched_algorithms():
    """List all scheduling algorithms with preemptive flag and descriptions."""
    return jsonify(scheduler.list_algorithms())


@app.route("/api/scheduler/run", methods=["POST"])
def sched_run():
    """
    Run a single scheduling algorithm.

    Request body:
        algorithm  — scheduling algorithm ID (default: "fcfs")
        processes  — list of {pid, arrival, burst, priority} dicts
        quantum    — time quantum for Round Robin (default: 2)

    Response: { success, algorithm, gantt, timeline, metrics, averages }
    """
    data = request.get_json() or {}
    try:
        algorithms = validate_sched_algorithms([data.get("algorithm", "fcfs")])
        processes  = validate_processes(
            data.get("processes", [
                {"pid": "P1", "arrival": 0, "burst": 5, "priority": 2},
                {"pid": "P2", "arrival": 1, "burst": 3, "priority": 1},
                {"pid": "P3", "arrival": 2, "burst": 8, "priority": 3},
            ])
        )
        quantum = validate_quantum(data.get("quantum", 2))
        result  = scheduler.run(algorithms[0], processes, quantum)
        return jsonify({"success": True, **result})
    except (ValidationError, ValueError) as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Simulation pipeline endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/pipeline/phase1", methods=["POST"])
def pipeline_phase1():
    """
    Phase 1: CPU Scheduling.

    Runs one or more scheduling algorithms, identifies the primary (lowest AWT),
    and returns the Gantt chart, metrics, execution order, and context-switch count.

    Request body:
        sched_algorithms — list of algorithm IDs
        processes        — list of process dicts
        quantum          — time quantum for Round Robin

    Response: { success, phase=1, scheduling, comparisons, primary_algorithm,
                execution_order, context_switches, processes }
    """
    data = request.get_json() or {}
    try:
        sched_algos = validate_sched_algorithms(
            data.get("sched_algorithms") or [data.get("algorithm", "fcfs")]
        )
        processes = validate_processes(data.get("processes", []))
        quantum   = validate_quantum(data.get("quantum", 2))
        result    = execution.run_phase_scheduling_multi(sched_algos, processes, quantum)
        return jsonify({"success": True, **result})
    except (ValidationError, ValueError) as e:
        return _err(str(e))


@app.route("/api/pipeline/phase2", methods=["POST"])
def pipeline_phase2():
    """
    Phase 2/3: Synchronization Simulation.

    Runs one or more synchronization algorithms on the Phase 1 workload.
    Each algorithm's steps are interleaved with the CPU schedule to produce
    a unified playback timeline.

    Request body:
        sync_algorithms — list of sync algorithm IDs
        phase1          — Phase 1 result (from /api/pipeline/phase1)
        sync_config     — optional simulation config dict

    Response: { success, phase=2, integrated_steps, sync_comparison,
                primary_sync_algorithm, synchronization, state_table }
    """
    data = request.get_json() or {}
    try:
        sync_algos  = validate_sync_algorithms(
            data.get("sync_algorithms") or [data.get("algorithm", "mutex")]
        )
        phase1      = data.get("phase1")
        if not phase1:
            raise ValidationError("phase1 result is required.")
        sync_config = validate_sync_config(data.get("sync_config", {}))
        result      = execution.run_phase_synchronization_multi(sync_algos, phase1, sync_config)
        return jsonify({"success": True, **result})
    except (ValidationError, ValueError) as e:
        return _err(str(e))


@app.route("/api/pipeline/phase3", methods=["POST"])
def pipeline_phase3():
    """
    Phase 4: Analysis Report Generation.

    Combines Phase 1 (scheduling results) and Phase 2 (sync results) to
    produce the executive summary, scheduler comparison, sync ranking,
    recommendation bullets, and an optional OpenAI explanation.

    Request body:
        phase1 — Phase 1 result dict
        phase2 — Phase 2 result dict

    Response: { success, conclusion, ai_explanation, llm_context }
    """
    data   = request.get_json() or {}
    phase1 = data.get("phase1")
    phase2 = data.get("phase2")
    if not phase1 or not phase2:
        return _err("Both phase1 and phase2 results are required.")
    try:
        conclusion   = analyzer.generate_multi_conclusion(phase1, phase2)
        llm_context  = analyzer.build_llm_context(phase1, phase2)
        ai           = analyzer.explain_with_ai(llm_context)
        return jsonify({
            "success":        True,
            "conclusion":     conclusion,
            "ai_explanation": ai,
            "llm_context":    llm_context,
        })
    except ValueError as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostics endpoints (Phase 2 problem detection)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/diagnostics/techniques")
def diagnostics_techniques():
    """List all synchronization technique profiles (name, desc, capability)."""
    return jsonify(list_techniques())


@app.route("/api/diagnostics/problems")
def diagnostics_problems():
    """List all detectable synchronization problems with their categories."""
    return jsonify(list_problems())


@app.route("/api/diagnostics/run", methods=["POST"])
def diagnostics_run():
    """
    Phase 2: Unsynchronized Problem Detection.

    Runs the full detect-then-evaluate pipeline:
        1. Schedule the workload with the given algorithm.
        2. Replay the CPU trace without synchronization to detect:
               - Race conditions (overlapping read-modify-write windows)
               - CS violations (mutual exclusion breaches in the model)
               - Deadlock (hold-and-wait circular wait on two resources)
               - Starvation (process waiting far longer than peers)
        3. Evaluate every synchronization technique against the detected problems.

    Note: livelock, producer-consumer, readers-writers, dining philosophers,
    and sleeping barber are returned with occurred=False and an explanation
    of why they cannot be inferred from a generic scheduling trace.

    Request body:
        processes       — list of process dicts
        sched_algorithm — scheduling algorithm ID (default: "round_robin")
        quantum         — time quantum
        techniques      — list of technique IDs to evaluate (None = all)

    Response: { success, scheduler, base_metrics, problems, problems_occurred,
                techniques, best, recommendation, contention }
    """
    data = request.get_json() or {}
    try:
        processes   = validate_processes(data.get("processes", []))
        sched_algos = validate_sched_algorithms(
            [data.get("sched_algorithm", "round_robin")]
        )
        quantum    = validate_quantum(data.get("quantum", 2))
        techniques = data.get("techniques")   # None → evaluate all techniques
        result     = diagnostics.run(processes, sched_algos[0], quantum, techniques)
        return jsonify({"success": True, **result})
    except (ValidationError, ValueError) as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Full pipeline (all phases in one request — useful for automated testing)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/pipeline/full", methods=["POST"])
def pipeline_full():
    """
    Run all four simulation phases in a single HTTP call.

    Convenience endpoint for automated tests or the "Run All" button.
    Executes Phase 1 → Phase 2/3 → Phase 4 sequentially and returns all results.

    Request body:
        sched_algorithms — list of scheduling algorithm IDs
        sync_algorithms  — list of synchronization algorithm IDs
        processes        — list of process dicts
        quantum          — time quantum
        sync_config      — optional sync simulation config

    Response: { success, phase1, phase2, conclusion, ai_explanation }
    """
    data = request.get_json() or {}
    try:
        sched_algos = validate_sched_algorithms(
            data.get("sched_algorithms") or ["fcfs"]
        )
        sync_algos  = validate_sync_algorithms(
            data.get("sync_algorithms") or ["mutex"]
        )
        processes   = validate_processes(data.get("processes", []))
        quantum     = validate_quantum(data.get("quantum", 2))
        sync_config = validate_sync_config(data.get("sync_config", {}))

        # Run all phases sequentially
        phase1      = execution.run_phase_scheduling_multi(sched_algos, processes, quantum)
        phase2      = execution.run_phase_synchronization_multi(sync_algos, phase1, sync_config)
        conclusion  = analyzer.generate_multi_conclusion(phase1, phase2)
        llm_context = analyzer.build_llm_context(phase1, phase2)
        ai          = analyzer.explain_with_ai(llm_context)

        return jsonify({
            "success":        True,
            "phase1":         phase1,
            "phase2":         phase2,
            "conclusion":     conclusion,
            "ai_explanation": ai,
        })
    except (ValidationError, ValueError) as e:
        return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
