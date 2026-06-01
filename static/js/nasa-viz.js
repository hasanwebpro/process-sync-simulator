/** Vice City ambient — neon city lights drifting down */

const NasaViz = {
  canvas: null,
  ctx: null,
  lights: [],
  animId: null,

  init() {
    this.canvas = document.getElementById("starfield");
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.resize();
    window.addEventListener("resize", () => this.resize());
    this.spawnLights(100);
    this.animate();
  },

  resize() {
    if (!this.canvas) return;
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  },

  spawnLights(n) {
    const palette = [
      [255, 45, 120],   // hot pink
      [0, 212, 212],    // electric teal
      [176, 38, 255],   // purple
      [255, 215, 0],    // gold
    ];
    this.lights = Array.from({ length: n }, () => {
      const c = palette[Math.floor(Math.random() * palette.length)];
      return {
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        speed: Math.random() * 0.25 + 0.04,
        size: Math.random() * 1.6 + 0.3,
        r: c[0], g: c[1], b: c[2],
        opacity: Math.random() * 0.35 + 0.08,
      };
    });
  },

  animate() {
    if (!this.ctx) return;
    const { width, height } = this.canvas;
    this.ctx.fillStyle = "rgba(12, 0, 24, 0.22)";
    this.ctx.fillRect(0, 0, width, height);
    for (const l of this.lights) {
      l.y += l.speed;
      if (l.y > height) {
        l.y = 0;
        l.x = Math.random() * width;
      }
      this.ctx.fillStyle = `rgba(${l.r},${l.g},${l.b},${l.opacity})`;
      this.ctx.beginPath();
      this.ctx.arc(l.x, l.y, l.size, 0, Math.PI * 2);
      this.ctx.fill();
    }
    this.animId = requestAnimationFrame(() => this.animate());
  },
};

document.addEventListener("DOMContentLoaded", () => NasaViz.init());
