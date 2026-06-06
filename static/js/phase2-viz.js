/**
 * Phase 2 — Timeline-Row Interleaving visualization.
 * Educational: each process has a lane, conflict zones glow red,
 * a plain-English step log updates at every tick.
 */

const Phase2Viz = {
  _blocks: {},

  // ── public entry ─────────────────────────────────────────────────────────

  async renderAll(diagResults, primaryAlgo, processes) {
    const container = document.getElementById("phase2-sim-container");
    if (!container) return;
    container.innerHTML = "";
    this._blocks = {};

    for (const [algoId, diag] of Object.entries(diagResults)) {
      this._buildBlock(container, algoId, diag, algoId === primaryAlgo);
    }

    // Run each algo animation sequentially so students can follow one at a time
    for (const [algoId, diag] of Object.entries(diagResults)) {
      await this._animate(algoId, diag, processes);
    }
  },

  clear() {
    const container = document.getElementById("phase2-sim-container");
    if (container) container.innerHTML = "";
    this._blocks = {};
  },

  // ── block builder ─────────────────────────────────────────────────────────

  _buildBlock(container, algoId, diag, isPrimary) {
    const safeId = algoId.replace(/[^a-z0-9_]/gi, "_");
    const name   = algoId.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

    const div = document.createElement("div");
    div.className = "p2-algo-block card hud-card glow-card";
    div.innerHTML = `
      <div class="p2-algo-header">
        <span class="p2-algo-label">${name}</span>
        ${isPrimary ? '<span class="badge badge-warn">Primary</span>' : ""}
        <span class="p2-conflict-count" id="p2-cc-${safeId}">—</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill progress-fill--warn" id="p2-bar-${safeId}"></div>
      </div>
      <span class="progress-label" id="p2-lbl-${safeId}">Waiting…</span>
      <div class="p2-canvas-wrap">
        <canvas id="p2-canvas-${safeId}"></canvas>
      </div>
      <div class="p2-legend">
        <span><i class="p2-dot" style="background:rgba(245,158,11,0.85)"></i>In critical section</span>
        <span><i class="p2-dot" style="background:rgba(220,38,38,0.9)"></i>RACE — two in CS at once</span>
        <span><i class="p2-dot" style="background:rgba(16,185,129,0.9)"></i>Write back (correct)</span>
        <span><i class="p2-dot" style="background:rgba(239,68,68,1)"></i>Write back (lost update)</span>
      </div>
      <div class="p2-step-log" id="p2-log-${safeId}">
        <span class="p2-log-idle">Simulation will start shortly…</span>
      </div>`;
    container.appendChild(div);

    const canvas = document.getElementById(`p2-canvas-${safeId}`);
    canvas.width = Math.max(canvas.parentElement.clientWidth - 4, 320);

    this._blocks[algoId] = {
      canvas,
      bar:    document.getElementById(`p2-bar-${safeId}`),
      label:  document.getElementById(`p2-lbl-${safeId}`),
      ccEl:   document.getElementById(`p2-cc-${safeId}`),
      logEl:  document.getElementById(`p2-log-${safeId}`),
    };
  },

  // ── animation ─────────────────────────────────────────────────────────────

  async _animate(algoId, diag, processes) {
    const block = this._blocks[algoId];
    if (!block) return;

    const gantt   = diag.scheduler?.gantt || [];
    const pids    = processes.map(p => p.pid);
    const data    = this._derive(gantt, processes, pids);
    const { canvas, bar, label, ccEl, logEl } = block;

    canvas.height = this.HEADER_H + pids.length * this.ROW_H + this.COUNTER_H + 12;

    // Base delay per tick — slower than before
    const baseDelay = Math.max(400, Playback.getStepDelay(Playback.getSpeedSlider()) / 1.5);

    for (let tick = 0; tick <= data.maxEnd; tick++) {
      this._draw(canvas, tick, data, pids);
      Playback.setProgressEl(bar, (tick / data.maxEnd) * 100, label, `t = ${tick}`);

      const logHtml = this._stepLog(tick, data, pids);
      if (logEl) logEl.innerHTML = logHtml;

      // Extra pause when a conflict starts or a write happens — let student read it
      const isConflict = data.conflictTicks.has(tick - 1);
      const isWrite    = data.writeEvents[tick - 1] !== undefined;
      const extraPause = (isConflict || isWrite) ? baseDelay * 1.2 : 0;

      await Playback.sleep(baseDelay + extraPause);
    }

    this._draw(canvas, data.maxEnd, data, pids);
    Playback.setProgressEl(bar, 100, label, "Done");

    // Final summary
    const nConflicts = data.conflictTicks.size;
    const lostWrites = Object.values(data.writeEvents).filter(w => w.lost).length;
    ccEl.textContent  = nConflicts > 0
      ? `⚠ ${nConflicts} conflict tick(s) — race exposed`
      : "✓ No race conflicts detected";
    ccEl.className = `p2-conflict-count ${nConflicts > 0 ? "p2-cc-bad" : "p2-cc-ok"}`;

    if (logEl) {
      const expected = Object.values(data.rmw).reduce((a, b) => a + b, 0);
      const actual   = data.counterAt[data.maxEnd];
      logEl.innerHTML = nConflicts > 0
        ? `<span class="p2-log-conflict">
            ${nConflicts} conflict tick(s) · ${lostWrites} lost write(s) · X = ${actual} (expected ${expected})
           </span>`
        : `<span class="p2-log-ok">No race conditions under this schedule.</span>`;
    }
  },

  // ── step log (plain English) ───────────────────────────────────────────────

  _stepLog(tick, data, pids) {
    const { trace, firstTick, lastTick, writeEvents, conflictTicks } = data;
    const pid = tick < data.maxEnd ? trace[tick] : null;

    const inCSNow = pids.filter(p =>
      firstTick[p] !== undefined && tick >= firstTick[p] && tick <= lastTick[p]
    );

    // Write event at the previous tick (just happened)
    const we = writeEvents[tick - 1];
    if (we) {
      if (we.lost) {
        return `<span class="p2-log-conflict">
          ✗ t=${tick - 1} — <strong>${we.pid}</strong> writes back
          X = <strong>${we.writeVal}</strong>, but it read a stale value (${we.readVal}).
          Another process already changed X to ${we.currentX}.
          This is a <strong>lost update</strong> — data was silently overwritten.
        </span>`;
      } else {
        return `<span class="p2-log-ok">
          ✓ t=${tick - 1} — <strong>${we.pid}</strong> writes X = <strong>${we.writeVal}</strong> successfully.
        </span>`;
      }
    }

    // Conflict at this tick
    if (conflictTicks.has(tick)) {
      const names = inCSNow.join(" and ");
      return `<span class="p2-log-conflict">
        ⚠ t=${tick} — <strong>RACE CONDITION:</strong>
        <strong>${names}</strong> are both inside the critical section at the same time.
        Without synchronization, they can overwrite each other's work.
      </span>`;
    }

    if (!pid) {
      return `<span class="p2-log-idle">t=${tick} — CPU is idle, no process running.</span>`;
    }

    const pidInCS = inCSNow.includes(pid);
    if (pidInCS && inCSNow.length === 1) {
      return `<span class="p2-log-cs">
        t=${tick} — <strong>${pid}</strong> is running on CPU, currently inside its
        critical section. It has read the shared variable but has not written back yet.
        The shared variable is unprotected.
      </span>`;
    }

    return `<span class="p2-log-idle">t=${tick} — <strong>${pid}</strong> is on CPU.</span>`;
  },

  // ── data derivation ───────────────────────────────────────────────────────

  _derive(gantt, processes, pids) {
    const maxEnd = Math.max(...gantt.map(s => s.end), 1);
    const trace  = new Array(maxEnd).fill(null);
    gantt.forEach(seg => {
      if (seg.pid !== "IDLE") {
        for (let t = seg.start; t < seg.end; t++) trace[t] = seg.pid;
      }
    });

    const firstTick = {}, lastTick = {};
    trace.forEach((pid, t) => {
      if (!pid) return;
      if (firstTick[pid] === undefined) firstTick[pid] = t;
      lastTick[pid] = t;
    });

    const rmw = {};
    processes.forEach(p => { rmw[p.pid] = Math.max(1, Math.floor(p.burst / 2)); });

    let X = 0;
    const reg = {}, openRead = {}, writeEvents = {};
    const counterAt = new Array(maxEnd + 1).fill(0);

    for (let t = 0; t < maxEnd; t++) {
      counterAt[t] = X;
      const pid = trace[t];
      if (!pid || rmw[pid] === undefined) continue;
      if (t === firstTick[pid]) { reg[pid] = X; openRead[pid] = true; }
      if (t === lastTick[pid] && openRead[pid]) {
        const result = reg[pid] + rmw[pid];
        writeEvents[t] = { pid, readVal: reg[pid], writeVal: result, currentX: X, lost: X !== reg[pid] };
        X = result;
        openRead[pid] = false;
      }
    }
    counterAt[maxEnd] = X;

    const conflictTicks = new Set();
    for (let t = 0; t < maxEnd; t++) {
      const inCS = pids.filter(pid =>
        firstTick[pid] !== undefined && t >= firstTick[pid] && t <= lastTick[pid]
      );
      if (inCS.length > 1) conflictTicks.add(t);
    }

    return { trace, firstTick, lastTick, writeEvents, counterAt, conflictTicks, maxEnd, rmw };
  },

  // ── cell state ────────────────────────────────────────────────────────────

  _cellState(pid, t, data) {
    const { firstTick, lastTick, writeEvents, conflictTicks } = data;
    if (firstTick[pid] === undefined || t < firstTick[pid] || t > lastTick[pid]) return "idle";
    if (writeEvents[t]?.pid === pid) return writeEvents[t].lost ? "write_lost" : "write_ok";
    return conflictTicks.has(t) ? "conflict" : "cs";
  },

  // ── canvas constants ──────────────────────────────────────────────────────
  LABEL_W:    72,
  STATUS_W:   108,
  ROW_H:      72,
  HEADER_H:   44,
  COUNTER_H:  56,

  CELL_COLORS: {
    cs:         "rgba(245,158,11,0.80)",
    conflict:   "rgba(220,38,38,0.92)",
    write_ok:   "rgba(16,185,129,0.95)",
    write_lost: "rgba(239,68,68,1.00)",
  },

  // ── draw ──────────────────────────────────────────────────────────────────

  _draw(canvas, upToTick, data, pids) {
    const ctx = canvas.getContext("2d");
    const { trace, firstTick, lastTick, writeEvents, counterAt, maxEnd } = data;
    const { LABEL_W, STATUS_W, ROW_H, HEADER_H, COUNTER_H, CELL_COLORS } = this;
    const W      = canvas.width;
    const CELL_W = Math.max(4, (W - LABEL_W - STATUS_W) / maxEnd);

    ctx.clearRect(0, 0, W, canvas.height);
    ctx.fillStyle = "#100020";
    ctx.fillRect(0, 0, W, canvas.height);

    // ── "time →" + tick numbers ───────────────────────────────────────────
    ctx.fillStyle = "#9070B0";
    ctx.font      = "9px JetBrains Mono";
    ctx.textAlign = "left";
    ctx.fillText("time →", 4, 14);

    const tickStep = maxEnd <= 15 ? 1 : maxEnd <= 30 ? 2 : 5;
    ctx.textAlign  = "center";
    for (let t = 0; t <= Math.min(upToTick, maxEnd); t += tickStep) {
      ctx.fillText(String(t), LABEL_W + t * CELL_W + CELL_W / 2, 24);
    }

    ctx.fillStyle = "rgba(144,112,176,0.2)";
    ctx.fillRect(LABEL_W, HEADER_H - 2, W - LABEL_W - STATUS_W, 1);

    // ── Process rows ──────────────────────────────────────────────────────
    pids.forEach((pid, rowIdx) => {
      const rowY = HEADER_H + rowIdx * ROW_H;

      // Row separator
      ctx.fillStyle = "rgba(80,48,120,0.12)";
      ctx.fillRect(0, rowY + ROW_H - 1, W, 1);

      // PID label
      ctx.fillStyle = "#EEE0FF";
      ctx.font      = "bold 16px JetBrains Mono";
      ctx.textAlign = "right";
      ctx.fillText(pid, LABEL_W - 10, rowY + ROW_H / 2 + 6);

      // Cells
      for (let t = 0; t < upToTick && t < maxEnd; t++) {
        const state = this._cellState(pid, t, data);
        if (state === "idle") continue;

        const x   = LABEL_W + t * CELL_W;
        const y   = rowY + 6;
        const w   = Math.max(CELL_W - 1, 3);
        const h   = ROW_H - 12;
        const col = CELL_COLORS[state];

        ctx.fillStyle   = col;
        ctx.shadowColor = col;
        ctx.shadowBlur  = state === "conflict" || state.startsWith("write") ? 14 : 5;
        ctx.fillRect(x, y, w, h);
        ctx.shadowBlur  = 0;

        // Label inside cell
        if (CELL_W > 18) {
          ctx.fillStyle = "rgba(255,255,255,0.95)";
          ctx.font      = `bold ${Math.min(13, CELL_W - 4)}px JetBrains Mono`;
          ctx.textAlign = "center";
          const cx = x + w / 2;
          const cy = y + h / 2 + 5;
          if (state === "conflict") ctx.fillText("RACE", cx, cy);
          else if (state === "cs")   ctx.fillText("CS", cx, cy);
          else if (state === "write_ok" || state === "write_lost") {
            const we = writeEvents[t];
            if (we) ctx.fillText("W:" + we.writeVal, cx, cy);
          }
        }
      }

      // ── Right-side live status label ──────────────────────────────────
      const statusX  = LABEL_W + maxEnd * CELL_W + 8;
      const inCS     = firstTick[pid] !== undefined
        && upToTick > firstTick[pid]
        && (upToTick - 1) <= lastTick[pid];
      const onCPU    = upToTick > 0 && trace[upToTick - 1] === pid;
      const conflict = inCS && data.conflictTicks.has(upToTick - 1);
      const done     = lastTick[pid] !== undefined && upToTick > lastTick[pid];

      let statusText  = "—";
      let statusColor = "#604080";
      if (done)          { statusText = "done";     statusColor = "#9070B0"; }
      else if (conflict) { statusText = "⚠ RACE";   statusColor = "rgba(220,38,38,0.95)"; }
      else if (onCPU)    { statusText = "▶ running"; statusColor = "rgba(245,158,11,0.9)"; }
      else if (inCS)     { statusText = "in CS";     statusColor = "rgba(245,158,11,0.6)"; }
      else if (upToTick === 0 || firstTick[pid] === undefined || upToTick <= firstTick[pid]) {
                           statusText = "waiting";   statusColor = "#604080"; }

      ctx.fillStyle = statusColor;
      ctx.font      = "bold 10px JetBrains Mono";
      ctx.textAlign = "left";
      ctx.fillText(statusText, statusX, rowY + ROW_H / 2 + 4);
    });

    // Scanner line at current tick
    if (upToTick < maxEnd) {
      const scanX = LABEL_W + upToTick * CELL_W;
      ctx.strokeStyle = "rgba(255,45,120,0.7)";
      ctx.lineWidth   = 2;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(scanX, HEADER_H);
      ctx.lineTo(scanX, HEADER_H + pids.length * ROW_H);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // ── Shared counter strip ──────────────────────────────────────────────
    const cY = HEADER_H + pids.length * ROW_H + 8;

    ctx.fillStyle = "rgba(144,112,176,0.06)";
    ctx.fillRect(LABEL_W, cY, maxEnd * CELL_W, COUNTER_H - 6);

    ctx.fillStyle = "#9070B0";
    ctx.font      = "bold 12px JetBrains Mono";
    ctx.textAlign = "right";
    ctx.fillText("Shared X", LABEL_W - 10, cY + 20);

    for (let t = 0; t < upToTick && t < maxEnd; t++) {
      const we = writeEvents[t];
      if (!we) continue;
      const x   = LABEL_W + t * CELL_W;
      const w   = Math.max(CELL_W - 1, 3);
      const col = we.lost ? "rgba(220,38,38,0.85)" : "rgba(16,185,129,0.85)";
      ctx.fillStyle   = col;
      ctx.shadowColor = col;
      ctx.shadowBlur  = 8;
      ctx.fillRect(x, cY + 3, w, COUNTER_H - 12);
      ctx.shadowBlur  = 0;

      if (CELL_W > 14) {
        ctx.fillStyle = "#fff";
        ctx.font      = `bold ${Math.min(10, CELL_W - 4)}px JetBrains Mono`;
        ctx.textAlign = "center";
        ctx.fillText(String(we.writeVal), x + w / 2, cY + 16);
      }
      if (we.lost && CELL_W > 30) {
        ctx.fillStyle = "rgba(255,190,190,0.9)";
        ctx.font      = "7px JetBrains Mono";
        ctx.textAlign = "center";
        ctx.fillText("LOST!", x + w / 2, cY + 27);
      }
    }

    // Final expected vs actual summary
    if (upToTick >= maxEnd) {
      const actual   = counterAt[maxEnd];
      const expected = Object.values(data.rmw).reduce((a, b) => a + b, 0);
      const ok       = actual === expected;
      ctx.fillStyle  = ok ? "rgba(16,185,129,0.9)" : "rgba(239,68,68,0.9)";
      ctx.font       = "bold 9px JetBrains Mono";
      ctx.textAlign  = "left";
      ctx.fillText(
        ok
          ? `X = ${actual}  ✓  correct`
          : `X = ${actual}  ✗  expected ${expected},  lost ${expected - actual}`,
        LABEL_W + maxEnd * CELL_W + 8,
        cY + 18
      );
    }
  },
};
