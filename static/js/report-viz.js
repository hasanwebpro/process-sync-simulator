/** Analysis report — concise, viva-ready */

const ReportViz = {
  render(conclusion, phase1, phase2, aiExplanation) {
    this.renderExecutive(conclusion, aiExplanation);
    this.renderSchedBlock(conclusion, phase1);
    this.renderSyncBlock(conclusion, phase2);
    this.renderComparison(phase2);
    this.renderRecommendation(conclusion, phase2);
  },

  /* ── Helpers ── */
  _md(text) {
    /* Convert **bold** markers to HTML and preserve line breaks */
    if (!text) return "";
    return text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, " ");
  },

  /* ── Executive Summary ── */
  renderExecutive(conclusion, ai) {
    const el = document.getElementById("report-executive");
    if (!el) return;
    const c       = conclusion || {};
    const summary = c.executive_summary || c.conclusion || "";

    const sentences = summary.split(/(?<=\.)\s+/).filter(Boolean);
    const body = sentences.map((s, i) => {
      if (i === 0) return `<p class="conclusion-hero">${this._md(s)}</p>`;
      if (/lowest|best|highest|scored|recommend/i.test(s))
        return `<p class="conclusion-highlight">${this._md(s)}</p>`;
      return `<p class="conclusion-body">${this._md(s)}</p>`;
    }).join("");

    /* Only show AI box when OpenAI actually responded */
    const aiHtml = (ai?.text && ai?.source === "openai")
      ? `<div class="ai-box">
           <span class="source-tag">AI Explanation</span>
           <p>${this._md(ai.text)}</p>
         </div>`
      : "";

    el.innerHTML = `
      <div class="conclusion-banner">
        <div class="conclusion-banner-text">
          <h4>Analysis Report</h4>
          <span class="conclusion-sub">CPU Scheduling + Process Synchronization</span>
        </div>
      </div>
      <div class="conclusion-summary-block">
        ${body || "<p class='conclusion-body'>Run Phase 3 to generate the report.</p>"}
      </div>
      ${aiHtml}`;
  },

  /* ── Scheduling Results ── */
  renderSchedBlock(conclusion, phase1) {
    const el = document.getElementById("report-scheduling");
    if (!el || !phase1) return;
    const sched   = conclusion.sched_analysis || {};
    const best    = sched.best || {};
    const primary = phase1.primary_algorithm || "";
    const avgs    = phase1.scheduling?.averages || {};

    let rows = "";
    for (const [id, data] of Object.entries(phase1.comparisons || {})) {
      const a      = data.averages || {};
      const isBest = id === (best.algorithm || primary);
      rows += `<tr class="${isBest ? "row-best" : ""}">
        <td>${id.toUpperCase().replace(/_/g, " ")} ${isBest ? "★" : ""}</td>
        <td>${a.avg_completion ?? "—"}</td>
        <td>${a.avg_turnaround ?? "—"}</td>
        <td>${a.avg_waiting ?? "—"}</td>
        <td>${a.avg_response ?? "—"}</td>
        <td>${a.throughput ?? "—"}</td>
      </tr>`;
    }

    el.innerHTML = `
      <h4>CPU Scheduling Results</h4>
      ${conclusion.sched_summary
        ? `<p class="report-p">${this._md(conclusion.sched_summary)}</p>`
        : ""}
      <div class="table-scroll">
        <table class="metrics-table">
          <thead>
            <tr>
              <th>Algorithm</th><th>Avg CT</th><th>Avg TAT</th>
              <th>Avg WT</th><th>Avg RT</th><th>Throughput</th>
            </tr>
          </thead>
          <tbody>${rows || `<tr><td colspan="6">Run Phase 1 first</td></tr>`}</tbody>
        </table>
      </div>
      <div class="highlight-box">
        <strong>Used for sync:</strong> ${(primary || "").toUpperCase()}
        &nbsp;·&nbsp; Order: ${(phase1.execution_order || []).join(" → ")}
        &nbsp;·&nbsp; AWT=${avgs.avg_waiting} &nbsp;·&nbsp; ATAT=${avgs.avg_turnaround}
      </div>`;
  },

  /* ── Synchronization Results ── */
  renderSyncBlock(conclusion, phase2) {
    const el = document.getElementById("report-sync");
    if (!el || !phase2) return;
    const sync = conclusion.sync_analysis || phase2.sync_comparison || {};
    const best = sync.best || {};

    el.innerHTML = `
      <h4>Synchronization Results</h4>
      ${conclusion.sync_summary
        ? `<p class="report-p">${this._md(conclusion.sync_summary)}</p>`
        : ""}
      <div class="highlight-box green">
        <strong>Best algorithm:</strong> ${best.name || "—"}
        &nbsp;·&nbsp; Score: ${best.score ?? "—"}/100
        <br><span class="muted">${(best.strengths || []).join(" · ")}</span>
      </div>`;
  },

  /* ── Full Comparison Table ── */
  renderComparison(phase2) {
    const el       = document.getElementById("report-sync-table");
    if (!el) return;
    const rankings = phase2?.sync_comparison?.rankings || [];
    if (!rankings.length) {
      el.innerHTML = "<p class='muted'>No sync comparison data yet.</p>";
      return;
    }
    el.innerHTML = `
      <h4>Algorithm Comparison</h4>
      <div class="table-scroll">
        <table class="metrics-table">
          <thead>
            <tr>
              <th>Rank</th><th>Algorithm</th><th>Score</th>
              <th>Strengths</th><th>Weaknesses</th>
            </tr>
          </thead>
          <tbody>
            ${rankings.map((r, i) => `
              <tr class="${i === 0 ? "row-best" : ""}">
                <td>${i + 1}</td>
                <td><strong>${r.name}</strong></td>
                <td><span class="score-badge">${r.score}</span></td>
                <td>${(r.strengths  || []).slice(0, 2).join("; ") || "—"}</td>
                <td>${(r.weaknesses || []).slice(0, 2).join("; ") || "—"}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  },

  /* ── Final Recommendation ── */
  renderRecommendation(conclusion, phase2) {
    const el = document.getElementById("report-recommendation");
    if (!el) return;
    const best    = phase2?.sync_comparison?.best || {};
    const rec     = conclusion.detailed_recommendation || conclusion.recommendation || "";
    const bullets = conclusion.recommendation_bullets || [];

    el.innerHTML = `
      <h4>Recommendation</h4>
      <div class="rec-box">
        <p class="rec-main">${this._md(rec)}</p>
        <ul class="rec-list">
          ${bullets.map((b) => `<li>${this._md(b)}</li>`).join("")}
        </ul>
        ${best.use_case
          ? `<p class="rec-usecase"><strong>Real-world use:</strong> ${best.use_case}</p>`
          : ""}
      </div>`;
  },
};
