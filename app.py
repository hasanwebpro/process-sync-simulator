"""Process Synchronization Simulator — Flask application."""

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

load_dotenv()

app = Flask(__name__)
sync_sim = SyncSimulator()
scheduler = CPUScheduler()
analyzer = AnalysisEngine()
execution = ExecutionEngine()
diagnostics = DiagnosticsEngine()


def _err(msg: str, status: int = 400):
    return jsonify({"success": False, "error": msg}), status


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sync/algorithms")
def sync_algorithms():
    return jsonify(sync_sim.list_algorithms())


@app.route("/api/sync/run", methods=["POST"])
def sync_run():
    data = request.get_json() or {}
    try:
        algorithms = validate_sync_algorithms([data.get("algorithm", "mutex")])
        config = validate_sync_config(data.get("config", {}))
        result = sync_sim.run(algorithms[0], config)
        return jsonify({"success": True, **result})
    except ValidationError as e:
        return _err(str(e))
    except ValueError as e:
        return _err(str(e))


@app.route("/api/scheduler/algorithms")
def sched_algorithms():
    return jsonify(scheduler.list_algorithms())


@app.route("/api/scheduler/run", methods=["POST"])
def sched_run():
    data = request.get_json() or {}
    try:
        algorithms = validate_sched_algorithms([data.get("algorithm", "fcfs")])
        processes = validate_processes(
            data.get("processes", [
                {"pid": "P1", "arrival": 0, "burst": 5, "priority": 2},
                {"pid": "P2", "arrival": 1, "burst": 3, "priority": 1},
                {"pid": "P3", "arrival": 2, "burst": 8, "priority": 3},
            ])
        )
        quantum = validate_quantum(data.get("quantum", 2))
        result = scheduler.run(algorithms[0], processes, quantum)
        return jsonify({"success": True, **result})
    except ValidationError as e:
        return _err(str(e))
    except ValueError as e:
        return _err(str(e))


@app.route("/api/pipeline/phase1", methods=["POST"])
def pipeline_phase1():
    data = request.get_json() or {}
    try:
        sched_algos = validate_sched_algorithms(
            data.get("sched_algorithms") or [data.get("algorithm", "fcfs")]
        )
        processes = validate_processes(data.get("processes", []))
        quantum = validate_quantum(data.get("quantum", 2))
        result = execution.run_phase_scheduling_multi(sched_algos, processes, quantum)
        return jsonify({"success": True, **result})
    except ValidationError as e:
        return _err(str(e))
    except ValueError as e:
        return _err(str(e))


@app.route("/api/pipeline/phase2", methods=["POST"])
def pipeline_phase2():
    data = request.get_json() or {}
    try:
        sync_algos = validate_sync_algorithms(
            data.get("sync_algorithms") or [data.get("algorithm", "mutex")]
        )
        phase1 = data.get("phase1")
        if not phase1:
            raise ValidationError("phase1 result is required.")
        sync_config = validate_sync_config(data.get("sync_config", {}))
        result = execution.run_phase_synchronization_multi(sync_algos, phase1, sync_config)
        return jsonify({"success": True, **result})
    except ValidationError as e:
        return _err(str(e))
    except ValueError as e:
        return _err(str(e))


@app.route("/api/pipeline/phase3", methods=["POST"])
def pipeline_phase3():
    data = request.get_json() or {}
    phase1 = data.get("phase1")
    phase2 = data.get("phase2")
    if not phase1 or not phase2:
        return _err("Both phase1 and phase2 results are required.")
    try:
        conclusion = analyzer.generate_multi_conclusion(phase1, phase2)
        llm_context = analyzer.build_llm_context(phase1, phase2)
        ai = analyzer.explain_with_ai(llm_context)
        return jsonify({
            "success": True,
            "conclusion": conclusion,
            "ai_explanation": ai,
            "llm_context": llm_context,
        })
    except ValueError as e:
        return _err(str(e))


@app.route("/api/diagnostics/techniques")
def diagnostics_techniques():
    return jsonify(list_techniques())


@app.route("/api/diagnostics/problems")
def diagnostics_problems():
    return jsonify(list_problems())


@app.route("/api/diagnostics/run", methods=["POST"])
def diagnostics_run():
    """
    Run the full detect→resolve pipeline:
      1. Schedule the workload (chosen scheduler).
      2. Detect synchronization problems in the unsynchronized run.
      3. Evaluate every synchronization technique on the same workload.
    """
    data = request.get_json() or {}
    try:
        processes = validate_processes(data.get("processes", []))
        sched_algos = validate_sched_algorithms(
            [data.get("sched_algorithm", "round_robin")]
        )
        quantum = validate_quantum(data.get("quantum", 2))
        techniques = data.get("techniques")  # None -> all by default
        result = diagnostics.run(
            processes, sched_algos[0], quantum, techniques
        )
        return jsonify({"success": True, **result})
    except ValidationError as e:
        return _err(str(e))
    except ValueError as e:
        return _err(str(e))


@app.route("/api/pipeline/full", methods=["POST"])
def pipeline_full():
    data = request.get_json() or {}
    try:
        sched_algos = validate_sched_algorithms(
            data.get("sched_algorithms") or ["fcfs"]
        )
        sync_algos = validate_sync_algorithms(
            data.get("sync_algorithms") or ["mutex"]
        )
        processes = validate_processes(data.get("processes", []))
        quantum = validate_quantum(data.get("quantum", 2))
        sync_config = validate_sync_config(data.get("sync_config", {}))

        phase1 = execution.run_phase_scheduling_multi(sched_algos, processes, quantum)
        phase2 = execution.run_phase_synchronization_multi(sync_algos, phase1, sync_config)
        conclusion = analyzer.generate_multi_conclusion(phase1, phase2)
        llm_context = analyzer.build_llm_context(phase1, phase2)
        ai = analyzer.explain_with_ai(llm_context)
        return jsonify({
            "success": True,
            "phase1": phase1,
            "phase2": phase2,
            "conclusion": conclusion,
            "ai_explanation": ai,
        })
    except ValidationError as e:
        return _err(str(e))
    except ValueError as e:
        return _err(str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
