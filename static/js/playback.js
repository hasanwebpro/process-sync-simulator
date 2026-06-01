/** Shared slow-teaching playback — students need time to see each step */

const Playback = {
  /** Slider 1 = slowest, 10 = faster (still readable) */
  getStepDelay(sliderValue) {
    const v = parseInt(sliderValue, 10) || 3;
    return 3200 - v * 260; // 1→2940ms, 5→1900ms, 10→600ms
  },

  getPhaseDelay(sliderValue) {
    const v = parseInt(sliderValue, 10) || 3;
    return 4500 - v * 350;
  },

  isSlowMode() {
    return document.getElementById("slow-teach-mode")?.checked !== false;
  },

  isAutoVisualize() {
    return document.getElementById("auto-visualize")?.checked !== false;
  },

  isAutoGantt() {
    return document.getElementById("auto-gantt")?.checked !== false;
  },

  isAutoSyncPlay() {
    return document.getElementById("auto-sync-play")?.checked !== false;
  },

  getSpeedSlider() {
    return document.getElementById("global-speed")?.value
      || document.getElementById("sync-speed")?.value
      || "3";
  },

  sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  },

  setProgress(barId, pct, labelId, text) {
    const bar = document.getElementById(barId);
    if (bar) bar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
    if (labelId && text !== undefined) {
      const el = document.getElementById(labelId);
      if (el) el.textContent = text;
    }
  },
};
