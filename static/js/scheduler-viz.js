/** CPU scheduling — responsive Gantt, full metrics tables, comparison charts */

const SchedulerViz = {
  pidColors: {},
  _canvases: {},
  chartWt: null,
  chartTat: null,

  colorForPid(pid, idx) {
    if (pid === "IDLE") return "#2a1040";
    if (!this.pidColors[pid]) {
      const colors = [
        "#FF2D78", "#00D4D4", "#39FF14", "#B026FF",
        "#FFD700", "#FF4757", "#DA70D6", "#00BFFF",
      ];
      this.pidColors[pid] = colors[Object.keys(this.pidColors).length % colors.length];
    }
    return this.pidColors[pid];
  },

  init() {
    window.addEventListener("resize", () => {
      Object.values(this._canvases).forEach(({ canvas, legendEl, lastTimeline }) => {
        const wrap = canvas?.parentElement;
        if (!wrap || !canvas) return;
        canvas.width = Math.max(wrap.clientWidth - 2, 320);
        if (lastTimeline) this.drawGanttToEl(lastTimeline, canvas, legendEl);
      });
    });
  },

  registerCanvas(algoId, canvas, legendEl) {
    const wrap = canvas.parentElement;
    canvas.width  = wrap ? Math.max(wrap.clientWidth - 2, 320) : 600;
    canvas.height = 160;
    this._canvases[algoId] = { canvas, legendEl, lastTimeline: null };
  },

  drawGanttToEl(timeline, canvas, legendEl) {
    const ctx = canvas?.getContext("2d");
    if (!ctx || !canvas || !timeline?.length) return;

    const padding = { left: 44, right: 16, top: 28, bottom: 36 };
    const maxEnd  = Math.max(...timeline.map((t) => t.end), 1);
    const chartW  = canvas.width - padding.left - padding.right;
    const barH    = 48;
    const y       = padding.top;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
    grad.addColorStop(0, "#100020");
    grad.addColorStop(1, "#0C0018");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    timeline.forEach((seg, i) => {
      const x = padding.left + (seg.start / maxEnd) * chartW;
      const w = Math.max(((seg.end - seg.start) / maxEnd) * chartW, 6);
      const color = seg.color || this.colorForPid(seg.pid, i);

      if (seg.pid === "IDLE") {
        ctx.fillStyle  = "#1e0838";
        ctx.setLineDash([4, 4]);
        ctx.shadowBlur = 0;
      } else {
        ctx.shadowColor = color;
        ctx.shadowBlur  = 14;
        ctx.fillStyle   = color;
        ctx.setLineDash([]);
      }
      ctx.fillRect(x, y, w, barH);
      ctx.setLineDash([]);
      ctx.shadowBlur = 0;

      ctx.strokeStyle = "rgba(255,255,255,0.2)";
      ctx.lineWidth   = 1;
      ctx.strokeRect(x, y, w, barH);

      if (w > 28 && seg.pid !== "IDLE") {
        ctx.fillStyle  = "#0C0018";
        ctx.font       = "bold 12px JetBrains Mono";
        ctx.textAlign  = "center";
        ctx.fillText(seg.pid, x + w / 2, y + barH / 2 + 4);
      }
      if (seg.pid === "IDLE" && w > 20) {
        ctx.fillStyle = "#6040A0";
        ctx.font      = "10px JetBrains Mono";
        ctx.textAlign = "center";
        ctx.fillText("IDLE", x + w / 2, y + barH / 2 + 4);
      }
    });

    ctx.strokeStyle = "rgba(255, 45, 120, 0.5)";
    ctx.lineWidth   = 2;
    ctx.beginPath();
    ctx.moveTo(padding.left, y + barH + 12);
    ctx.lineTo(canvas.width - padding.right, y + barH + 12);
    ctx.stroke();

    ctx.fillStyle = "#9070B0";
    ctx.font      = "10px JetBrains Mono";
    ctx.textAlign = "center";
    const step = maxEnd <= 12 ? 1 : Math.ceil(maxEnd / 12);
    for (let t = 0; t <= maxEnd; t += step) {
      const x = padding.left + (t / maxEnd) * chartW;
      ctx.fillText(String(t), x, y + barH + 28);
    }

    if (legendEl) this.renderLegendToEl(timeline, legendEl);
  },

  drawGanttForAlgo(algoId, timeline) {
    const entry = this._canvases[algoId];
    if (!entry) return;
    entry.lastTimeline = timeline;
    this.drawGanttToEl(timeline, entry.canvas, entry.legendEl);
  },

  renderLegendToEl(timeline, el) {
    if (!el) return;
    const pids = [...new Set(timeline.map((s) => s.pid))].filter((p) => p !== "IDLE");
    el.innerHTML = [
      ...pids.map((p) => `<span class="legend-item"><i style="background:${this.colorForPid(p)}"></i>${p}</span>`),
      `<span class="legend-item"><i style="background:#1e0838;border:1px dashed #6040A0"></i>IDLE</span>`,
    ].join("");
  },

  renderMetrics(metrics, averages) {
    if (averages) this.renderAvgPills(averages);
  },

  renderAvgPills(averages) {
    const avgEl = document.getElementById("sched-avg-stats");
    if (!avgEl || !averages) return;
    const metrics = [
      { label: "Avg CT",  title: "Completion Time", value: averages.avg_completion, color: "cyan"   },
      { label: "Avg TAT", title: "Turnaround Time", value: averages.avg_turnaround, color: "purple" },
      { label: "Avg WT",  title: "Waiting Time",    value: averages.avg_waiting,    color: "green"  },
      { label: "Avg RT",  title: "Response Time",   value: averages.avg_response,   color: "orange" },
    ];
    avgEl.innerHTML = metrics.map(({ label, title, value, color }) => `
      <div class="metric-ring metric-ring--${color}">
        <div class="metric-ring__glow"></div>
        <div class="metric-ring__inner">
          <span class="metric-ring__value">${value ?? "—"}</span>
          <span class="metric-ring__label">${label}</span>
        </div>
        <span class="metric-ring__title">${title}</span>
      </div>`).join("");
  },

  renderComparison(comparisons) {
    const table = document.getElementById("sched-compare-table");
    if (!table) return;

    const rows = Object.entries(comparisons).map(([id, r]) => {
      const a = r.averages || {};
      return `<tr>
        <td><strong>${id.toUpperCase().replace(/_/g, " ")}</strong></td>
        <td>${a.avg_completion ?? "—"}</td>
        <td>${a.avg_turnaround ?? "—"}</td>
        <td>${a.avg_waiting ?? "—"}</td>
        <td>${a.avg_response ?? "—"}</td>
        <td>${a.throughput ?? "—"}</td>
      </tr>`;
    });
    table.innerHTML = `<thead><tr>
      <th>Algorithm</th><th>Avg CT</th><th>Avg TAT</th><th>Avg WT</th><th>Avg RT</th><th>Throughput</th>
    </tr></thead><tbody>${rows.join("")}</tbody>`;

    const labels = Object.keys(comparisons).map((l) => l.toUpperCase().replace(/_/g, " "));
    const wt  = Object.values(comparisons).map((r) => r.averages?.avg_waiting    ?? 0);
    const tat = Object.values(comparisons).map((r) => r.averages?.avg_turnaround ?? 0);

    this._barChart("sched-compare-chart-wt",  labels, wt,  "Avg Waiting Time",    "rgba(255, 45, 120, 0.75)");
    this._barChart("sched-compare-chart-tat", labels, tat, "Avg Turnaround Time", "rgba(0, 212, 212, 0.75)");
  },

  _barChart(canvasId, labels, data, label, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const key = canvasId.includes("wt") ? "chartWt" : "chartTat";
    if (this[key]) this[key].destroy();
    this[key] = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label, data, backgroundColor: color, borderRadius: 6 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: { ticks: { color: "#9070B0", maxRotation: 45 }, grid: { color: "rgba(58,24,96,0.5)" } },
          y: { ticks: { color: "#9070B0" },                  grid: { color: "rgba(58,24,96,0.5)" } },
        },
      },
    });
  },

  renderSyncRankChart(rankings) {
    const canvas = document.getElementById("sync-rank-chart");
    if (!canvas || !rankings?.length) return;
    if (this.syncRankChart) this.syncRankChart.destroy();
    this.syncRankChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: rankings.map((r) => r.name),
        datasets: [{
          label: "Score",
          data: rankings.map((r) => r.score),
          backgroundColor: rankings.map((_, i) =>
            i === 0 ? "rgba(57, 255, 20, 0.8)" : "rgba(255, 45, 120, 0.5)"
          ),
          borderRadius: 8,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { max: 100, ticks: { color: "#9070B0" }, grid: { color: "rgba(58,24,96,0.5)" } },
          y: { ticks: { color: "#EEE0FF" },           grid: { display: false } },
        },
      },
    });
  },
};
