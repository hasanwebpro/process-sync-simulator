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

let schedAlgorithms  = [];
let syncAlgorithms   = [];
let phase1Result     = null;   // /api/pipeline/phase1 — scheduling result
let phase2Result     = null;   // primary algorithm's diagnostics result
let phase2AllResults = {};     // { algoId: diagResult } — all algorithms' results for Phase 3 context
let missionRunning   = false;

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

/**
 * Generate a random process table that produces visibly different scheduling
 * outcomes each click.  The algorithm rotates through preset "scenario shapes"
 * (e.g. burst-heavy, staggered arrivals, priority inversion) while randomising
 * the exact numeric values so every run looks distinct.
 */
function loadDemoProcesses() {
  const container = document.getElementById("process-inputs");
  container.innerHTML = "";

  // Helper: random integer in [lo, hi]
  const rnd = (lo, hi) => Math.floor(Math.random() * (hi - lo + 1)) + lo;

  // Pick one of six scenario shapes at random — each produces a noticeably
  // different Gantt chart and set of detected problems.
  const scenarios = [
    // 1. Convoy effect: one very long job blocks several short ones (FCFS vs SJF contrast)
    () => [
      { pid: "P1", arrival: 0,  burst: rnd(8, 14), priority: rnd(3, 5) },
      { pid: "P2", arrival: 1,  burst: rnd(1, 3),  priority: rnd(1, 2) },
      { pid: "P3", arrival: 2,  burst: rnd(2, 4),  priority: rnd(1, 3) },
      { pid: "P4", arrival: 3,  burst: rnd(1, 3),  priority: rnd(2, 4) },
    ],
    // 2. Staggered arrivals: processes trickle in — highlights IDLE gaps
    () => [
      { pid: "P1", arrival: 0,  burst: rnd(3, 6),  priority: rnd(2, 4) },
      { pid: "P2", arrival: rnd(4, 7),  burst: rnd(4, 8),  priority: rnd(1, 3) },
      { pid: "P3", arrival: rnd(8, 12), burst: rnd(2, 5),  priority: rnd(3, 5) },
      { pid: "P4", arrival: rnd(13,17), burst: rnd(3, 6),  priority: rnd(1, 4) },
    ],
    // 3. Equal bursts: fairness test — RR and FCFS produce similar AWT
    () => {
      const b = rnd(4, 7);
      return [
        { pid: "P1", arrival: 0, burst: b,         priority: rnd(1, 4) },
        { pid: "P2", arrival: 1, burst: b,         priority: rnd(1, 4) },
        { pid: "P3", arrival: 2, burst: b,         priority: rnd(1, 4) },
        { pid: "P4", arrival: 3, burst: b,         priority: rnd(1, 4) },
      ];
    },
    // 4. Priority inversion: high-priority job arrives late — shows priority vs FCFS gap
    () => [
      { pid: "P1", arrival: 0,         burst: rnd(6, 10), priority: 4 },
      { pid: "P2", arrival: 1,         burst: rnd(4, 7),  priority: 3 },
      { pid: "P3", arrival: rnd(3, 6), burst: rnd(2, 4),  priority: 1 },
      { pid: "P4", arrival: rnd(5, 8), burst: rnd(3, 6),  priority: 2 },
    ],
    // 5. Five processes — more context switches under RR, richer Gantt
    () => [
      { pid: "P1", arrival: 0,         burst: rnd(4, 8),  priority: rnd(2, 5) },
      { pid: "P2", arrival: rnd(1, 3), burst: rnd(2, 6),  priority: rnd(1, 4) },
      { pid: "P3", arrival: rnd(2, 5), burst: rnd(5, 10), priority: rnd(1, 3) },
      { pid: "P4", arrival: rnd(3, 6), burst: rnd(1, 4),  priority: rnd(2, 5) },
      { pid: "P5", arrival: rnd(4, 7), burst: rnd(3, 7),  priority: rnd(1, 4) },
    ],
    // 6. Short vs long: bimodal — SJF/SRTF give a very different order than FCFS
    () => [
      { pid: "P1", arrival: 0, burst: rnd(1, 3),  priority: rnd(3, 5) },
      { pid: "P2", arrival: 0, burst: rnd(9, 15), priority: rnd(1, 2) },
      { pid: "P3", arrival: 1, burst: rnd(1, 3),  priority: rnd(2, 4) },
      { pid: "P4", arrival: 2, burst: rnd(8, 12), priority: rnd(3, 5) },
    ],
  ];

  const chosen = scenarios[rnd(0, scenarios.length - 1)]();
  chosen.forEach(p => addProcessRow(container, p.pid, p.arrival, p.burst, p.priority));
  setFooter("Random processes generated — run scheduling to see the outcome.");
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

  // Collect all problems that occurred across ANY algorithm run in Phase 2.
  // These are the only ones Phase 3 needs to address.
  const allAlgoEntries = Object.entries(phase2AllResults);

  // Gather union of occurred problem IDs across all algorithms
  const occurredIds = new Set();
  allAlgoEntries.forEach(([, diag]) => {
    (diag.problems || []).filter(p => p.occurred).forEach(p => occurredIds.add(p.id));
  });

  // ── Per-algorithm breakdown rows ─────────────────────────────────────────
  const algoRows = allAlgoEntries.map(([algoId, diag]) => {
    const probs    = (diag.problems || []).filter(p => p.category === "sync");
    const occurred = probs.filter(p => p.occurred);
    const isPrimary = algoId === phase1Result?.primary_algorithm;
    const label    = formatAlgoName(algoId) + (isPrimary ? " ★" : "");

    if (!occurred.length) {
      return `
        <div class="p3-algo-row p3-row-clean">
          <span class="p3-algo-name">${label}</span>
          <span class="p3-row-status ok">✓ No problems detected</span>
        </div>`;
    }

    const chips = occurred.map(p =>
      `<span class="prob-chip prob-occurred" title="${p.explanation || p.name}">● ${p.name}</span>`
    ).join("");

    return `
      <div class="p3-algo-row p3-row-problems">
        <span class="p3-algo-name">${label}</span>
        <div class="p3-row-chips">${chips}</div>
      </div>`;
  }).join("");

  // ── Summary line ──────────────────────────────────────────────────────────
  const totalOccurred = occurredIds.size;
  const summaryHtml = totalOccurred === 0
    ? `<p class="hint" style="color:var(--hud-green);margin-bottom:0.5rem">
         ✓ No synchronization problems were detected under any selected algorithm.
         Synchronization is still recommended as best practice.
       </p>`
    : `<p style="font-size:0.78rem;color:var(--muted);margin-bottom:0.55rem">
         <strong style="color:var(--hud-pink)">${totalOccurred}</strong> unique
         problem(s) exposed — apply synchronization mechanisms below to resolve them.
       </p>`;

  el.innerHTML = summaryHtml + `<div class="p3-algo-breakdown">${algoRows}</div>`;
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

}

