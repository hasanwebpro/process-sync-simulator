// ─────────────────────────────────────────────────────────────────────────────
//  Theme toggle (runs immediately, before DOM ready, to avoid flash)
// ─────────────────────────────────────────────────────────────────────────────
(function () {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
})();

/**
 * Process Sync Simulator — 4-phase OS workflow
 *
 * Phase 1: Process Creation → CPU Scheduling
 * Phase 2: Same workload WITHOUT sync → expose race conditions, deadlocks, etc.
 * Phase 3: Same workload WITH sync → mutexes, semaphores, monitors protect critical sections
 * Phase 4: Analysis & Report — scheduling results + issues detected + sync applied + recommendations
 *
 * Data flows forward: phase1Result → phase2Result → (phase3 uses phase2 data) → phase4 report
 * All phases operate on the SAME process input table.
 */

const API = {
  async get(path) {
    return (await fetch(path)).json();
  },
  async post(path, body) {
    return (await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })).json();
  },
};

let schedAlgorithms = [];
let syncAlgorithms  = [];
let phase1Result    = null;   // /api/pipeline/phase1 — scheduling result
let phase2Result    = null;   // /api/diagnostics/run — unsynchronized problem detection
let missionRunning  = false;

document.addEventListener("DOMContentLoaded", async () => {
  SchedulerViz.init();
  SyncViz.init();
  Phase1Tutor.init();

  await loadAlgorithms();

  renderProcessInputs();
  bindEvents();
  updateQuantumVisibility();
  updateSpeedLabel();

  setFooter("Configure processes and press Run Scheduling.");
});

// ─────────────────────────────────────────────────────────────────────────────
//  Event binding
// ─────────────────────────────────────────────────────────────────────────────

function bindEvents() {
  document.getElementById("btn-add-process").addEventListener("click", () => {
    const c = document.getElementById("process-inputs");
    if (c.children.length < 8) addProcessRow(c, `P${c.children.length + 1}`, 0, 4, 1);
  });

  document.getElementById("btn-load-demo").addEventListener("click", loadDemoProcesses);

  // Phase 1 — scheduling
  document.getElementById("btn-phase1-run").addEventListener("click", runPhase1);
  document.getElementById("btn-phase1-play").addEventListener("click", () => Phase1Tutor.autoPlayGantt());
  document.getElementById("btn-phase1-step").addEventListener("click", () => {
    Phase1Tutor.nextSegment();
    document.getElementById("btn-phase1-step").disabled =
      Phase1Tutor.segmentIndex >= Phase1Tutor.gantt.length;
  });
  document.getElementById("btn-phase1-pause").addEventListener("click", () => Phase1Tutor.stop());

  // Phase 2 — detect problems without sync
  document.getElementById("btn-phase2-run").addEventListener("click", runPhase2);

  // Phase 3 — sync simulation playback
  document.getElementById("btn-sim-run").addEventListener("click", simulateSync);
  document.getElementById("btn-sim-play").addEventListener("click", () => SyncViz.startPlay());
  document.getElementById("btn-sim-pause").addEventListener("click", () => SyncViz.stopPlay());
  document.getElementById("btn-sim-step").addEventListener("click", () => SyncViz.stepForward());
  document.getElementById("btn-sim-rewind").addEventListener("click", () => SyncViz.resetToStart());

  // Phase 3 — technique comparison
  document.getElementById("btn-phase3-compare").addEventListener("click", runPhase3Compare);

  // Phase 4 — analysis report
  document.getElementById("btn-phase4-run").addEventListener("click", runPhase4);

  // Phase navigation
  document.getElementById("btn-proceed-phase2").addEventListener("click", () => {
    renderProcessContext();
    goToPhase(2);
  });
  document.getElementById("btn-proceed-phase3").addEventListener("click", () => {
    renderPhase3ProblemContext();
    goToPhase(3);
  });
  document.getElementById("btn-proceed-phase4").addEventListener("click", () => goToPhase(4));

  // Theme toggle
  document.getElementById("btn-theme-toggle").addEventListener("click", toggleTheme);
  _syncThemeButton();

  // Global controls
  document.getElementById("btn-full-mission").addEventListener("click", runFullMission);
  document.getElementById("btn-reset-mission").addEventListener("click", resetMission);
  document.getElementById("sched-algorithm-checks").addEventListener("change", updateQuantumVisibility);
  document.getElementById("global-speed").addEventListener("input", updateSpeedLabel);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Theme helpers
// ─────────────────────────────────────────────────────────────────────────────

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  _syncThemeButton();
}

