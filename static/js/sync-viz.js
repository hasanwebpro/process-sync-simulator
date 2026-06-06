/** Synchronization visualization — Vice City neon palette */

const SyncViz = {
  canvas: null,
  ctx: null,
  steps: [],
  currentIndex: 0,
  playTimer: null,
  playing: false,

  init() {
    this.canvas = document.getElementById("sync-canvas");
    if (this.canvas) {
      this.ctx = this.canvas.getContext("2d");
      this._resize();
      window.addEventListener("resize", () => this._resize());
    }
  },

  _resize() {
    const wrap = this.canvas?.parentElement;
    if (!wrap || !this.canvas) return;
    this.canvas.width  = Math.max(wrap.clientWidth - 2, 300);
    this.canvas.height = 680;
    if (this.steps.length) this.drawCanvas(this.steps[this.currentIndex]);
  },

  setSteps(steps, algoName) {
    this.steps = steps || [];
    this.algoName = algoName || "";
    this.currentIndex = 0;
    const stepBtn = document.getElementById("btn-sim-step");
    if (stepBtn) stepBtn.disabled = this.steps.length === 0;
    if (typeof SyncInsights !== "undefined" && this.steps.length) {
      SyncInsights.renderRunSummary(SyncInsights.summarizeRun(this.steps, this.algoName));
    }
    this.renderStep(0);
    this.buildTimeline();
  },

  renderStep(index) {
    if (!this.steps.length || index < 0 || index >= this.steps.length) return;
    this.currentIndex = index;
    const step = this.steps[index];

    const pct = ((index + 1) / this.steps.length) * 100;
    Playback.setProgress(
      "sync-progress-bar",
      pct,
      "sync-progress-label",
      `Step ${index + 1}/${this.steps.length}`
    );

    const tickEl = document.getElementById("tick-display");
    if (tickEl) {
      const phase = step.phase ? ` · ${step.phase.replace(/_/g, " ")}` : "";
      tickEl.textContent = `Tick ${step.tick ?? index}${phase}`;
    }

    this.renderProcessStates(step);
    this.drawCanvas(step);
    this.updateResourceBar(step);
    this.renderWaitingQueue(step);
    if (typeof SyncInsights !== "undefined") {
      SyncInsights.renderExplainPanel(step);
    }
    this.highlightTimeline(index);
  },

  renderProcessStates(step) {
    const container = document.getElementById("process-states");
    if (!container) return;
    const cs     = new Set(step.critical_section || []);
    const active = step.active_cpu || step.scheduled_process;

    container.innerHTML = Object.entries(step.processes || {})
      .map(([pid, state]) => {
        const classes = [
          "proc-chip",
          `state-${state}`,
          cs.has(pid) ? "in-cs" : "",
          pid === active ? "on-cpu" : "",
        ].filter(Boolean).join(" ");
        return `<div class="${classes}">
          <span class="state-dot"></span>
          <span class="pid">${pid}</span>
          <span class="state-label">${state}</span>
        </div>`;
      })
      .join("");
  },

  renderWaitingQueue(step) {
    const el = document.getElementById("waiting-queue-viz");
    if (!el) return;
    const wq = step.waiting_queue || [];
    if (!wq.length) {
      el.innerHTML = `<span class="wq-empty">No processes waiting</span>`;
      return;
    }
    el.innerHTML = `<span class="wq-label">Waiting Queue</span>` +
      wq.map((p, i) => `<span class="wq-chip">${i + 1}. ${p}</span>`)
        .join('<span class="wq-arrow">→</span>');
  },

  drawCanvas(step) {
    const ctx    = this.ctx;
    const canvas = this.canvas;
    if (!ctx || !canvas) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Background
    const bg = ctx.createLinearGradient(0, 0, w, h);
    bg.addColorStop(0, "#100020");
    bg.addColorStop(1, "#080018");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    const inCs = step.critical_section || [];
    const wq   = step.waiting_queue   || [];
    const glow = inCs.length > 0;

    // ── Shared Resource box ───────────────────────────────────────────────
    const csX = w * 0.18;
    const csW = w * 0.64;
    const csY = 56;
    const csH = 220;
    const csCx = csX + csW / 2;

    if (glow) { ctx.shadowColor = "#39FF14"; ctx.shadowBlur = 22; }
    ctx.strokeStyle = glow ? "#39FF14" : "rgba(0,212,212,0.4)";
    ctx.lineWidth   = glow ? 3 : 2;
    ctx.fillStyle   = glow ? "rgba(57,255,20,0.07)" : "rgba(0,212,212,0.04)";
    ctx.fillRect(csX, csY, csW, csH);
    ctx.strokeRect(csX, csY, csW, csH);
    ctx.shadowBlur = 0;

    // Label above box
    ctx.fillStyle  = "#9070B0";
    ctx.font       = "10px Outfit";
    ctx.textAlign  = "left";
    ctx.fillText("SHARED RESOURCE", csX, csY - 8);

    // Status line (top of box)
    ctx.fillStyle  = glow ? "#39FF14" : "#00D4D4";
    ctx.font       = '700 12px "Orbitron", sans-serif';
    ctx.textAlign  = "center";
    ctx.fillText(inCs.length ? "🔒 LOCKED — IN USE" : "OPEN — NO ONE INSIDE", csCx, csY + 24);

    // ── Processes INSIDE the CS box ───────────────────────────────────────
    if (inCs.length) {
      const chipW = 94, chipH = 52, chipGap = 16;
      const totalW = inCs.length * chipW + (inCs.length - 1) * chipGap;
      let cx = csCx - totalW / 2;
      const cy = csY + (csH - chipH) / 2 + 12;

      inCs.forEach(pid => {
        ctx.shadowColor = "#39FF14"; ctx.shadowBlur = 16;
        ctx.fillStyle   = "rgba(57,255,20,0.18)";
        ctx.strokeStyle = "#39FF14"; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.roundRect(cx, cy, chipW, chipH, 10);
        ctx.fill(); ctx.stroke();
        ctx.shadowBlur = 0;

        ctx.font      = "bold 20px JetBrains Mono";
        ctx.fillStyle = "#D8FFD0";
        ctx.textAlign = "center";
        ctx.fillText(pid, cx + chipW / 2, cy + chipH / 2 + 7);
        cx += chipW + chipGap;
      });
    } else {
      ctx.font      = "italic 13px Outfit";
      ctx.fillStyle = "#4A3870";
      ctx.textAlign = "center";
      ctx.fillText("— empty —", csCx, csY + csH / 2 + 10);
    }

    // ── Waiting queue BELOW the CS box ───────────────────────────────────
    if (wq.length) {
      const qChipW = 68, qChipH = 42, qGap = 12;
      const totalQW = wq.length * qChipW + (wq.length - 1) * qGap;
      const qY  = csY + csH + 62;
      let   qX  = csCx - totalQW / 2;

      // Dashed arrow from queue up to CS box bottom
      const arrowTipY = csY + csH + 2;
      const arrowBaseY = qY - 8;
      ctx.strokeStyle = "rgba(255,176,32,0.45)";
      ctx.lineWidth   = 1.5;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(csCx, arrowBaseY);
      ctx.lineTo(csCx, arrowTipY + 8);
      ctx.stroke();
      ctx.setLineDash([]);
      // arrowhead (pointing up)
      ctx.fillStyle = "#FFB020";
      ctx.beginPath();
      ctx.moveTo(csCx,     arrowTipY);
      ctx.lineTo(csCx - 7, arrowTipY + 11);
      ctx.lineTo(csCx + 7, arrowTipY + 11);
      ctx.closePath(); ctx.fill();

      // "WAITING QUEUE" label
      ctx.fillStyle  = "#FFB020";
      ctx.font       = '700 10px "Orbitron"';
      ctx.textAlign  = "center";
      ctx.fillText("WAITING QUEUE", csCx, qY - 14);

      // Chips
      wq.forEach((pid, i) => {
        ctx.fillStyle   = "rgba(255,176,32,0.12)";
        ctx.strokeStyle = "#FFB020"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.roundRect(qX, qY, qChipW, qChipH, 8);
        ctx.fill(); ctx.stroke();

        ctx.fillStyle  = "#FFB020";
        ctx.font       = "bold 10px Outfit";
        ctx.textAlign  = "center";
        ctx.fillText(`#${i + 1}`, qX + qChipW / 2, qY + 14);

        ctx.fillStyle  = "#EEE0FF";
        ctx.font       = "bold 15px JetBrains Mono";
        ctx.fillText(pid, qX + qChipW / 2, qY + 32);
        qX += qChipW + qGap;
      });
    }

    // ── CPU box — top-left ────────────────────────────────────────────────
    if (step.active_cpu) {
      const cpuX = 10, cpuY = 10;
      ctx.fillStyle   = "rgba(255,45,120,0.15)";
      ctx.strokeStyle = "#FF2D78"; ctx.lineWidth = 2;
      ctx.shadowColor = "#FF2D78"; ctx.shadowBlur = 8;
      ctx.fillRect(cpuX, cpuY, 80, 56);
      ctx.strokeRect(cpuX, cpuY, 80, 56);
      ctx.shadowBlur = 0;
      ctx.fillStyle  = "#FF2D78";
      ctx.font       = '700 10px "Orbitron"';
      ctx.textAlign  = "center";
      ctx.fillText("CPU", cpuX + 40, cpuY + 17);
      ctx.font       = "bold 15px JetBrains Mono";
      ctx.fillStyle  = "#EEE0FF";
      ctx.fillText(step.active_cpu, cpuX + 40, cpuY + 40);
    }

    // ── CPU interval — top-right ──────────────────────────────────────────
    if (step.cpu_interval) {
      ctx.fillStyle = "#9070B0";
      ctx.font      = "9px JetBrains Mono";
      ctx.textAlign = "right";
      ctx.fillText(`t=${step.cpu_interval.start}–${step.cpu_interval.end}`, w - 8, 16);
    }

    // ── Action label — bottom-centre ──────────────────────────────────────
    ctx.fillStyle = "#9070B0";
    ctx.font      = "11px Outfit";
    ctx.textAlign = "center";
    ctx.fillText((step.action || "step").replace(/_/g, " ").toUpperCase(), w / 2, h - 10);
  },

  updateResourceBar(step) {
    const bar = document.getElementById("resource-bar");
    if (!bar) return;
    const parts = [];
    if (step.resources) {
      for (const [k, v] of Object.entries(step.resources)) {
        parts.push(`<span class="res-chip">${k}: <strong>${v}</strong></span>`);
      }
    }
    if (step.shared_vars) {
      for (const [k, v] of Object.entries(step.shared_vars)) {
        const val = Array.isArray(v) ? `[${v.join(",")}]` : v;
        parts.push(`<span class="res-chip shared">${k}: <strong>${val}</strong></span>`);
      }
    }
    bar.innerHTML = parts.length
      ? parts.join("")
      : '<span class="res-chip muted">Shared state idle</span>';
  },

  buildTimeline() {
    const tl = document.getElementById("sync-timeline");
    if (!tl) return;
    const phaseColors = {
      scheduling:            "#FF2D78",   // pink — CPU scheduling phase
      sync_during_execution: "#00D4D4",   // teal — sync phase
      complete:              "#39FF14",   // green — done
    };
    const labels = {
      scheduling: "CPU",
      sync_during_execution: "Sync",
      complete: "Done",
    };
    tl.innerHTML = this.steps
      .map((s, i) => {
        const c   = phaseColors[s.phase] || "#B026FF";
        const tag = labels[s.phase] || "?";
        const title = `${s.action}: ${s.message || ""}`.slice(0, 80);
        return `<div class="tick-seg" data-idx="${i}" style="--seg-color:${c}" title="${title}">
          <span class="tick-num">${i}</span><span class="tick-tag">${tag}</span></div>`;
      })
      .join("");
    tl.querySelectorAll(".tick-seg").forEach((el) => {
      el.addEventListener("click", () => {
        this.stopPlay();
        this.renderStep(parseInt(el.dataset.idx, 10));
      });
    });
  },

  highlightTimeline(index) {
    document.querySelectorAll("#sync-timeline .tick-seg").forEach((el, i) => {
      el.classList.toggle("active", i === index);
      el.style.opacity = i === index ? "1" : "0.45";
    });
  },

  stepForward() {
    if (this.currentIndex < this.steps.length - 1) {
      this.renderStep(this.currentIndex + 1);
      return true;
    }
    this.stopPlay();
    return false;
  },

  startPlay(speed) {
    this.stopPlay();
    this.playing = true;
    const slider = speed ?? Playback.getSpeedSlider();
    const delay  = Playback.getStepDelay(slider);
    this.playTimer = setInterval(() => {
      if (!this.stepForward()) this.stopPlay();
    }, delay);
  },

  resetToStart() {
    this.stopPlay();
    if (this.steps.length) this.renderStep(0);
  },

  stopPlay() {
    this.playing = false;
    if (this.playTimer) clearInterval(this.playTimer);
    this.playTimer = null;
  },
};
