/** Phase 1 — parallel Gantt build for all selected algorithms */

const Phase1Tutor = {
  blocks: [],   // [{id, gantt, canvas, legendEl, progressBar, progressLabel, label, segmentIndex}]
  logEl: null,
  playing: false,
  timer: null,

  init() {
    this.logEl = document.getElementById("phase1-tutor-log");
  },

  resetAll(blocksMap) {
    this.stop();
    this.blocks = Object.entries(blocksMap).map(([id, b]) => ({
      id,
      gantt:         b.gantt        || [],
      canvas:        b.canvas,
      legendEl:      b.legendEl,
      progressBar:   b.progressBar,
      progressLabel: b.progressLabel,
      label:         b.label,
      segmentIndex:  0,
    }));
    if (this.logEl) this.logEl.innerHTML = "";
    this.blocks.forEach((b) =>
      Playback.setProgressEl(b.progressBar, 0, b.progressLabel, "Ready to build Gantt…")
    );
    const names = this.blocks.map((b) => b.label).join(" & ");
    this.log(`${names} — building Gantt chart${this.blocks.length > 1 ? "s" : ""}`);
  },

  reset() {},   // legacy no-op

  log(msg) {
    if (!this.logEl) return;
    const line = document.createElement("div");
    line.className = "tutor-line";
    line.textContent = msg;
    this.logEl.appendChild(line);
    this.logEl.scrollTop = this.logEl.scrollHeight;
  },

  stop() {
    this.playing = false;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  },

  _drawPartialForBlock(block) {
    const partial = block.gantt.slice(0, block.segmentIndex).map((s, i) => ({
      ...s,
      color: SchedulerViz.colorForPid(s.pid, i),
    }));
    // Keep lastTimeline up-to-date so ResizeObserver can redraw on zoom
    const entry = SchedulerViz._canvases[block.id];
    if (entry) entry.lastTimeline = partial;
    SchedulerViz.drawGanttToEl(partial, block.canvas, block.legendEl);
  },

  nextSegment() {
    let anyMore = false;
    this.blocks.forEach((block) => {
      if (block.segmentIndex >= block.gantt.length) return;
      const seg = block.gantt[block.segmentIndex];
      block.segmentIndex++;
      this._drawPartialForBlock(block);
      const pct = (block.segmentIndex / block.gantt.length) * 100;
      Playback.setProgressEl(block.progressBar, pct, block.progressLabel,
        `Segment ${block.segmentIndex}/${block.gantt.length}: ${seg.pid}`);
      if (block.segmentIndex < block.gantt.length) anyMore = true;
    });
    return anyMore;
  },

  async _autoPlayBlock(block, delay) {
    block.segmentIndex = 0;
    this._drawPartialForBlock(block);
    while (this.playing && block.segmentIndex < block.gantt.length) {
      const seg = block.gantt[block.segmentIndex];
      block.segmentIndex++;
      this._drawPartialForBlock(block);
      const pct = (block.segmentIndex / block.gantt.length) * 100;
      Playback.setProgressEl(block.progressBar, pct, block.progressLabel,
        `${block.label}: ${seg.pid} t=${seg.start}→${seg.end}`);
      if (seg.pid === "IDLE") {
        this.log(`[${block.label}] IDLE: t=${seg.start} to t=${seg.end}`);
      } else {
        this.log(`[${block.label}] ${seg.pid}: t=${seg.start}→${seg.end} (slice=${seg.end - seg.start})`);
      }
      await Playback.sleep(delay);
    }
    Playback.setProgressEl(block.progressBar, 100, block.progressLabel, `${block.label}: complete`);
  },

  async autoPlayGantt() {
    this.stop();
    this.playing = true;
    const delay = Playback.getStepDelay(Playback.getSpeedSlider());
    await Promise.all(this.blocks.map((b) => this._autoPlayBlock(b, delay)));
    this.playing = false;
    const stepBtn = document.getElementById("btn-phase1-step");
    if (stepBtn) stepBtn.disabled = true;
  },

  async revealMetricsTable() {
    // averages rendered by main.js directly after autoPlayGantt
  },
};