function _syncThemeButton() {
  const theme  = document.documentElement.getAttribute("data-theme") || "light";
  const icon   = document.getElementById("theme-icon");
  const label  = document.getElementById("theme-label");
  if (icon)  icon.textContent  = theme === "dark" ? "☀" : "🌙";
  if (label) label.textContent = theme === "dark" ? "Light" : "Dark";
}

// ─────────────────────────────────────────────────────────────────────────────
//  UI helpers
// ─────────────────────────────────────────────────────────────────────────────

function updateSpeedLabel() {
  const v = document.getElementById("global-speed").value;
  const labels = ["Very slow","Slow","Slow+","Medium","Medium+","Fast","Faster","Quick","Rapid","Max"];
  document.getElementById("speed-label").textContent = labels[parseInt(v, 10) - 1] || "Slow";
}

function setFooter(msg) {
  const el = document.getElementById("footer-status");
  if (el) el.textContent = msg;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function renderInsights(elId, items) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.innerHTML = items.map(x => `
    <div class="insight-chip">
      <span class="insight-key">${x.k}</span>
      <span class="insight-val">${x.v}</span>
    </div>`).join("");
}

async function loadAlgorithms() {
  [schedAlgorithms, syncAlgorithms] = await Promise.all([
    API.get("/api/scheduler/algorithms"),
    API.get("/api/sync/algorithms"),
  ]);

  document.getElementById("sched-algorithm-checks").innerHTML = schedAlgorithms
    .map(a => `
      <label class="algo-check" title="${a.description || ""}">
        <input type="checkbox" value="${a.id}" ${a.id === "round_robin" ? "checked" : ""}>
        <span>${a.name}</span>
      </label>`
    ).join("");

  // Show only real sync techniques (not demo scenarios) in the simulation selector
  const SYNC_TECHNIQUES = new Set([
    "peterson", "dekker", "mutex",
    "binary_semaphore", "counting_semaphore", "monitor",
  ]);

  const sel = document.getElementById("sync-sim-algo");
  if (sel) {
    sel.innerHTML = syncAlgorithms
      .filter(a => SYNC_TECHNIQUES.has(a.id))
      .map(a => `<option value="${a.id}">${a.name}</option>`)
      .join("");
    sel.value = "mutex";
    updateSyncAlgoDesc();
    sel.addEventListener("change", updateSyncAlgoDesc);
  }
}

function getCheckedAlgorithms(containerId) {
  return [...document.querySelectorAll(`#${containerId} input:checked`)].map(el => el.value);
}

function updateQuantumVisibility() {
  const selected = getCheckedAlgorithms("sched-algorithm-checks");
  const needs = selected.some(id => schedAlgorithms.find(x => x.id === id)?.preemptive);
  document.getElementById("quantum-wrap").classList.toggle("hidden", !needs);
}

function loadDemoProcesses() {
  const container = document.getElementById("process-inputs");
  container.innerHTML = "";
  [
    { pid: "P1", arrival: 0, burst: 8, priority: 3 },
    { pid: "P2", arrival: 0, burst: 3, priority: 1 },
    { pid: "P3", arrival: 0, burst: 5, priority: 2 },
    { pid: "P4", arrival: 2, burst: 2, priority: 4 },
  ].forEach(p => addProcessRow(container, p.pid, p.arrival, p.burst, p.priority));
  setFooter("Demo processes loaded.");
}

function renderProcessInputs() { loadDemoProcesses(); }

function addProcessRow(container, pid, arrival, burst, priority) {
  const row = document.createElement("div");
  row.className = "proc-row";
  row.innerHTML = `
    <input type="text"   class="pid"      value="${pid}"      maxlength="6">
    <input type="number" class="arrival"  value="${arrival}"  min="0">
    <input type="number" class="burst"    value="${burst}"    min="1">
    <input type="number" class="priority" value="${priority}" min="1">
    <button type="button" class="remove">×</button>`;
  row.querySelector(".remove").addEventListener("click", () => row.remove());
  container.appendChild(row);
}

