/** Phase 1 — slow Gantt build + metrics reveal for students */

const Phase1Tutor = {
  gantt: [],
  metrics: [],
  averages: null,
  segmentIndex: 0,
  logEl: null,
  playing: false,
  timer: null,

  init() {
    this.logEl = document.getElementById("phase1-tutor-log");
  },

  reset(gantt, metrics, averages, label) {
    this.stop();
    this.gantt     = gantt    || [];
    this.metrics   = metrics  || [];
    this.averages  = averages;
    this.segmentIndex = 0;
    if (this.logEl) this.logEl.innerHTML = "";
    Playback.setProgress("gantt-progress-bar", 0, "gantt-progress-label", "Ready to build Gantt…");
    const title = label
      ? `${label} — building Gantt chart`
      : "Phase 1: Watch the Gantt chart build one CPU slice at a time.";
    this.log(title);
  },

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

  drawPartial(count) {
    const partial = this.gantt.slice(0, count);
    SchedulerViz.drawGantt(
      partial.map((s, i) => ({
        ...s,
        color: SchedulerViz.colorForPid(s.pid, i),
      }))
    );
  },

  nextSegment() {
    if (this.segmentIndex >= this.gantt.length) {
      this.log("Gantt complete.");
      Playback.setProgress("gantt-progress-bar", 100, "gantt-progress-label", "Gantt complete");
      return false;
    }
    const seg = this.gantt[this.segmentIndex];
    this.segmentIndex += 1;
    this.drawPartial(this.segmentIndex);
    const pct = (this.segmentIndex / this.gantt.length) * 100;
    Playback.setProgress(
      "gantt-progress-bar",
      pct,
      "gantt-progress-label",
      `Segment ${this.segmentIndex}/${this.gantt.length}: ${seg.pid}`
    );
    const dur = seg.end - seg.start;
    if (seg.pid === "IDLE") {
      this.log(`IDLE: t=${seg.start} to t=${seg.end} (CPU free)`);
    } else {
      this.log(`${seg.pid}: t=${seg.start} → t=${seg.end} (slice = ${dur})`);
    }
    return true;
  },

  async autoPlayGantt() {
    this.stop();
    this.playing = true;
    this.segmentIndex = 0;
    this.drawPartial(0);
    const delay = Playback.getStepDelay(Playback.getSpeedSlider());

    while (this.playing && this.segmentIndex < this.gantt.length) {
      this.nextSegment();
      document.getElementById("btn-phase1-step").disabled = false;
      await Playback.sleep(delay);
    }
    this.playing = false;
    document.getElementById("btn-phase1-step").disabled =
      this.segmentIndex >= this.gantt.length;
  },

  async revealMetricsTable() {
    if (this.averages) {
      const a = this.averages;
      SchedulerViz.renderAvgPills(a);
      this.log(`Averages — ATAT=${a.avg_turnaround}, AWT=${a.avg_waiting}, ART=${a.avg_response}`);
    }
  },
};