// ─────────────────────────────────────────────────────────────────────────────
//  PHASE 2 — Shared Resource Access WITHOUT Synchronization
//            Detects the generic sync problems: race condition, critical
//            section problem, mutual exclusion violation, deadlock,
//            starvation (livelock & busy waiting demoed in Phase 3).
// ─────────────────────────────────────────────────────────────────────────────

async function runPhase2() {
  if (!phase1Result) {
    setFooter("Run CPU Scheduling (Phase 1) first.");
    goToPhase(1);
    return;
  }

  const btn = document.getElementById("btn-phase2-run");
  btn.disabled = true;

  // Use ONLY the algorithms that were actually selected and run in Phase 1.
  // Phase 2 replays the same workload under each of those schedules to show
  // how the different interleavings expose different synchronization problems.
  const selectedAlgos = phase1Result.sched_algorithms || [phase1Result.primary_algorithm];
  setFooter(
    `Detecting problems under ${selectedAlgos.map(formatAlgoName).join(", ")}…`
  );

  const diagResults = {};

  await Promise.all(
    selectedAlgos.map(async (algo) => {
      const r = await API.post("/api/diagnostics/run", {
        processes:       phase1Result.processes,
        sched_algorithm: algo,
        quantum:         getQuantum(),
      });
      if (r.success) {
        diagResults[algo] = r;
      } else {
        console.warn(`Phase 2: diagnostics failed for ${algo}:`, r.error);
      }
    })
  );

  btn.disabled = false;

  // The primary algorithm's result drives Phase 3 and Phase 4.
  // Fall back to any available result if the primary somehow failed.
  const primaryDiag =
    diagResults[phase1Result.primary_algorithm] ||
    Object.values(diagResults)[0];

  if (!primaryDiag) {
    setFooter("⚠ Problem detection failed for all algorithms. Try running Phase 1 again.");
    return;
  }
  phase2Result     = primaryDiag;
  phase2AllResults = diagResults;   // expose to Phase 3 context banner

  // Timeline-row canvas — one animated block per algorithm that succeeded
  await Phase2Viz.renderAll(diagResults, phase1Result.primary_algorithm, phase1Result.processes);

  // Problems table — one block per algorithm so students can compare
  await DiagnosticsViz.renderDetectionMulti(diagResults, phase1Result.primary_algorithm);

  const nOcc    = phase2Result.problems_occurred.length;
  const nAlgos  = Object.keys(diagResults).length;
  document.getElementById("proceed-phase3").style.display = "";
  setFooter(
    `${nOcc} problem(s) exposed under ${formatAlgoName(phase1Result.primary_algorithm)}` +
    (nAlgos > 1 ? ` · ${nAlgos} algorithms compared` : "") +
    ` · Proceed to Phase 3.`
  );

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
    iterations: parseInt(document.getElementById("sync-iterations").value, 10) || 2,
    slots:      parseInt(document.getElementById("sync-slots").value,      10) || 2,
    processes:  getProcessesFromForm().length,
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

  // Unlock compare button now that at least one simulation has run
  const compareBtn = document.getElementById("btn-phase3-compare");
  if (compareBtn) compareBtn.disabled = false;

  if (document.getElementById("slow-teach-mode")?.checked) {
    SyncViz.startPlay();
  }

  if (phase2Result) {
    document.getElementById("proceed-phase4").style.display = "";
  }

  setFooter(
    `${formatAlgoName(algoId)}: ${steps.length} step(s) on your actual processes. ` +
    `Use playback controls to step through the critical section, ` +
    `then click Compare All Techniques for full scoring or proceed to Report.`
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

  // Only include real synchronization SOLUTIONS in the technique comparison.
  // race_condition and deadlock_demo are demonstration scenarios (absence of sync),
  // not solutions — including them in a technique comparison is academically incorrect.
  const COMPARE_TECHNIQUES = [
    "mutex", "binary_semaphore", "counting_semaphore",
    "monitor", "peterson", "dekker",
  ];

  // Collect the union of problems that actually occurred across all Phase 2 runs.
  // Only algorithms that HAD problems need their issues resolved in Phase 3.
  const allAlgoEntries = Object.entries(phase2AllResults);
  const algosSummary   = allAlgoEntries.map(([id, diag]) => {
    const occ = (diag.problems || []).filter(p => p.occurred && p.category === "sync");
    return { id, name: formatAlgoName(id), count: occ.length };
  });
  const algosWithProbs  = algosSummary.filter(a => a.count > 0).map(a => a.name);
  const algosClean      = algosSummary.filter(a => a.count === 0).map(a => a.name);
  const summaryLine     =
    (algosWithProbs.length ? `⚠ Problems found under: ${algosWithProbs.join(", ")}. ` : "") +
    (algosClean.length     ? `✓ No problems under: ${algosClean.join(", ")}. ` : "");

  setFooter(summaryLine + "Running synchronization techniques…");

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
  // with the prevention data already computed by the diagnostics engine.
  // Use phase2Result (primary algorithm) for diagTechMap — this correctly
  // reflects the capability of each technique against the primary schedule's problems.
  const diagTechMap = {};
  (phase2Result.techniques || []).forEach(t => { diagTechMap[t.technique] = t; });

  const enriched = pipelineResults
    .filter(Boolean)
    .map(({ algo, data }) => {
      const simComp  = data.sync_comparison || {};
      const ranking  = (simComp.rankings || []).find(r => r.algorithm === algo) || {};
      const diagTech = diagTechMap[algo] || {};
      const metrics  = ranking.metrics || {};

      return {
        ...diagTech,
        technique:        algo,
        name:             ranking.name      || diagTech.name      || formatAlgoName(algo),
        score:            ranking.score     ?? diagTech.score     ?? 0,
        // ── always guarantee these arrays exist so renderComparison never crashes ──
        prevented:        diagTech.prevented        || [],
        partial:          diagTech.partial          || [],
        not_prevented:    diagTech.not_prevented    || [],
        prevention_ratio: diagTech.prevention_ratio ?? 0,
        // ── real simulation metrics from AnalysisEngine.analyze_sync ──
        sim_metrics: {
          total_steps:      metrics.total_steps      ?? "—",
          cs_entries:       metrics.cs_entries       ?? "—",
          wait_events:      metrics.wait_events      ?? "—",
          busy_wait_steps:  metrics.busy_wait_steps  ?? "—",
          mutual_exclusion: metrics.mutual_exclusion ?? true,
          deadlock_free:    metrics.deadlock_free     ?? true,
          correctness:      metrics.correctness       ?? "—",
        },
        strengths:  ranking.strengths  || diagTech.strengths  || [],
        weaknesses: ranking.weaknesses || diagTech.weaknesses || [],
      };
    })
    .sort((a, b) => b.score - a.score);

  // Merge enriched techniques + best back into phase2Result so Phase 4
  // uses the simulation-based scores, not just the diagnostic estimates.
  if (enriched.length > 0) {
    phase2Result = {
      ...phase2Result,
      techniques: enriched,
      best: enriched[0],
    };
  }

  const enrichedPhase2 = phase2Result;   // same object — both Phase 3 render and Phase 4 now share it
  DiagnosticsViz.renderComparison(enrichedPhase2);

  document.getElementById("comparison-section").style.display = "";
  document.getElementById("performance-section").style.display = "";
  document.getElementById("proceed-phase4").style.display = "";

  const best = enriched[0];
  setFooter(
    summaryLine +
    `${enriched.length} techniques compared. Best = ${best?.name || "—"} ` +
    `(score ${best?.score ?? "—"}/100). Proceed to Phase 4 for the full report.`
  );

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


// ─────────────────────────────────────────────────────────────────────────────
//  Reset — back to clean Phase 1
// ─────────────────────────────────────────────────────────────────────────────

function resetMission() {
  missionRunning = false;
  phase1Result     = null;
  phase2Result     = null;
  phase2AllResults = {};

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
