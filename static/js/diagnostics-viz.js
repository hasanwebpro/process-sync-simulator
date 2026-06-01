/**
 * Diagnostics visualization — problem detection grid, technique comparison
 * dashboard, and the analysis report. Driven entirely by /api/diagnostics/run.
 */

const DiagnosticsViz = {
  charts: {},

  PROBLEM_SHORT: {
    race_condition: "Race",
    cs_violation: "CS Viol",
    deadlock: "Deadlock",
    starvation: "Starve",
    livelock: "Livelock",
    producer_consumer: "Prod/Cons",
    readers_writers: "Read/Write",
    dining_philosophers: "Dining",
    sleeping_barber: "Barber",
  },

  /* ════════════════════════════════════════════════════════════════════
     PHASE 1 — Problem detection grid (Yes/No + metrics + events)
     ════════════════════════════════════════════════════════════════════ */
  renderDetection(diag) {
    const el = document.getElementById("detection-grid");
    if (!el) return;
    const problems = diag.problems || [];
    const occurred = problems.filter((p) => p.occurred).length;
    const algo = (diag.scheduler?.algorithm || "").toUpperCase().replace(/_/g, " ");

    const summary = document.getElementById("detection-summary");
    if (summary) {
      const preemptive = diag.scheduler?.preemptive;
      summary.innerHTML =
        `<strong>${occurred}</strong> of ${problems.length} synchronization ` +
        `problems are exposed when this workload runs under ` +
        `<strong>${algo}</strong> without synchronization. ` +
        (preemptive
          ? "Preemptive scheduling creates more interleaving, surfacing more problems."
          : "Non-preemptive scheduling reduces interleaving, so fewer problems surface."
        );
    }

    el.innerHTML = problems
      .map((p) => {
        const yes = p.occurred;
        const metricChips = Object.entries(p.metrics || {})
          .map(
            ([k, v]) =>
              `<span class="dx-metric"><span class="dx-mk">${k}</span><span class="dx-mv">${v}</span></span>`
          )
          .join("");
        const events = (p.events || [])
          .map((e) => `<li>${e}</li>`)
          .join("");
        return `
          <div class="dx-card ${yes ? "dx-yes" : "dx-no"}">
            <div class="dx-card-head">
              <span class="dx-name">${p.name}</span>
              <span class="dx-flag ${yes ? "flag-yes" : "flag-no"}">${yes ? "YES" : "NO"}</span>
            </div>
            <div class="dx-cat">${p.category === "schedule" ? "schedule-driven" : "classic problem"}${
              yes ? ` · ${p.severity}` : ""
            }</div>
            <p class="dx-explain">${p.explanation || ""}</p>
            ${metricChips ? `<div class="dx-metrics">${metricChips}</div>` : ""}
            ${
              events
                ? `<details class="dx-events"><summary>Key events</summary><ul>${events}</ul></details>`
                : ""
            }
          </div>`;
      })
      .join("");
  },

  /* ════════════════════════════════════════════════════════════════════
     PHASE 2 — Technique comparison dashboard
     ════════════════════════════════════════════════════════════════════ */
  renderComparison(diag) {
    const techniques = diag.techniques || [];
    const occurred = (diag.problems || []).filter((p) => p.occurred);
    const best = diag.best;

    this._renderBestBanner(best, occurred);
    this._renderPreventionMatrix(techniques, occurred);
    this._renderTechniqueTable(techniques, occurred.length);
    this._renderScoreChart(techniques);
    this._renderCostChart(techniques);
  },

  _renderBestBanner(best, occurred) {
    const el = document.getElementById("technique-best-banner");
    if (!el || !best) return;
    const prevented = best.prevented.length;
    el.innerHTML = `
      <div class="best-tech-icon">★</div>
      <div class="best-tech-body">
        <div class="best-tech-title">Best technique: ${best.name}</div>
        <div class="best-tech-sub">
          Score ${best.score}/100 · prevents ${prevented}/${occurred.length} detected problems ·
          overhead ${best.metrics.overhead} ticks · fairness ${best.metrics.fairness}
        </div>
      </div>`;
  },

  _cell(cap) {
    if (cap === "prevents") return `<td class="cap cap-yes" title="Prevents">✓</td>`;
    if (cap === "partial") return `<td class="cap cap-part" title="Partial">~</td>`;
    return `<td class="cap cap-no" title="Does not prevent">✗</td>`;
  },

  _capOf(tech, problemId) {
    if (tech.prevented.includes(problemId)) return "prevents";
    if (tech.partial.includes(problemId)) return "partial";
    return "no";
  },

  _renderPreventionMatrix(techniques, occurred) {
    const el = document.getElementById("prevention-matrix");
    if (!el) return;
    if (!occurred.length) {
      el.innerHTML = "<p class='muted'>No problems were detected to prevent.</p>";
      return;
    }
    const head = occurred
      .map((p) => `<th title="${p.name}">${this.PROBLEM_SHORT[p.id] || p.name}</th>`)
      .join("");
    const rows = techniques
      .map((t, i) => {
        const cells = occurred.map((p) => this._cell(this._capOf(t, p.id))).join("");
        return `<tr class="${i === 0 ? "row-best" : ""}">
          <td class="tech-name">${t.name}${i === 0 ? " ★" : ""}</td>
          ${cells}
        </tr>`;
      })
      .join("");
    el.innerHTML = `
      <div class="table-scroll">
        <table class="metrics-table matrix-table">
          <thead><tr><th class="tech-col">Technique</th>${head}</tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="matrix-legend">
        <span><i class="cap-dot cap-yes">✓</i> Prevents</span>
        <span><i class="cap-dot cap-part">~</i> Partial</span>
        <span><i class="cap-dot cap-no">✗</i> No</span>
      </div>`;
  },

  _renderTechniqueTable(techniques, nOccurred) {
    const el = document.getElementById("technique-table");
    if (!el) return;
    const rows = techniques
      .map((t, i) => {
        const m = t.metrics;
        return `<tr class="${i === 0 ? "row-best" : ""}">
          <td class="tech-name">${t.name}${i === 0 ? " ★" : ""}</td>
          <td>${t.prevented.length}/${nOccurred}</td>
          <td>${m.throughput}</td>
          <td>${m.avg_waiting}</td>
          <td>${m.avg_response}</td>
          <td>${m.avg_turnaround}</td>
          <td>${m.cpu_util}%</td>
          <td>${m.fairness}</td>
          <td>${m.overhead}</td>
          <td><span class="score-badge">${t.score}</span></td>
        </tr>`;
      })
      .join("");
    el.innerHTML = `
      <div class="table-scroll">
        <table class="metrics-table">
          <thead>
            <tr>
              <th>Technique</th><th>Prevents</th><th>Throughput</th>
              <th>Avg WT</th><th>Avg RT</th><th>Avg TAT</th>
              <th>CPU %</th><th>Fairness</th><th>Overhead</th><th>Score</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  },

  _renderScoreChart(techniques) {
    const canvas = document.getElementById("technique-score-chart");
    if (!canvas) return;
    if (this.charts.score) this.charts.score.destroy();
    this.charts.score = new Chart(canvas, {
      type: "bar",
      data: {
        labels: techniques.map((t) => t.name),
        datasets: [
          {
            label: "Effectiveness score",
            data: techniques.map((t) => t.score),
            backgroundColor: techniques.map((_, i) =>
              i === 0 ? "rgba(57,255,20,0.85)" : "rgba(255,45,120,0.55)"
            ),
            borderRadius: 8,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, title: { display: true, text: "Effectiveness Score (0–100)", color: "#EEE0FF" } },
        scales: {
          x: { max: 100, ticks: { color: "#9070B0" }, grid: { color: "rgba(58,24,96,0.5)" } },
          y: { ticks: { color: "#EEE0FF" }, grid: { display: false } },
        },
      },
    });
  },

  _renderCostChart(techniques) {
    const canvas = document.getElementById("technique-cost-chart");
    if (!canvas) return;
    if (this.charts.cost) this.charts.cost.destroy();
    this.charts.cost = new Chart(canvas, {
      type: "bar",
      data: {
        labels: techniques.map((t) => t.name),
        datasets: [
          {
            label: "Overhead (ticks)",
            data: techniques.map((t) => t.metrics.overhead),
            backgroundColor: "rgba(255,45,120,0.65)",
            borderRadius: 6,
          },
          {
            label: "Avg waiting",
            data: techniques.map((t) => t.metrics.avg_waiting),
            backgroundColor: "rgba(0,212,212,0.65)",
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#EEE0FF" } },
          title: { display: true, text: "Cost: Overhead vs Waiting", color: "#EEE0FF" },
        },
        scales: {
          x: { ticks: { color: "#9070B0", maxRotation: 45, minRotation: 30 }, grid: { display: false } },
          y: { ticks: { color: "#9070B0" }, grid: { color: "rgba(58,24,96,0.5)" } },
        },
      },
    });
  },

  /* ════════════════════════════════════════════════════════════════════
     PHASE 3 — Analysis report (before/after + recommendation)
     ════════════════════════════════════════════════════════════════════ */
  renderReport(diag, schedComparison, ai) {
    this._reportExecutive(diag, ai);
    this._reportBeforeAfter(diag);
    this._reportScheduler(schedComparison, diag);
    this._reportRecommendation(diag);
  },

  _reportExecutive(diag, ai) {
    const el = document.getElementById("report-executive");
    if (!el) return;
    const rec = diag.recommendation || {};
    const aiHtml =
      ai?.text && ai?.source === "openai"
        ? `<div class="ai-box"><span class="source-tag">AI Explanation</span><p>${ai.text}</p></div>`
        : "";
    el.innerHTML = `
      <div class="conclusion-banner">
        <div class="conclusion-banner-text">
          <h4>Analysis Report</h4>
          <span class="conclusion-sub">CPU Scheduling + Process Synchronization</span>
        </div>
      </div>
      <div class="conclusion-summary-block">
        <p class="conclusion-hero">${rec.summary || "Run the diagnostics to generate the report."}</p>
      </div>
      ${aiHtml}`;
  },

  _reportBeforeAfter(diag) {
    const el = document.getElementById("report-before-after");
    if (!el) return;
    const occurred = (diag.problems || []).filter((p) => p.occurred);
    const best = diag.best || {};
    const base = diag.base_metrics || {};
    const bm = best.metrics || {};

    const problemList = occurred.length
      ? occurred.map((p) => `<li>${p.name} <span class="muted">(${p.severity})</span></li>`).join("")
      : "<li>None detected</li>";
    const preventedList = (best.prevented || []).length
      ? best.prevented.map((id) => `<li>${(diag.problems.find((p) => p.id === id) || {}).name || id}</li>`).join("")
      : "<li>—</li>";

    el.innerHTML = `
      <h4>Before vs After Synchronization</h4>
      <div class="ba-grid">
        <div class="ba-col ba-before">
          <div class="ba-title">Without synchronization</div>
          <p style="font-size:0.72rem;color:var(--muted);margin-bottom:0.4rem">
            Problems exposed by concurrent unsynchronized access:
          </p>
          <ul class="ba-list">${problemList}</ul>
          <div class="ba-metrics">
            Avg WT ${base.avg_waiting} · CPU ${base.cpu_util}% · throughput ${base.throughput}
          </div>
        </div>
        <div class="ba-col ba-after">
          <div class="ba-title">With ${best.name || "best technique"}</div>
          <div class="ba-sub">Problems prevented by this technique:</div>
          <ul class="ba-list">${preventedList}</ul>
          <div class="ba-metrics">
            Avg WT ${bm.avg_waiting} · CPU ${bm.cpu_util}% · throughput ${bm.throughput} · overhead ${bm.overhead}
          </div>
        </div>
      </div>`;
  },

  _reportScheduler(schedComparison, diag) {
    const el = document.getElementById("report-scheduler");
    if (!el) return;
    const comparisons = schedComparison || {};
    const primary = diag.scheduler?.algorithm;
    // Only worth showing when more than one scheduler was compared.
    if (Object.keys(comparisons).length < 2) {
      el.innerHTML = "";
      return;
    }
    let rows = "";
    for (const [id, data] of Object.entries(comparisons)) {
      const a = data.averages || {};
      const isBest = id === primary;
      rows += `<tr class="${isBest ? "row-best" : ""}">
        <td>${id.toUpperCase().replace(/_/g, " ")} ${isBest ? "★" : ""}</td>
        <td>${a.avg_completion ?? "—"}</td>
        <td>${a.avg_turnaround ?? "—"}</td>
        <td>${a.avg_waiting ?? "—"}</td>
        <td>${a.avg_response ?? "—"}</td>
        <td>${a.throughput ?? "—"}</td>
      </tr>`;
    }
    if (!rows) {
      el.innerHTML = "";
      return;
    }
    el.innerHTML = `
      <h4>Scheduler Comparison</h4>
      <p class="report-p">
        The primary scheduler (★) was used for the problem detection above.
        Scheduling determines execution order and interleaving — it does not
        directly cause synchronization problems, but controls how often processes
        compete for shared resources.
      </p>
      <div class="table-scroll">
        <table class="metrics-table">
          <thead><tr><th>Algorithm</th><th>Avg CT</th><th>Avg TAT</th><th>Avg WT</th><th>Avg RT</th><th>Throughput</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  },

  _reportRecommendation(diag) {
    const el = document.getElementById("report-recommendation");
    if (!el) return;
    const rec = diag.recommendation || {};
    const bullets = (rec.bullets || []).map((b) => `<li>${b}</li>`).join("");
    el.innerHTML = `
      <h4>Recommendation</h4>
      <div class="rec-box">
        <ul class="rec-list">${bullets}</ul>
      </div>`;
  },

  clear() {
    [
      "detection-grid",
      "detection-summary",
      "technique-best-banner",
      "prevention-matrix",
      "technique-table",
      "report-executive",
      "report-before-after",
      "report-scheduler",
      "report-recommendation",
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = "";
    });
    Object.values(this.charts).forEach((c) => c && c.destroy());
    this.charts = {};
  },
};