function getProcessesFromForm() {
  return [...document.querySelectorAll("#process-inputs .proc-row")].map(row => ({
    pid:      row.querySelector(".pid").value.trim() || "P?",
    arrival:  parseInt(row.querySelector(".arrival").value,  10) || 0,
    burst:    parseInt(row.querySelector(".burst").value,    10) || 1,
    priority: parseInt(row.querySelector(".priority").value, 10) || 1,
  }));
}

function getQuantum() {
  return parseInt(document.getElementById("sched-quantum").value, 10) || 2;
}

function formatAlgoName(id) {
  return (id || "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

/** Switch the visible phase (1–4) and update the stepper. */
function goToPhase(n) {
  document.querySelectorAll(".mission-phase").forEach(p => p.classList.remove("active"));
  const phaseEl = document.getElementById(`phase-${n}`);
  if (phaseEl) phaseEl.classList.add("active");

  document.querySelectorAll(".mission-stepper .step").forEach(s => {
    const ph = parseInt(s.dataset.phase, 10);
    s.classList.remove("active", "locked", "done");
    if      (ph < n)  s.classList.add("done");
    else if (ph === n) s.classList.add("active");
    else               s.classList.add("locked");
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Phase context helpers (same-data banners)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Show a compact read-only summary of the Phase 1 process table + scheduler
 * inside the Phase 2 sidebar — reinforcing "same input data".
 */
function renderProcessContext() {
  const el = document.getElementById("phase2-process-context");
  if (!el || !phase1Result) return;

  const procs  = phase1Result.processes || [];
  const algo   = formatAlgoName(phase1Result.primary_algorithm);
  const order  = (phase1Result.execution_order || []).join(" → ");

  el.innerHTML = `
    <div style="margin-bottom:0.4rem;display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap">
      <span class="badge">${algo}</span>
      <span style="font-size:0.68rem;color:var(--muted)">Order: ${order}</span>
    </div>
    ${procs.map(p =>
      `<span class="proc-ctx-chip" title="AT=${p.arrival} BT=${p.burst} Pri=${p.priority}">
        <strong>${p.pid}</strong>&nbsp;AT:${p.arrival}&nbsp;BT:${p.burst}
       </span>`
    ).join("")}`;
}

/**
 * Show a strip of detected problems from Phase 2 at the top of Phase 3
 * so the student understands which issues the sync mechanisms must address.
 */
function renderPhase3ProblemContext() {
  const el = document.getElementById("phase3-problem-context");
  if (!el) return;

  if (!phase2Result) {
    el.innerHTML = `<p class="hint">Complete Phase 2 to see which problems need to be resolved.</p>`;
    return;
  }

  const all      = phase2Result.problems || [];
  const occurred = all.filter(p => p.occurred);

  if (!occurred.length) {
    el.innerHTML = `<p class="hint" style="color:var(--hud-green)">
      No synchronization problems were detected — synchronization is still a best
      practice to guarantee correctness under any schedule.
    </p>`;
    return;
  }

  el.innerHTML = `
    <p style="font-size:0.78rem;color:var(--muted);margin-bottom:0.5rem">
      Phase 2 exposed <strong style="color:var(--hud-pink)">${occurred.length}</strong>
      problem(s). Use the mechanisms below to resolve them:
    </p>
    <div class="detected-prob-chips">
      ${all.map(p =>
        `<span class="prob-chip ${p.occurred ? "prob-occurred" : "prob-safe"}">
          ${p.occurred ? "●" : "○"}&nbsp;${p.name}
         </span>`
      ).join("")}
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Phase 1 helpers
// ─────────────────────────────────────────────────────────────────────────────

function buildGanttBlocks(comparisons, primaryAlgo) {
  const container = document.getElementById("gantt-charts-container");
  container.innerHTML = "";

  const blocks = {};
  Object.entries(comparisons).forEach(([id, r]) => {
    const safeId = id.replace(/[^a-z0-9_]/gi, "_");

    const seen = [];
    (r.gantt || []).forEach((s) => {
      if (s.pid !== "IDLE" && !seen.includes(s.pid)) seen.push(s.pid);
    });
    const order = seen.join(" → ") || "—";

    const block = document.createElement("div");
    block.className = "gantt-algo-block";
    block.innerHTML = `
      <div class="gantt-algo-header">
        <span class="gantt-algo-label">${formatAlgoName(id)}</span>
        ${id === primaryAlgo ? '<span class="badge">Primary</span>' : ""}
        <span class="gantt-algo-order">${order}</span>
      </div>
      <div class="progress-track">
        <div id="gp-bar-${safeId}" class="progress-fill"></div>
      </div>
      <span id="gp-label-${safeId}" class="progress-label">Waiting…</span>
      <div class="gantt-wrap"><canvas id="gc-${safeId}"></canvas></div>
      <div id="gl-${safeId}" class="gantt-legend"></div>
    `;
    container.appendChild(block);

    const canvas        = document.getElementById(`gc-${safeId}`);
    const legendEl      = document.getElementById(`gl-${safeId}`);
    const progressBar   = document.getElementById(`gp-bar-${safeId}`);
    const progressLabel = document.getElementById(`gp-label-${safeId}`);

    SchedulerViz.registerCanvas(id, canvas, legendEl);

    blocks[id] = { gantt: r.gantt || [], canvas, legendEl, progressBar, progressLabel, label: formatAlgoName(id) };
  });

  return blocks;
}

function renderPhase1Insights(data) {
  const items = Object.entries(data.comparisons || {}).map(([id, r]) => {
    const seen = [];
    (r.gantt || []).forEach(s => {
      if (s.pid !== "IDLE" && !seen.includes(s.pid)) seen.push(s.pid);
    });
    return { k: formatAlgoName(id) + " order", v: seen.join(" → ") || "—" };
  });
  renderInsights("phase1-insights", items);
}

async function renderAllAlgoTables(comparisons) {
  const wrap = document.getElementById("sched-all-algo-tables");
  if (!wrap) return;

  // Build skeletons with empty bodies first
  wrap.innerHTML = Object.entries(comparisons).map(([id]) => {
    const safeId = id.replace(/[^a-z0-9_]/gi, "_");
    return `
      <div class="card hud-card glow-card algo-table-card">
        <div class="card-header">
          <h3>${formatAlgoName(id)}</h3>
          <span class="badge" id="atbadge-${safeId}">calculating…</span>
        </div>
        <div class="table-scroll">
          <table class="metrics-table">
            <thead>
              <tr><th>PID</th><th>AT</th><th>BT</th><th>CT</th><th>TAT</th><th>WT</th><th>RT</th></tr>
            </thead>
            <tbody id="attbody-${safeId}"></tbody>
            <tfoot id="attfoot-${safeId}"></tfoot>
          </table>
        </div>
      </div>`;
  }).join("");

  const rowDelay = Math.max(220, Playback.getStepDelay(Playback.getSpeedSlider()) / 4);

  for (const [id, r] of Object.entries(comparisons)) {
    const safeId = id.replace(/[^a-z0-9_]/gi, "_");
    const tbody  = document.getElementById(`attbody-${safeId}`);
    const tfoot  = document.getElementById(`attfoot-${safeId}`);
    const badge  = document.getElementById(`atbadge-${safeId}`);
    const a      = r.averages || {};

    for (const m of (r.metrics || [])) {
      await Playback.sleep(rowDelay);
      const tr = document.createElement("tr");
      tr.className = "row-appear";
      tr.innerHTML = `
        <td><strong>${m.pid}</strong></td>
        <td>${m.arrival}</td><td>${m.burst}</td>
        <td>${m.completion}</td><td>${m.turnaround}</td>
        <td>${m.waiting}</td><td>${m.response}</td>`;
      tbody.appendChild(tr);
    }

    await Playback.sleep(rowDelay);
    tfoot.innerHTML = `<tr class="row-appear">
      <td colspan="3">Averages</td>
      <td>${a.avg_completion}</td><td>${a.avg_turnaround}</td>
      <td>${a.avg_waiting}</td><td>${a.avg_response}</td>
    </tr>`;
    if (badge) badge.textContent = `AWT ${a.avg_waiting} · ATAT ${a.avg_turnaround}`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  PHASE 1 — Process Creation + CPU Scheduling
// ─────────────────────────────────────────────────────────────────────────────

async function runPhase1() {
  const schedAlgos = getCheckedAlgorithms("sched-algorithm-checks");
  if (!schedAlgos.length) {
    setFooter("Select at least one scheduling algorithm.");
    return;
  }

  const processes = getProcessesFromForm();
  const quantum   = getQuantum();

  const btn = document.getElementById("btn-phase1-run");
  btn.disabled = true;
  setFooter("Running CPU scheduling…");

  const data = await API.post("/api/pipeline/phase1", {
    sched_algorithms: schedAlgos,
    processes,
    quantum,
  });
  btn.disabled = false;

  if (!data.success) {
    setFooter(`⚠ ${data.error || "Scheduling failed."}`);
    return;
  }

  // Store result; reset downstream phases
  phase1Result = data;
  phase2Result = null;

  const primary = data.scheduling;

  // Hide comparison until tables finish animating
  const compareCard = document.getElementById("sched-compare-card");
  compareCard.style.display = "none";

  const blocks = buildGanttBlocks(data.comparisons, data.primary_algorithm);
  Phase1Tutor.resetAll(blocks);

  ["btn-phase1-play","btn-phase1-step","btn-phase1-pause"].forEach(id => {
    const b = document.getElementById(id);
    if (b) b.disabled = false;
  });

  if (Playback.isAutoGantt()) {
    await Phase1Tutor.autoPlayGantt();
  } else {
    Object.entries(blocks).forEach(([id, b]) => {
      SchedulerViz.drawGanttForAlgo(id, b.gantt);
      Playback.setProgressEl(b.progressBar, 100, b.progressLabel, "Gantt ready");
    });
  }

  // Animate tables after Gantt, then reveal comparison
  await renderAllAlgoTables(data.comparisons);

  if (Object.keys(data.comparisons).length > 1) {
    compareCard.style.display = "";
    SchedulerViz.renderComparison(data.comparisons);
  }

  document.getElementById("proceed-phase2").style.display = "";
  setFooter(
    `Scheduling complete (${formatAlgoName(data.primary_algorithm)}). ` +
    `Order: ${(data.execution_order || []).join(" → ")}. ` +
    `Proceed to Phase 2 to detect synchronization problems.`
  );

  if (!missionRunning && document.getElementById("auto-advance").checked) {
    renderProcessContext();
    goToPhase(2);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  PHASE 2 — Shared Resource Access WITHOUT Synchronization
//            Demonstrates: race conditions, CS violations, deadlocks,
//            starvation, livelock, producer-consumer, readers-writers, etc.
// ─────────────────────────────────────────────────────────────────────────────

async function runPhase2() {
  if (!phase1Result) {
    setFooter("Run CPU Scheduling (Phase 1) first.");
    goToPhase(1);
    return;
  }

  const btn = document.getElementById("btn-phase2-run");
  btn.disabled = true;
  setFooter("Replaying workload without synchronization — detecting problems…");

  // Use the SAME processes and the primary scheduling algorithm from Phase 1
  const diag = await API.post("/api/diagnostics/run", {
    processes:       phase1Result.processes,
    sched_algorithm: phase1Result.primary_algorithm,
    quantum:         getQuantum(),
  });
  btn.disabled = false;

  if (!diag.success) {
    setFooter(`⚠ ${diag.error || "Detection failed."}`);
    return;
  }

  phase2Result = diag;

  // Run diagnostics for ALL selected algorithms in parallel
  const allAlgos   = phase1Result.sched_algorithms || [phase1Result.primary_algorithm];
  const diagResults = { [phase1Result.primary_algorithm]: diag };

  await Promise.all(
    allAlgos
      .filter(a => a !== phase1Result.primary_algorithm)
      .map(async (algo) => {
        const r = await API.post("/api/diagnostics/run", {
          processes:       phase1Result.processes,
          sched_algorithm: algo,
          quantum:         getQuantum(),
        });
        if (r.success) diagResults[algo] = r;
      })
  );

  // Timeline-row simulation for each algorithm
  await Phase2Viz.renderAll(diagResults, phase1Result.primary_algorithm, phase1Result.processes);

  // Animate problems table (primary algo)
  await DiagnosticsViz.renderDetection(diag);

  const nOcc = diag.problems_occurred.length;
  document.getElementById("proceed-phase3").style.display = "";
  setFooter(
    `${nOcc} synchronization problem(s) exposed under ` +
    `${formatAlgoName(phase1Result.primary_algorithm)} without synchronization. ` +
    `Proceed to Phase 3 to apply synchronization mechanisms.`
  );

  if (!missionRunning && document.getElementById("auto-advance").checked) {
    renderPhase3ProblemContext();
    goToPhase(3);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  PHASE 3 — Process Synchronization (simulate + compare)
//            Part A: Step-through simulation of a chosen mechanism
//            Part B: Compare all techniques against the detected problems
// ─────────────────────────────────────────────────────────────────────────────

function updateSyncAlgoDesc() {
  const sel    = document.getElementById("sync-sim-algo");
  const descEl = document.getElementById("sync-algo-desc");
  if (!sel || !descEl) return;
  const meta = syncAlgorithms.find(a => a.id === sel.value);
  descEl.textContent = meta?.description || "";
}

function getSyncSimConfig() {
  return {
    iterations:  parseInt(document.getElementById("sync-iterations").value, 10) || 2,
    buffer_size: parseInt(document.getElementById("sync-buffer").value,     10) || 5,
    slots:       parseInt(document.getElementById("sync-slots").value,      10) || 2,
    corrected:   document.getElementById("sync-corrected").checked,
    processes:   getProcessesFromForm().length,
  };
}

function setSimControls(enabled) {
  ["btn-sim-play","btn-sim-pause","btn-sim-step","btn-sim-rewind"].forEach(id => {
    const b = document.getElementById(id);
    if (b) b.disabled = !enabled;
  });
}

/** Part A — Step-by-step simulation using the real Phase 1 process data + schedule. */
async function simulateSync() {
  const algoId = document.getElementById("sync-sim-algo")?.value;
  if (!algoId) return;

  if (!phase1Result) {
    setFooter("Run Phase 1 (CPU Scheduling) first so the simulation uses your real processes.");
    goToPhase(1);
    return;
  }

  const btn = document.getElementById("btn-sim-run");
  btn.disabled = true;
  setSimControls(false);
  SyncViz.stopPlay();

  Playback.setProgress("sync-progress-bar", 0, "sync-progress-label", "Loading…");
  setText("tick-display", "—");
  setFooter(`Running ${formatAlgoName(algoId)} on your Phase 1 processes…`);

  const data = await API.post("/api/pipeline/phase2", {
    sync_algorithms: [algoId],
    phase1:          phase1Result,
    sync_config:     getSyncSimConfig(),
  });
  btn.disabled = false;

  if (!data.success) {
    setFooter(`⚠ ${data.error || "Simulation failed."}`);
    return;
  }

  // integrated_steps weaves the real CPU schedule with sync steps, using actual PIDs
  const steps = data.integrated_steps || [];

  SyncViz.setSteps(steps, formatAlgoName(algoId));
  setSimControls(true);

  if (document.getElementById("slow-teach-mode")?.checked) {
    SyncViz.startPlay();
  }

  setFooter(
    `${formatAlgoName(algoId)}: ${steps.length} step(s) on your actual processes. ` +
    `Use the playback controls to step through how the critical section is protected.`
  );
}

/** Part B — Run every sync technique on the real Phase 1 workload, compare empirically. */
async function runPhase3Compare() {
  if (!phase1Result) {
    setFooter("Run Phase 1 (Scheduling) first.");
    goToPhase(1);
    return;
  }
  if (!phase2Result) {
    setFooter("Running problem detection first…");
    await runPhase2();
    if (!phase2Result) return;
  }

  const COMPARE_TECHNIQUES = ["mutex", "binary_semaphore", "counting_semaphore",
                               "monitor", "peterson", "dekker"];

  setFooter("Running all synchronization techniques on your actual processes…");

  // Run all techniques through the real pipeline in parallel
  const pipelineResults = await Promise.all(
    COMPARE_TECHNIQUES.map(async (algo) => {
      const r = await API.post("/api/pipeline/phase2", {
        sync_algorithms: [algo],
        phase1:          phase1Result,
        sync_config:     getSyncSimConfig(),
      });
      return r.success ? { algo, data: r } : null;
    })
  );

  // Build an enriched comparison by merging real simulation metrics
  // with the prevention data already computed by the diagnostics engine
  const diagTechMap = {};
  (phase2Result.techniques || []).forEach(t => { diagTechMap[t.technique] = t; });

  const enriched = pipelineResults
    .filter(Boolean)
    .map(({ algo, data }) => {
      const simComp   = data.sync_comparison || {};
      const ranking   = (simComp.rankings || []).find(r => r.algorithm === algo) || {};
      const diagTech  = diagTechMap[algo] || {};
      const metrics   = ranking.metrics || {};

      return {
        ...diagTech,
        technique:   algo,
        name:        ranking.name || diagTech.name || formatAlgoName(algo),
        score:       ranking.score ?? diagTech.score ?? 0,
        sim_metrics: {
          total_steps:      metrics.total_steps      ?? "—",
          cs_entries:       metrics.cs_entries       ?? "—",
          wait_events:      metrics.wait_events      ?? "—",
          busy_wait_steps:  metrics.busy_wait_steps  ?? "—",
          mutual_exclusion: metrics.mutual_exclusion ?? true,
          deadlock_free:    metrics.deadlock_free     ?? true,
        },
        strengths:  ranking.strengths  || diagTech.strengths  || [],
        weaknesses: ranking.weaknesses || diagTech.weaknesses || [],
      };
    })
    .sort((a, b) => b.score - a.score);

  // Patch phase2Result with real scores for the comparison render
  const enrichedPhase2 = {
    ...phase2Result,
    techniques: enriched,
    best: enriched[0] || phase2Result.best,
  };

  DiagnosticsViz.renderComparison(enrichedPhase2);

  document.getElementById("comparison-section").style.display = "";
  document.getElementById("performance-section").style.display = "";
  document.getElementById("proceed-phase4").style.display = "";

  const best = enriched[0];
  setFooter(
    `All ${enriched.length} techniques simulated on your actual processes. ` +
    `Best = ${best?.name || "—"} (score ${best?.score ?? "—"}/100). ` +
    `Proceed to Phase 4 for the full report.`
  );

  if (!missionRunning && document.getElementById("auto-advance").checked) {
    goToPhase(4);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  PHASE 4 — Analysis & Report
//            Scheduling results + detected issues + sync applied + recommendations
// ─────────────────────────────────────────────────────────────────────────────

async function runPhase4() {
  if (!phase2Result) {
    setFooter("Complete Phases 1 and 2 first to generate the report.");
    return;
  }

  // Render the full DiagnosticsViz report: executive + before/after + scheduler + recommendations
  DiagnosticsViz.renderReport(
    phase2Result,
    phase1Result?.comparisons || {},
    null
  );

  const ring = document.getElementById("score-ring");
  if (ring) ring.textContent = phase2Result.best?.score ?? "—";

  renderWorkflowSummary();
  setFooter("Analysis & Report complete. Review the findings and recommendations.");
}

/** Render the full-workflow summary banner at the top of Phase 4. */
function renderWorkflowSummary() {
  const el = document.getElementById("workflow-summary");
  if (!el || !phase1Result) return;

  const best   = phase2Result?.best;
  const sched  = formatAlgoName(phase1Result.primary_algorithm);
  const order  = (phase1Result.execution_order || []).join(" → ");
  const avgs   = phase1Result.scheduling?.averages || {};
  const nProbs = (phase2Result?.problems_occurred || []).length;

  el.innerHTML = `
    <div class="wf-banner">
      <div class="wf-step done">
        <span class="wf-num">01</span>
        <div>
          <strong>CPU Scheduling</strong>
          <p>${sched} · AWT: ${avgs.avg_waiting ?? "—"}</p>
          <p>Order: ${order}</p>
        </div>
      </div>
      <div class="wf-arrow">→</div>
      <div class="wf-step ${nProbs > 0 ? "warn" : "done"}">
        <span class="wf-num">02</span>
        <div>
          <strong>Problems Without Sync</strong>
          <p>${nProbs} problem(s) exposed by unsynchronized access</p>
        </div>
      </div>
      <div class="wf-arrow">→</div>
      <div class="wf-step done">
        <span class="wf-num">03</span>
        <div>
          <strong>Synchronization Applied</strong>
          <p>Best: ${best?.name || "—"} · Score: ${best?.score ?? "—"}/100</p>
        </div>
      </div>
      <div class="wf-arrow">→</div>
      <div class="wf-step done">
        <span class="wf-num">04</span>
        <div>
          <strong>Analysis &amp; Report</strong>
          <p>Recommendations below</p>
        </div>
      </div>
    </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Full auto-run (all 4 phases in sequence)
// ─────────────────────────────────────────────────────────────────────────────

async function runFullMission() {
  if (missionRunning) return;
  missionRunning = true;

  const btn = document.getElementById("btn-full-mission");
  btn.disabled = true;
  setFooter("Running all phases automatically…");

  try {
    goToPhase(1);
    await runPhase1();
    if (!phase1Result) {
      setFooter("Stopped — Phase 1 (Scheduling) did not complete.");
      return;
    }
    await Playback.sleep(Playback.getPhaseDelay(Playback.getSpeedSlider()));

    renderProcessContext();
    goToPhase(2);
    await runPhase2();
    if (!phase2Result) {
      setFooter("Stopped — Phase 2 (Problem Detection) did not complete.");
      return;
    }
    await Playback.sleep(Playback.getPhaseDelay(Playback.getSpeedSlider()));

    renderPhase3ProblemContext();
    goToPhase(3);
    await runPhase3Compare();
    await Playback.sleep(Playback.getPhaseDelay(Playback.getSpeedSlider()));

    goToPhase(4);
    await runPhase4();
    setFooter("All phases complete. Review the Analysis & Report.");
  } finally {
    missionRunning = false;
    btn.disabled = false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Reset — back to clean Phase 1
// ─────────────────────────────────────────────────────────────────────────────

function resetMission() {
  missionRunning = false;
  phase1Result   = null;
  phase2Result   = null;

  Phase1Tutor.stop();
  SyncViz.stopPlay();
  DiagnosticsViz.clear();

  ["comparison-section","performance-section"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });

  ["sched-avg-stats","sched-all-algo-tables",
   "sched-compare-table","phase1-tutor-log",
   "phase2-process-context","phase3-problem-context",
   "technique-best-banner","workflow-summary"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = "";
  });

  const ganttContainer = document.getElementById("gantt-charts-container");
  if (ganttContainer) ganttContainer.innerHTML = "";
  SchedulerViz._canvases = {};

  // Destroy comparison charts so stale data doesn't linger
  if (SchedulerViz.chartWt)  { SchedulerViz.chartWt.destroy();  SchedulerViz.chartWt  = null; }
  if (SchedulerViz.chartTat) { SchedulerViz.chartTat.destroy(); SchedulerViz.chartTat = null; }
  SchedulerViz.pidColors = {};

  const detSummary = document.getElementById("detection-summary");
  if (detSummary) {
    detSummary.textContent =
      "Run scheduling first, then click Detect Problems to see which " +
      "synchronization issues arise from concurrent unsynchronized access.";
  }

  setText("score-ring", "—");
  setText("tick-display", "—");

  const compareCard = document.getElementById("sched-compare-card");
  if (compareCard) compareCard.style.display = "none";

  ["proceed-phase2","proceed-phase3","proceed-phase4"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });

  ["btn-phase1-play","btn-phase1-step","btn-phase1-pause"].forEach(id => {
    const b = document.getElementById(id);
    if (b) b.disabled = true;
  });
  setSimControls(false);

  Playback.setProgress("gantt-progress-bar", 0, "gantt-progress-label", "Waiting…");
  Playback.setProgress("sync-progress-bar",  0, "sync-progress-label",  "—");

  // Reset Phase 2 sidebar context to placeholder
  const ctx2 = document.getElementById("phase2-process-context");
  if (ctx2) {
    ctx2.innerHTML = `<span style="font-size:0.68rem;color:var(--muted)">
      Run Phase 1 first to populate this.
    </span>`;
  }

  loadDemoProcesses();
  goToPhase(1);
  setFooter("Reset. Configure processes and run scheduling.");
}
