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
    this.canvas.width = Math.max(wrap.clientWidth - 2, 300);
    this.canvas.height = 220;
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

    // Vice City dark-purple background
    const bg = ctx.createLinearGradient(0, 0, w, h);
    bg.addColorStop(0, "#100020");
    bg.addColorStop(1, "#080018");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    // Critical section box
    const csX = w * 0.32;
    const csW = w * 0.36;
    const csY = 36;
    const csH = h - 100;

    const inCs = step.critical_section || [];
    const glow = inCs.length > 0;

    if (glow) {
      ctx.shadowColor = "#39FF14";
      ctx.shadowBlur  = 28;
    }
    ctx.strokeStyle = glow ? "#39FF14" : "rgba(0, 212, 212, 0.4)";
    ctx.lineWidth   = glow ? 3 : 2;
    ctx.fillStyle   = glow ? "rgba(57, 255, 20, 0.08)" : "rgba(0, 212, 212, 0.05)";
    ctx.fillRect(csX, csY, csW, csH);
    ctx.strokeRect(csX, csY, csW, csH);
    ctx.shadowBlur = 0;

    ctx.fillStyle = "#9070B0";
    ctx.font = "10px Outfit";
    ctx.textAlign = "left";
    ctx.fillText("SHARED RESOURCE", csX, csY - 6);

    ctx.fillStyle = glow ? "#39FF14" : "#00D4D4";
    ctx.font = '600 12px "Orbitron", sans-serif';
    ctx.textAlign = "center";
    ctx.fillText(
      inCs.length ? "LOCKED — IN USE" : "OPEN — NO ONE INSIDE",
      csX + csW / 2, csY + 20
    );

    if (inCs.length) {
      ctx.font = "13px JetBrains Mono";
      ctx.fillStyle = "#EEE0FF";
      ctx.fillText(inCs.join(" · "), csX + csW / 2, csY + csH / 2);
    } else {
      ctx.font = "11px Outfit";
      ctx.fillStyle = "#9070B0";
      ctx.fillText("— empty —", csX + csW / 2, csY + csH / 2);
    }

    // CPU box — hot pink
    if (step.active_cpu) {
      ctx.fillStyle   = "rgba(255, 45, 120, 0.15)";
      ctx.strokeStyle = "#FF2D78";
      ctx.lineWidth   = 2;
      ctx.shadowColor = "#FF2D78";
      ctx.shadowBlur  = 10;
      const cpuX = 16;
      const cpuY = csY + 10;
      ctx.fillRect(cpuX, cpuY, 70, 50);
      ctx.strokeRect(cpuX, cpuY, 70, 50);
      ctx.shadowBlur  = 0;
      ctx.fillStyle   = "#FF2D78";
      ctx.font = '600 10px "Orbitron"';
      ctx.textAlign = "center";
      ctx.fillText("CPU", cpuX + 35, cpuY + 18);
      ctx.font = "bold 14px JetBrains Mono";
      ctx.fillStyle = "#EEE0FF";
      ctx.fillText(step.active_cpu, cpuX + 35, cpuY + 38);
    }

    // CPU time interval label
    if (step.cpu_interval) {
      ctx.fillStyle  = "#9070B0";
      ctx.font = "10px JetBrains Mono";
      ctx.textAlign = "right";
      ctx.fillText(
        `t=${step.cpu_interval.start}–${step.cpu_interval.end}`,
        w - 12, 20
      );
    }

    // Action label at bottom
    ctx.fillStyle  = "#9070B0";
    ctx.font = "11px Outfit";
    ctx.textAlign = "center";
    ctx.fillText(
      (step.action || "step").replace(/_/g, " ").toUpperCase(),
      w / 2, h - 12
    );
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
