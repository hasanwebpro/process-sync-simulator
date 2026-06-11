/**
 * Diagnostics visualization — problem detection grid, technique comparison
 * dashboard, and the analysis report. Driven entirely by /api/diagnostics/run.
 */

const DiagnosticsViz = {
  charts: {},

  PROBLEM_SHORT: {
    race_condition: "Race",
    critical_section: "CS Problem",
    mutual_exclusion: "ME Viol",
    deadlock: "Deadlock",
    starvation: "Starve",
    livelock: "Livelock",
    busy_waiting: "Busy Wait",
  },

  SHORT_WHY: {
    // ── Detectable from CPU scheduling traces ─────────────────────────────
    race_condition:   "Concurrent read-modify-write — one process overwrites another's result (Silberschatz §6.1).",
    critical_section: "Processes contend for the same shared resource with no entry protocol (Silberschatz §6.2).",
    mutual_exclusion: "Two processes inside the critical section simultaneously — mutual exclusion violated.",
    deadlock:         "Circular wait: each process holds what the other needs (Silberschatz §8.3).",
    starvation:       "Process waits far longer than peers — scheduler systematically bypasses it (Silberschatz §6.6).",
    // ── Not detectable from scheduling traces — demonstrated in Phase 3 ──
    livelock:         "Not detectable from scheduling trace (requires voluntary-yield retry code). See the Phase 3 Livelock Demo.",
    busy_waiting:     "A property of spin-based locks, not unsynchronized execution. See the Phase 3 Busy Waiting Demo.",
  },

  /* ════════════════════════════════════════════════════════════════════
     PHASE 2 — Animated detection table, one block per algorithm
     ════════════════════════════════════════════════════════════════════ */

  /**
   * Render a separate detection block for every algorithm in diagResults.
   * Each block shows ✓/✗ for every sync problem with an explanation
   * tailored to whether the problem occurred or not under that schedule.
   *
   * @param {Object} diagResults  — { algoId: diagResponse, … }
   * @param {string} primaryAlgo  — the primary algorithm from Phase 1
   */
  async renderDetectionMulti(diagResults, primaryAlgo) {
    const el = document.getElementById("detection-grid");
    if (!el) return;
    el.innerHTML = "";

    const delay   = Math.max(180, Playback.getStepDelay(Playback.getSpeedSlider()) / 5);
    const entries = Object.entries(diagResults);

    for (const [algoId, diag] of entries) {
      const problems  = diag.problems || [];
      const syncProbs = problems.filter(p => p.category === "sync");
      const nOcc      = syncProbs.filter(p => p.occurred).length;
      const isPrimary = algoId === primaryAlgo;
      const algoName  = algoId.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      const safeId    = algoId.replace(/[^a-z0-9_]/gi, "_");

      // ── Build the block ─────────────────────────────────────────────
      const block = document.createElement("div");
      block.className = "dx-algo-block";
      block.innerHTML = `
        <div class="dx-algo-header">
          <span class="dx-algo-label">${algoName}</span>
          ${isPrimary ? '<span class="badge badge-warn">Primary</span>' : ""}
          <span class="dx-algo-summary ${nOcc > 0 ? "bad" : "ok"}">
            ${nOcc > 0 ? `⚠ ${nOcc} / ${syncProbs.length} problems exposed` : `✓ 0 / ${syncProbs.length} problems exposed`}
          </span>
        </div>
        <table class="dx-table">
          <thead>
            <tr>
              <th class="dx-th-name">Synchronization Problem</th>
              <th class="dx-th-status">Status</th>
              <th class="dx-th-why">Why it occurs / does not occur under this schedule</th>
            </tr>
          </thead>
          <tbody id="dx-tbody-${safeId}"></tbody>
        </table>`;
      el.appendChild(block);

      // ── Animate rows one by one ──────────────────────────────────────
      const tbody = document.getElementById(`dx-tbody-${safeId}`);
      for (const p of syncProbs) {
        await Playback.sleep(delay);

        // Occurring problems: use the short generic "why" label.
        // Non-occurring problems: use the backend's specific explanation
        // (e.g. "No race condition exposed under this schedule").
        const why = p.occurred
          ? (this.SHORT_WHY[p.id] || (p.explanation || "").slice(0, 120))
          : ((p.explanation || this.SHORT_WHY[p.id] || "").slice(0, 120));

        const tr = document.createElement("tr");
        tr.className = `dx-row ${p.occurred ? "dx-row-bad" : "dx-row-ok"} row-appear`;
        tr.innerHTML = `
          <td class="dx-prob-name">${p.name}</td>
          <td class="dx-status-cell">
            <span class="${p.occurred ? "dx-cross" : "dx-tick"}">${p.occurred ? "✗" : "✓"}</span>
          </td>
          <td class="dx-why-cell">${why}</td>`;
        tbody.appendChild(tr);
      }
    }

    // ── Update summary badge (use primary algo) ──────────────────────
    const primaryDiag    = diagResults[primaryAlgo] || Object.values(diagResults)[0];
    const primarySyncPr  = (primaryDiag?.problems || []).filter(p => p.category === "sync");
    const primaryOcc     = primarySyncPr.filter(p => p.occurred).length;
    const primaryName    = (primaryAlgo || "").toUpperCase().replace(/_/g, " ");
    const summary        = document.getElementById("detection-summary");
    if (summary) {
      summary.textContent = entries.length > 1
        ? `${primaryOcc}/${primarySyncPr.length} (${primaryName}) · ${entries.length} algorithms`
        : `${primaryOcc} / ${primarySyncPr.length} sync problems · ${primaryName}`;
    }
  },

  /** Single-algo wrapper kept for backward compatibility. */
  async renderDetection(diag) {
    await this.renderDetectionMulti({ [diag.scheduler?.algorithm || "primary"]: diag }, diag.scheduler?.algorithm);
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
    const prevented = (best.prevented || []).length;           // ← null-safe
    const overhead  = best.metrics?.overhead  ?? best.sim_metrics?.wait_events  ?? "—";
    const fairness  = best.metrics?.fairness  ?? "—";
    el.innerHTML = `
      <div class="best-tech-icon">★</div>
      <div class="best-tech-body">
        <div class="best-tech-title">Best technique: ${best.name}</div>
        <div class="best-tech-sub">
          Score ${best.score}/100 · prevents ${prevented}/${occurred.length} detected problems ·
          overhead ${overhead} · fairness ${fairness}
        </div>
      </div>`;
  },

  _cell(cap) {
    if (cap === "prevents") return `<td class="cap cap-yes" title="Prevents">✓</td>`;
    if (cap === "partial") return `<td class="cap cap-part" title="Partial">~</td>`;
    return `<td class="cap cap-no" title="Does not prevent">✗</td>`;
  },

  _capOf(tech, problemId) {
    if ((tech.prevented || []).includes(problemId)) return "prevents";   // ← null-safe
    if ((tech.partial   || []).includes(problemId)) return "partial";    // ← null-safe
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

    // Detect whether we have real simulation metrics (from pipeline) or analytical
    const hasSimMetrics = techniques.some(t => t.sim_metrics);

    const rows = techniques
      .map((t, i) => {
        const prevented = (t.prevented || []).length;
        if (hasSimMetrics) {
          const s = t.sim_metrics || {};
          return `<tr class="${i === 0 ? "row-best" : ""}">
            <td class="tech-name">${t.name}${i === 0 ? " ★" : ""}</td>
            <td>${prevented}/${nOccurred}</td>
            <td>${s.cs_entries ?? "—"}</td>
            <td>${s.wait_events ?? "—"}</td>
            <td>${s.busy_wait_steps ?? "—"}</td>
            <td>${s.mutual_exclusion ? "✓" : "✗"}</td>
            <td>${s.deadlock_free ? "✓" : "✗"}</td>
            <td>${s.total_steps ?? "—"}</td>
            <td><span class="score-badge">${t.score}</span></td>
          </tr>`;
        }
        const m = t.metrics || {};
        return `<tr class="${i === 0 ? "row-best" : ""}">
          <td class="tech-name">${t.name}${i === 0 ? " ★" : ""}</td>
          <td>${prevented}/${nOccurred}</td>
          <td>${m.throughput ?? "—"}</td>
          <td>${m.avg_waiting ?? "—"}</td>
          <td>${m.avg_response ?? "—"}</td>
          <td>${m.cpu_util ?? "—"}%</td>
          <td>${m.overhead ?? "—"}</td>
          <td><span class="score-badge">${t.score}</span></td>
        </tr>`;
      })
      .join("");

    if (hasSimMetrics) {
      el.innerHTML = `
        <div class="table-scroll">
          <table class="metrics-table">
            <thead>
              <tr>
                <th>Technique</th><th>Prevents</th><th>CS Entries</th>
                <th>Wait Events</th><th>Busy-Wait</th>
                <th>Mutual Excl.</th><th>Deadlock Free</th><th>Total Steps</th><th>Score</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    } else {
      el.innerHTML = `
        <div class="table-scroll">
          <table class="metrics-table">
            <thead>
              <tr>
                <th>Technique</th><th>Prevents</th><th>Throughput</th>
                <th>Avg WT</th><th>Avg RT</th><th>CPU %</th><th>Overhead</th><th>Score</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    }
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
            data: techniques.map((t) => t.metrics?.overhead ?? 0),   // null-safe
            backgroundColor: "rgba(255,45,120,0.65)",
            borderRadius: 6,
          },
          {
            label: "Avg waiting",
            data: techniques.map((t) => t.metrics?.avg_waiting ?? 0), // null-safe
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
     PHASE 4 — Analysis report
     Structure: header + takeaway → key findings → before/after →
     observations → impact analysis → scheduler comparison →
     recommendations → conclusion
     ════════════════════════════════════════════════════════════════════ */

  /** Real-world consequence of each generic synchronization problem. */
  PROBLEM_IMPACT: {
    race_condition:   "Silent data corruption — e.g. two transactions updating the same account balance produce a wrong final amount with no error raised.",
    critical_section: "Shared state cannot be trusted — every access to the resource needs an entry protocol before results are reliable.",
    mutual_exclusion: "Invariants break mid-update — another process reads or writes a structure while it is in an inconsistent half-modified state.",
    deadlock:         "System freeze — the affected processes hang forever holding their resources; recovery requires killing processes or restarting.",
    starvation:       "Unbounded delays — a request can wait indefinitely behind favoured peers, causing timeouts and unresponsive services.",
    livelock:         "CPU burns while nothing completes — processes stay active in a retry storm yet no work finishes.",
    busy_waiting:     "Wasted CPU capacity — cycles spent spinning on a lock are stolen from useful work, degrading whole-system throughput.",
  },

  _occurred(diag) {
    return (diag.problems || []).filter((p) => p.occurred);
  },

  _takeaway(diag) {
    const occurred = this._occurred(diag);
    const total = (diag.problems || []).length || 7;
    const best = diag.best || {};
    if (occurred.length) {
      return `Unsynchronized access exposed ${occurred.length} of ${total} generic synchronization problems — ` +
             `${best.name || "the best technique"} resolved them most effectively (${best.score ?? "—"}/100).`;
    }
    return `No problems surfaced under this schedule — but correctness must never depend on scheduling luck; ` +
           `${best.name || "a blocking primitive"} remains the recommended protection.`;
  },

  renderReport(diag, schedComparison, ai) {
    this._reportHeader(diag, ai);
    this._reportKeyFindings(diag);
    this._reportBeforeAfter(diag);
    this._reportObservations(diag);
    this._reportImpact(diag);
    this._reportScheduler(schedComparison, diag);
    this._reportRecommendation(diag);
    this._reportConclusion(diag);
  },

  _reportHeader(diag, ai) {
    const el = document.getElementById("report-executive");
    if (!el) return;
    const rec = diag.recommendation || {};
    const sched = (diag.scheduler?.algorithm || "").toUpperCase().replace(/_/g, " ");
    const date = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
    const aiHtml =
      ai?.text && ai?.source === "openai"
        ? `<div class="ai-box"><span class="source-tag">AI Explanation</span><p>${ai.text}</p></div>`
        : "";
    el.innerHTML = `
      <div class="conclusion-banner">
        <div class="conclusion-banner-text">
          <h4>Synchronization Analysis Report</h4>
          <span class="conclusion-sub">Generic OS Synchronization Problems · Schedule: ${sched} · ${date}</span>
        </div>
      </div>
      <div class="report-takeaway">
        <span class="takeaway-label">One-line takeaway</span>
        <p class="takeaway-text">${this._takeaway(diag)}</p>
      </div>
      <div class="conclusion-summary-block">
        <p class="conclusion-body">${rec.summary || "Run the diagnostics to generate the report."}</p>
      </div>
      ${aiHtml}`;
  },

  _reportKeyFindings(diag) {
    const el = document.getElementById("report-key-findings");
    if (!el) return;
    const occurred = this._occurred(diag);
    const total = (diag.problems || []).length || 7;
    const best = diag.best || {};
    const byId = {};
    (diag.problems || []).forEach((p) => { byId[p.id] = p; });

    const findings = [];

    findings.push({
      tag: "Detection",
      text: occurred.length
        ? `<strong>${occurred.length} of ${total}</strong> generic synchronization problems occurred: ${occurred.map((p) => p.name).join(", ")}.`
        : `<strong>0 of ${total}</strong> problems occurred under this schedule — the workload ran without harmful interleaving this time.`,
    });

    const race = byId.race_condition;
    if (race?.occurred) {
      const m = race.metrics || {};
      findings.push({
        tag: "Race Condition",
        text: `<strong>${m["Lost updates"] ?? "—"} update(s) lost</strong> — the shared counter ended at ${m["Actual counter"] ?? "—"} instead of ${m["Expected counter"] ?? "—"}.`,
      });
    }
    const me = byId.mutual_exclusion;
    if (me?.occurred) {
      findings.push({
        tag: "Mutual Exclusion",
        text: `Two processes were inside the critical section simultaneously <strong>${(me.metrics || {})["Overlapping entries"] ?? "—"} time(s)</strong>.`,
      });
    }
    const dl = byId.deadlock;
    if (dl?.occurred) {
      findings.push({
        tag: "Deadlock",
        text: `Circular wait formed: <strong>${(dl.metrics || {})["Cycle"] ?? "P0↔P1"}</strong> — neither process could ever proceed.`,
      });
    }
    const sv = byId.starvation;
    if (sv?.occurred) {
      findings.push({
        tag: "Starvation",
        text: `Process(es) <strong>${(sv.metrics || {})["Starved"] ?? "—"}</strong> waited far beyond the average (${(sv.metrics || {})["Max waiting"] ?? "—"} vs avg ${(sv.metrics || {})["Avg waiting"] ?? "—"} ticks).`,
      });
    }

    if (best.name) {
      const prevented = (best.prevented || []).length;
      findings.push({
        tag: "Best Technique",
        text: `<strong>${best.name}</strong> scored <strong>${best.score ?? "—"}/100</strong>` +
              (occurred.length ? `, preventing ${prevented}/${occurred.length} detected problems.` : `.`),
      });
    }

    // Busy-waiting cost: compare spin-based vs blocking technique scores when available
    const techs = diag.techniques || [];
    const spin = techs.filter((t) => ["peterson", "dekker", "spinlock"].includes(t.technique));
    const block = techs.filter((t) => ["mutex", "binary_semaphore", "monitor", "counting_semaphore", "condition_variable"].includes(t.technique));
    if (spin.length && block.length) {
      const avgSpin = spin.reduce((s, t) => s + (t.score || 0), 0) / spin.length;
      const avgBlock = block.reduce((s, t) => s + (t.score || 0), 0) / block.length;
      if (avgBlock > avgSpin) {
        findings.push({
          tag: "Busy Waiting",
          text: `Blocking primitives outscored spin-based ones by <strong>${(avgBlock - avgSpin).toFixed(1)} points</strong> on average — spinning wastes CPU cycles that blocking returns to useful work.`,
        });
      }
    }

    el.innerHTML = `
      <h4>Key Findings</h4>
      <ol class="findings-list">
        ${findings.map((f) => `
          <li class="finding-item">
            <span class="finding-tag">${f.tag}</span>
            <span class="finding-text">${f.text}</span>
          </li>`).join("")}
      </ol>`;
  },

  _reportBeforeAfter(diag) {
    const el = document.getElementById("report-before-after");
    if (!el) return;
    const occurred = (diag.problems || []).filter((p) => p.occurred);
    const best = diag.best || {};
    const base = diag.base_metrics || {};
    // prefer sim_metrics (real simulation) over analytical metrics
    const bm  = best.metrics     || {};
    const bsm = best.sim_metrics || {};

    const problemList = occurred.length
      ? occurred.map((p) => `<li>${p.name} <span class="muted">(${p.severity})</span></li>`).join("")
      : "<li>None detected</li>";
    const preventedList = (best.prevented || []).length
      ? (best.prevented || []).map((id) => `<li>${(diag.problems.find((p) => p.id === id) || {}).name || id}</li>`).join("")
      : "<li>—</li>";

    // Build "after" metric line — use simulation values when available
    const afterMetrics = bsm.total_steps
      ? `Steps: ${bsm.total_steps} · CS entries: ${bsm.cs_entries ?? "—"} · Wait events: ${bsm.wait_events ?? "—"} · Mutual exclusion: ${bsm.mutual_exclusion ? "✓" : "✗"}`
      : `Avg WT ${bm.avg_waiting ?? "—"} · CPU ${bm.cpu_util ?? "—"}% · overhead ${bm.overhead ?? "—"}`;

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
            Avg WT ${base.avg_waiting ?? "—"} · CPU ${base.cpu_util ?? "—"}% · throughput ${base.throughput ?? "—"}
          </div>
        </div>
        <div class="ba-col ba-after">
          <div class="ba-title">With ${best.name || "best technique"}</div>
          <div class="ba-sub">Problems prevented by this technique:</div>
          <ul class="ba-list">${preventedList}</ul>
          <div class="ba-metrics">${afterMetrics}</div>
        </div>
      </div>`;
  },

  _reportObservations(diag) {
    const el = document.getElementById("report-observations");
    if (!el) return;
    const sched = (diag.scheduler?.algorithm || "").toUpperCase().replace(/_/g, " ");
    const preemptive = !!diag.scheduler?.preemptive;
    const base = diag.base_metrics || {};
    const best = diag.best || {};
    const contention = diag.contention;

    const obs = [];
    obs.push(
      preemptive
        ? `${sched} is <strong>preemptive</strong> — frequent context switches interleaved the processes mid-execution, which is exactly the condition under which shared-resource problems surface.`
        : `${sched} is <strong>non-preemptive</strong> — each process ran to completion before the next started, so concurrency problems latent in the code had little chance to surface.`
    );
    obs.push(
      `The scheduler <strong>exposes</strong> synchronization problems but does not cause them — the cause is unprotected access to shared resources. A different schedule can hide or reveal the same defect.`
    );
    if (typeof contention === "number") {
      obs.push(
        `Measured resource contention was <strong>${Math.round(contention * 100)}%</strong> — ${contention >= 0.5 ? "high contention amplifies lock overhead and starvation risk" : "moderate contention keeps lock overhead manageable"}.`
      );
    }
    if (typeof base.fairness === "number") {
      obs.push(
        `Waiting-time fairness (Jain index) was <strong>${base.fairness}</strong> — ${base.fairness >= 0.85 ? "waiting time was distributed evenly across processes" : "some processes waited disproportionately long, consistent with the starvation analysis"}.`
      );
    }
    if (best.name) {
      const blocks = !["peterson", "dekker", "spinlock"].includes(best.technique);
      obs.push(
        blocks
          ? `<strong>${best.name}</strong> blocks waiting processes instead of spinning — waiters consume zero CPU until the lock is released.`
          : `<strong>${best.name}</strong> busy-waits — acceptable for very short critical sections, but it burns CPU under contention.`
      );
    }

    el.innerHTML = `
      <h4>Observations</h4>
      <ul class="obs-list">
        ${obs.map((o) => `<li>${o}</li>`).join("")}
      </ul>`;
  },

  _reportImpact(diag) {
    const el = document.getElementById("report-impact");
    if (!el) return;
    const occurred = this._occurred(diag);

    if (!occurred.length) {
      el.innerHTML = `
        <h4>Impact Analysis</h4>
        <p class="report-p">
          No problems occurred under this schedule, so there is no measured impact —
          but the risks remain <strong>latent in the code</strong>. Any change in workload,
          timing, scheduling algorithm, or core count can surface them in production.
        </p>`;
      return;
    }

    const cards = occurred.map((p) => `
      <div class="impact-card sev-${p.severity || "medium"}">
        <div class="impact-head">
          <span class="impact-name">${p.name}</span>
          <span class="sev-badge ${p.severity}">${(p.severity || "").toUpperCase()}</span>
        </div>
        <p class="impact-real">${this.PROBLEM_IMPACT[p.id] || p.explanation || ""}</p>
      </div>`).join("");

    el.innerHTML = `
      <h4>Impact Analysis</h4>
      <p class="metrics-hint">What each detected problem would mean in a real production system.</p>
      <div class="impact-grid">${cards}</div>`;
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
    const best = diag.best || {};
    const bullets = (rec.bullets || []).map((b) => `<li>${b}</li>`).join("");
    const occurred = this._occurred(diag);

    // Forward-looking guidance derived from what was (or wasn't) detected
    const actions = [];
    actions.push(`Protect every shared-resource access with <strong>${best.name || "a blocking primitive"}</strong> — never rely on scheduling order for correctness.`);
    if (occurred.some((p) => p.id === "deadlock")) {
      actions.push(`Enforce a <strong>global lock-ordering discipline</strong> — deadlock prevention requires acquiring resources in a fixed order (no primitive prevents it automatically).`);
    }
    if (occurred.some((p) => p.id === "starvation")) {
      actions.push(`Use <strong>FIFO wait queues or priority aging</strong> so no process can be bypassed indefinitely (bounded waiting).`);
    }
    actions.push(`Avoid spin-based locks (Peterson, Dekker, spinlocks) for long critical sections — prefer blocking primitives that free the CPU.`);
    actions.push(`Keep critical sections <strong>as short as possible</strong> — less time holding a lock means less contention, lower overhead, and fewer starvation opportunities.`);

    el.innerHTML = `
      <h4>Recommendations</h4>
      <div class="rec-box">
        <ul class="rec-list">${bullets}</ul>
        <p class="rec-actions-label">Action plan</p>
        <ol class="rec-actions">
          ${actions.map((a) => `<li>${a}</li>`).join("")}
        </ol>
      </div>`;
  },

  _reportConclusion(diag) {
    const el = document.getElementById("report-conclusion");
    if (!el) return;
    const occurred = this._occurred(diag);
    const best = diag.best || {};
    const sched = (diag.scheduler?.algorithm || "").toUpperCase().replace(/_/g, " ");
    const prevented = (best.prevented || []).length;

    const body = occurred.length
      ? `This four-phase analysis demonstrated the complete synchronization workflow. ` +
        `Phase 1 fixed the execution interleaving under ${sched}; Phase 2 showed that the same workload, ` +
        `run without protection, suffered ${occurred.length} generic synchronization problem(s) ` +
        `(${occurred.map((p) => p.name).join(", ")}); Phase 3 applied each mechanism to that exact workload ` +
        `and measured the result. <strong>${best.name || "The best technique"}</strong> provided the strongest ` +
        `protection — preventing ${prevented} of ${occurred.length} detected problems with a score of ` +
        `${best.score ?? "—"}/100.`
      : `This four-phase analysis demonstrated the complete synchronization workflow. Under ${sched}, ` +
        `the unsynchronized run happened to complete without incident — a reminder that absence of failure ` +
        `is not proof of correctness. The same code, under a different schedule, can corrupt data.`;

    el.innerHTML = `
      <h4>Conclusion</h4>
      <div class="conclusion-final">
        <p class="report-p">${body}</p>
        <p class="report-p">
          The decisive lesson is that <strong>correctness must come from explicit synchronization,
          never from fortunate scheduling</strong>. A race condition that stays hidden for a thousand runs
          is still a defect; one re-ordered context switch is enough to corrupt data, deadlock the system,
          or starve a process. Blocking primitives with bounded waiting remain the engineering standard
          for protecting shared resources.
        </p>
        <div class="conclusion-pill">${this._takeaway(diag)}</div>
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
      "report-key-findings",
      "report-before-after",
      "report-observations",
      "report-impact",
      "report-scheduler",
      "report-recommendation",
      "report-conclusion",
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = "";
    });
    Phase2Viz.clear();
    const detSum = document.getElementById("detection-summary");
    if (detSum) detSum.textContent = "—";
    Object.values(this.charts).forEach((c) => c && c.destroy());
    this.charts = {};
  },
};
