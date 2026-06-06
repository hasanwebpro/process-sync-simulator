"use strict";
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout  = "LAYOUT_16x9";
pres.title   = "Process Synchronization Simulator";
pres.author  = "Syed Hassan Bukhari, Huzaifa Ali Khan";

// ─────────────── PALETTE ───────────────────────────────────────────────────
const BG   = "0F172A";   // Very dark navy  — slide background
const MID  = "1E293B";   // Dark slate      — card background
const DEEP = "0D1526";   // Deeper navy     — inset panels
const BLUE = "2563EB";   // Royal blue
const CYAN = "06B6D4";   // Cyan accent
const LBL  = "38BDF8";   // Light blue
const WHT  = "FFFFFF";
const LG   = "CBD5E1";   // Light gray body text
const MG   = "94A3B8";   // Muted gray captions
const GRN  = "10B981";   // Green
const AMB  = "F59E0B";   // Amber
const RED  = "EF4444";   // Red/warning

// Fresh shadow every call (PptxGenJS mutates options — NEVER reuse)
const sh  = () => ({ type: "outer", blur: 8,  offset: 2,  angle: 135, color: "000000", opacity: 0.28 });
const shL = () => ({ type: "outer", blur: 14, offset: 4,  angle: 135, color: "000000", opacity: 0.35 });

// ─────────────── HELPERS ───────────────────────────────────────────────────
function T(slide, text, opts) { slide.addText(text, opts); }
function R(slide, x, y, w, h, fill, border, radius) {
  const opts = { x, y, w, h, fill: { color: fill }, line: { color: border, width: 1.5 }, shadow: sh() };
  if (radius) { opts.rectRadius = radius; slide.addShape(pres.shapes.ROUNDED_RECTANGLE, opts); }
  else { slide.addShape(pres.shapes.RECTANGLE, opts); }
}
function oval(slide, x, y, w, h, color, trans = 0) {
  slide.addShape(pres.shapes.OVAL, { x, y, w, h, fill: { color, transparency: trans }, line: { color, width: 0 } });
}
function hline(slide, x, y, w, color = BLUE, wt = 1) {
  slide.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color, width: wt } });
}
function vline(slide, x, y, h, color = BLUE, wt = 1) {
  slide.addShape(pres.shapes.LINE, { x, y, w: 0, h, line: { color, width: wt } });
}
function slideTitle(slide, text) {
  T(slide, text, { x: 0.45, y: 0.2, w: 9.1, h: 0.65, fontSize: 28, bold: true,
    color: WHT, align: "left", valign: "middle", margin: 0, fontFace: "Calibri" });
  // Subtle cyan bar left of title
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 0.22, w: 0.07, h: 0.6,
    fill: { color: CYAN }, line: { color: CYAN, width: 0 } });
  T(slide, text, { x: 0.62, y: 0.2, w: 9.1, h: 0.65, fontSize: 28, bold: true,
    color: WHT, align: "left", valign: "middle", margin: 0, fontFace: "Calibri" });
}
function card(slide, x, y, w, h, border = BLUE) {
  R(slide, x, y, w, h, MID, border);
}
function badge(slide, x, y, label, color = BLUE) {
  R(slide, x, y, 1.6, 0.32, color, color, 0.05);
  T(slide, label, { x, y, w: 1.6, h: 0.32, fontSize: 9, bold: true, color: WHT,
    align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });
}
function numCircle(slide, x, y, num, color = BLUE) {
  oval(slide, x, y, 0.42, 0.42, color, 0);
  T(slide, String(num), { x, y, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: WHT,
    align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });
}
function arrowRight(slide, x, y) {
  hline(slide, x, y, 0.28, CYAN, 2);
  // Arrowhead triangle
  slide.addShape(pres.shapes.RECTANGLE, { x: x + 0.24, y: y - 0.05, w: 0.1, h: 0.1,
    fill: { color: CYAN }, line: { color: CYAN, width: 0 }, rotate: 45 });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };

  // Decorative circles
  oval(s,  7.9, -1.6, 5.2, 5.2, "1C3560",  45);
  oval(s, -2.2,  2.5, 4.8, 4.8, CYAN,       87);
  oval(s,  5.0,  0.3, 1.2, 1.2, BLUE,       70);

  // Badge
  R(s, 0.5, 0.3, 2.9, 0.38, BLUE, BLUE, 0.06);
  T(s, "OPERATING SYSTEM  ·  COMPUTER SCIENCE", { x: 0.5, y: 0.3, w: 2.9, h: 0.38,
    fontSize: 8.5, bold: true, color: WHT, align: "center", valign: "middle", margin: 0 });

  // Title lines
  T(s, "Process Synchronization", { x: 0.5, y: 0.86, w: 9, h: 0.92,
    fontSize: 46, bold: true, color: WHT, align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });
  T(s, "Simulator", { x: 0.5, y: 1.75, w: 9, h: 0.88,
    fontSize: 52, bold: true, color: CYAN, align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });
  T(s, "An Interactive OS Learning Platform", { x: 1, y: 2.68, w: 8, h: 0.45,
    fontSize: 15, italic: true, color: MG, align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });

  // Bottom info panel
  R(s, 0.3, 3.28, 9.4, 2.0, MID, BLUE);
  vline(s, 3.55, 3.42, 1.72, BLUE);
  vline(s, 6.78, 3.42, 1.72, BLUE);

  T(s, [{ text: "23FA-040-SE", options: { bold: true, color: CYAN, breakLine: true } },
        { text: "Syed Hassan Bukhari", options: { color: WHT, breakLine: true } },
        { text: "Software Engineering", options: { color: MG } }],
    { x: 0.4, y: 3.32, w: 3.0, h: 1.85, fontSize: 12, align: "center", valign: "middle", fontFace: "Calibri" });

  T(s, [{ text: "24SP-032-SE", options: { bold: true, color: CYAN, breakLine: true } },
        { text: "Huzaifa Ali Khan", options: { color: WHT, breakLine: true } },
        { text: "Software Engineering", options: { color: MG } }],
    { x: 3.65, y: 3.32, w: 3.0, h: 1.85, fontSize: 12, align: "center", valign: "middle", fontFace: "Calibri" });

  T(s, [{ text: "Dept. of Computer Science", options: { bold: true, color: LBL, breakLine: true } },
        { text: "Batch: 2024 Spring  •  Section: A", options: { color: LG, breakLine: true } },
        { text: "Spring Semester 2026", options: { color: MG } }],
    { x: 6.88, y: 3.32, w: 2.7, h: 1.85, fontSize: 11, align: "center", valign: "middle", fontFace: "Calibri" });

  s.addNotes("Welcome everyone. This is our Operating Systems project — the Process Synchronization Simulator — a web-based interactive platform that makes CPU scheduling and synchronization concepts visible and step-by-step. I am Syed Hassan Bukhari, roll 23FA-040-SE, presenting with Huzaifa Ali Khan, roll 24SP-032-SE. We are from the Department of Computer Science, Software Engineering batch 2024, Section A, Spring 2026.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 2 — PROJECT OVERVIEW
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Project Overview");

  // Left column: description
  T(s, "What is this project?", { x: 0.45, y: 1.05, w: 4.5, h: 0.42,
    fontSize: 15, bold: true, color: LBL, fontFace: "Calibri" });
  T(s, "A four-phase interactive web simulator that connects CPU scheduling decisions to synchronization problems — and then shows how to fix them using real OS algorithms.",
    { x: 0.45, y: 1.48, w: 4.4, h: 0.88, fontSize: 12.5, color: LG, fontFace: "Calibri", valign: "top" });

  // Bullets
  const bullets = [
    ["Built with", "Python Flask + JavaScript"],
    ["Visualization", "HTML5 Canvas + DOM step replay"],
    ["Algorithms", "5 schedulers + 10 sync mechanisms"],
    ["Educational", "Step-by-step, pause/play/rewind"],
  ];
  bullets.forEach(([label, val], i) => {
    const y = 2.5 + i * 0.52;
    card(s, 0.45, y, 4.4, 0.44, CYAN);
    T(s, [{ text: label + ": ", options: { bold: true, color: CYAN } },
          { text: val, options: { color: LG } }],
      { x: 0.6, y, w: 4.1, h: 0.44, fontSize: 12, valign: "middle", fontFace: "Calibri" });
  });

  // Right column: 4 phase cards
  const phases = [
    { num: 1, title: "CPU Scheduling",    desc: "FCFS, SJF, SRTF, RR, Priority",    color: BLUE },
    { num: 2, title: "Problem Detection", desc: "Race, Deadlock, Starvation",         color: AMB  },
    { num: 3, title: "Synchronization",   desc: "Mutex, Semaphore, Monitor +7 more", color: CYAN },
    { num: 4, title: "Analysis Report",   desc: "Scoring, ranking, recommendations", color: GRN  },
  ];
  phases.forEach(({ num, title, desc, color }, i) => {
    const y = 1.02 + i * 1.12;
    card(s, 5.3, y, 4.35, 0.98, color);
    numCircle(s, 5.45, y + 0.27, num, color);
    T(s, title, { x: 6.05, y: y + 0.08, w: 3.5, h: 0.38, fontSize: 13, bold: true, color: WHT, fontFace: "Calibri" });
    T(s, desc,  { x: 6.05, y: y + 0.50, w: 3.5, h: 0.38, fontSize: 10.5, color: MG, fontFace: "Calibri" });
  });

  s.addNotes("This project is a full simulation environment split into four phases. Phase 1 runs CPU scheduling algorithms on user-defined processes and produces Gantt charts with metrics. Phase 2 replays that schedule against a shared resource without any synchronization to detect race conditions and other problems. Phase 3 applies one of ten synchronization mechanisms and shows a step-by-step animated visualization of processes entering and leaving the critical section. Phase 4 scores and ranks all techniques. The key idea is that all four phases operate on the same set of processes, so you can directly trace how a scheduling decision leads to a synchronization problem.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 3 — PROBLEM STATEMENT
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Problem Statement");

  T(s, "OS concepts are taught with static diagrams. Students rarely see the cause-and-effect chain that connects them.",
    { x: 0.45, y: 0.95, w: 9.1, h: 0.5, fontSize: 13, italic: true, color: MG, fontFace: "Calibri" });

  const problems = [
    { title: "Abstract Concepts",       color: RED,
      points: ["Critical sections explained with text only", "Peterson's / Dekker's seen as pseudo-code", "No step-by-step state walkthrough available"] },
    { title: "Hidden Cause & Effect",   color: AMB,
      points: ["Scheduling → synchronization link invisible", "Round Robin exposes more races than FCFS — rarely shown", "Students can't observe the interleaving that causes bugs"] },
    { title: "No Interactive Platform", color: CYAN,
      points: ["No single tool connects all OS phases", "Semaphore count changes not visualized live", "Difficult to compare 10 algorithms simultaneously"] },
  ];

  problems.forEach(({ title, color, points }, i) => {
    const x = 0.38 + i * 3.14;
    card(s, x, 1.55, 3.0, 3.7, color);
    R(s, x, 1.55, 3.0, 0.1, color, color);
    T(s, title, { x: x + 0.15, y: 1.68, w: 2.7, h: 0.48, fontSize: 13, bold: true,
      color: color, fontFace: "Calibri" });
    points.forEach((pt, j) => {
      T(s, [{ text: "▸  ", options: { color: color, bold: true } }, { text: pt, options: { color: LG } }],
        { x: x + 0.15, y: 2.28 + j * 0.62, w: 2.7, h: 0.55, fontSize: 11, fontFace: "Calibri", valign: "top" });
    });
  });

  s.addNotes("The core problem is that OS education is highly theoretical. Three specific gaps motivated this project. First, concepts like critical sections are described abstractly — students never see which processes overlap, what values get corrupted, or why. Second, the connection between scheduling policy and synchronization severity is almost never demonstrated: a Round Robin schedule creates far more interleaving than FCFS, which means far more race conditions. Third, there is no single interactive tool that ties together scheduling, problem detection, synchronization, and comparison in one session.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 4 — PROJECT OBJECTIVES
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Project Objectives");

  const objs = [
    { n: 1, color: BLUE, title: "Interactive CPU Scheduling",
      text: "Let students define processes, run 5 algorithms, and compare Gantt charts + metrics (CT, TAT, WT, RT) side by side in real time." },
    { n: 2, color: AMB, title: "Synchronization Problem Detection",
      text: "Automatically detect race conditions, critical section violations, deadlock, and starvation from the Phase 1 execution trace — without any extra user input." },
    { n: 3, color: CYAN, title: "Live Critical Section Visualization",
      text: "Show each process entering/leaving the shared resource graphically — active process glows inside the box, waiters queue outside with a directional arrow." },
    { n: 4, color: GRN, title: "Comparative Algorithm Analysis",
      text: "Score all 10 sync techniques on mutual exclusion correctness, deadlock freedom, and efficiency. Rank them automatically from real simulation data." },
  ];

  objs.forEach(({ n, color, title, text }, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.38 + col * 4.75;
    const y = 1.1  + row * 2.2;
    card(s, x, y, 4.5, 2.02, color);
    numCircle(s, x + 0.2, y + 0.18, n, color);
    T(s, title, { x: x + 0.78, y: y + 0.12, w: 3.58, h: 0.55,
      fontSize: 13.5, bold: true, color: WHT, fontFace: "Calibri", valign: "top" });
    T(s, text,  { x: x + 0.2, y: y + 0.75, w: 4.1, h: 1.15,
      fontSize: 11.5, color: LG, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("Our four objectives directly address the four gaps we identified. The first is about making scheduling tangible — students can add their own processes, choose any combination of algorithms, and instantly see the Gantt chart and metrics change. The second is automatic problem detection from real execution data, not just a static description. The third is the most visual part — the live canvas showing processes literally inside and outside the critical section. The fourth ties everything together with a scoring system that ranks algorithms based on actual simulation correctness, not hardcoded values.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 5 — APPLIED OS CONCEPTS
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Applied OS Concepts");

  const concepts = [
    { title: "CPU Scheduling",       color: BLUE, icon: "⚙",
      bullets: ["FCFS · SJF · SRTF", "Round Robin · Priority", "CT, TAT, WT, RT metrics"] },
    { title: "Critical Section",     color: CYAN, icon: "🔒",
      bullets: ["Mutual Exclusion", "Progress + Bounded Wait", "Entry / Exit sections"] },
    { title: "Software Solutions",   color: AMB, icon: "✦",
      bullets: ["Peterson's Algorithm", "Dekker's Algorithm", "Flag + Turn variables"] },
    { title: "Semaphores",           color: GRN, icon: "◎",
      bullets: ["Binary Semaphore P()/V()", "Counting Semaphore (N slots)", "No ownership requirement"] },
    { title: "Mutex Locks",          color: LBL, icon: "⬡",
      bullets: ["acquire() / release()", "Blocking (no busy-wait)", "Ownership enforced"] },
    { title: "Classic Problems",     color: "E879F9", icon: "⬢",
      bullets: ["Producer–Consumer", "Readers–Writers", "Monitor + Condition Vars"] },
  ];

  concepts.forEach(({ title, color, bullets }, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.38 + col * 3.12;
    const y = 1.05 + row * 2.2;
    card(s, x, y, 2.96, 2.05, color);
    // Colored accent strip
    R(s, x, y, 2.96, 0.08, color, color);
    T(s, title, { x: x + 0.15, y: y + 0.15, w: 2.65, h: 0.48,
      fontSize: 12.5, bold: true, color: color, fontFace: "Calibri" });
    bullets.forEach((b, j) => {
      T(s, [{ text: "• ", options: { color: color } }, { text: b, options: { color: LG } }],
        { x: x + 0.15, y: y + 0.7 + j * 0.43, w: 2.65, h: 0.38,
          fontSize: 10.5, fontFace: "Calibri", valign: "top" });
    });
  });

  s.addNotes("Six core OS concepts are implemented in this project. CPU Scheduling covers five classical algorithms with all standard metrics. The Critical Section concept covers the three correctness requirements from Silberschatz. Software solutions include Peterson's and Dekker's algorithms — these are important historically but both have limitations like busy-waiting and two-process-only restriction. Semaphores cover both binary and counting variants. Mutex locks add ownership semantics over binary semaphores. Finally, classic problems like Producer-Consumer, Readers-Writers, and Monitor are fully simulated with all their synchronization primitives working together.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 6 — METHODOLOGY
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Development Methodology");

  // Phase pipeline (horizontal flow)
  const phases = [
    { label: "Phase 1",  sub: "CPU Scheduling",       color: BLUE,  tools: "scheduler.py" },
    { label: "Phase 2",  sub: "Problem Detection",     color: AMB,   tools: "diagnostics.py" },
    { label: "Phase 3",  sub: "Synchronization",       color: CYAN,  tools: "sync_engine.py" },
    { label: "Phase 4",  sub: "Analysis & Report",     color: GRN,   tools: "analyzer.py" },
  ];
  phases.forEach(({ label, sub, color, tools }, i) => {
    const x = 0.38 + i * 2.32;
    R(s, x, 1.08, 2.1, 1.48, DEEP, color, 0.08);
    T(s, label, { x, y: 1.12, w: 2.1, h: 0.42, fontSize: 14, bold: true, color: color, align: "center", fontFace: "Calibri" });
    T(s, sub,   { x, y: 1.54, w: 2.1, h: 0.48, fontSize: 11, color: LG, align: "center", fontFace: "Calibri" });
    T(s, tools, { x, y: 2.0,  w: 2.1, h: 0.42, fontSize: 10, color: MG, align: "center", italic: true, fontFace: "Calibri" });
    if (i < 3) {
      T(s, "→", { x: x + 2.12, y: 1.42, w: 0.18, h: 0.42, fontSize: 20, bold: true, color: color, align: "center", fontFace: "Calibri" });
    }
  });

  // Tools & technologies
  T(s, "Tools & Technologies", { x: 0.45, y: 2.78, w: 4.5, h: 0.4,
    fontSize: 14, bold: true, color: LBL, fontFace: "Calibri" });
  const tools = [
    { label: "Backend",      val: "Python 3 · Flask REST API",         color: BLUE },
    { label: "Frontend",     val: "HTML5 · CSS3 · Vanilla JavaScript",  color: CYAN },
    { label: "Visualization",val: "HTML5 Canvas API · DOM rendering",   color: AMB  },
    { label: "Data Format",  val: "JSON step snapshots (deep-copied)",  color: GRN  },
  ];
  tools.forEach(({ label, val, color }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.38 + col * 4.75, y = 3.22 + row * 0.6;
    R(s, x, y, 4.5, 0.5, MID, color, 0.04);
    T(s, [{ text: label + ":  ", options: { bold: true, color } }, { text: val, options: { color: LG } }],
      { x: x + 0.18, y, w: 4.15, h: 0.5, fontSize: 11.5, valign: "middle", fontFace: "Calibri" });
  });

  s.addNotes("The project follows the four-phase pipeline directly. Each phase has its own Python engine module and builds on the previous phase's output. Phase 1 produces the CPU schedule. Phase 2 uses that schedule to detect problems. Phase 3 uses the Phase 1 process data to run synchronization simulations. Phase 4 analyzes all Phase 3 results. For the tech stack — we chose Python Flask because it keeps simulation logic cleanly separated from the presentation layer. The frontend uses no framework, just vanilla JavaScript and the Canvas API, which meant we had full control over every pixel of the visualization.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 7 — SYSTEM ARCHITECTURE
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "System Architecture");

  // 3-layer architecture
  const layers = [
    { label: "FRONTEND LAYER",  color: CYAN, y: 0.98,
      boxes: ["index.html", "sync-viz.js", "main.js", "style.css"] },
    { label: "API LAYER",       color: BLUE, y: 2.18,
      boxes: ["app.py  (Flask)", "/api/pipeline/phase1-4", "JSON Request/Response", "Validators"] },
    { label: "ENGINE LAYER",    color: AMB,  y: 3.38,
      boxes: ["scheduler.py", "sync_engine.py", "execution_engine.py", "diagnostics.py  |  analyzer.py"] },
  ];

  layers.forEach(({ label, color, y, boxes }) => {
    R(s, 0.35, y, 9.3, 1.05, DEEP, color);
    T(s, label, { x: 0.38, y: y + 0.08, w: 1.8, h: 0.9,
      fontSize: 10, bold: true, color: color, align: "center", valign: "middle", fontFace: "Calibri" });
    vline(s, 2.22, y, 1.05, color);
    T(s, boxes.join("    ·    "), { x: 2.3, y, w: 7.2, h: 1.05,
      fontSize: 11, color: LG, valign: "middle", fontFace: "Calibri" });
  });

  // Bidirectional arrows between layers
  [1.95, 3.3].forEach(y => {
    vline(s, 1.1, y, 0.28, BLUE, 2);
    T(s, "↑↓", { x: 0.8, y: y + 0.02, w: 0.6, h: 0.22,
      fontSize: 12, color: BLUE, align: "center", fontFace: "Calibri" });
    T(s, "HTTP / JSON", { x: 1.3, y: y + 0.03, w: 1.6, h: 0.2,
      fontSize: 9, italic: true, color: MG, fontFace: "Calibri" });
  });

  // Key design notes
  T(s, "Key Design Decisions", { x: 0.45, y: 4.56, w: 4.5, h: 0.36,
    fontSize: 12, bold: true, color: LBL, fontFace: "Calibri" });
  const notes = ["Stateless engines — safe across concurrent requests",
                 "Deep-copied snapshots — step replay correctness",
                 "ExecutionEngine weaves Phase 1 + Phase 3 timelines"];
  notes.forEach((n, i) => {
    T(s, [{ text: "▸  ", options: { color: CYAN, bold: true } }, { text: n, options: { color: LG } }],
      { x: 0.45, y: 4.93 + i * 0.22, w: 9, h: 0.22, fontSize: 10.5, fontFace: "Calibri" });
  });

  s.addNotes("The architecture has three layers. The Frontend is a single-page application — one HTML file, one CSS file, and several JavaScript modules. It talks to the backend via simple JSON HTTP requests. The API Layer is Flask with seven REST endpoints, one per simulation operation. The Engine Layer contains five independent Python modules: the CPU Scheduler, Sync Simulator, Execution Engine, Diagnostics Engine, and Analysis Engine. All engines are stateless objects — they take input, return output, and store no data between calls. This makes them safe to reuse across requests without data leaking between sessions. The Execution Engine is the most complex piece — it weaves the CPU Gantt chart with sync simulation steps into a single unified timeline that the frontend plays back.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 8 — CODE IMPLEMENTATION
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Code Implementation");

  // Code block (dark terminal)
  R(s, 0.38, 0.98, 5.6, 4.35, "0D1117", "38BDF8");
  T(s, "# engine/sync_engine.py  —  _step() snapshot", {
    x: 0.48, y: 1.02, w: 5.4, h: 0.3, fontSize: 9, color: MG, italic: true, fontFace: "Courier New" });

  const codeLines = [
    { t: "def _step(self, tick, processes, action,",  c: "79C0FF" },
    { t: "          *, critical_section=None,",        c: "79C0FF" },
    { t: "             waiting_queue=None,   ...):",    c: "79C0FF" },
    { t: "  return {",                                 c: LG },
    { t: "    'processes':  deepcopy(processes),",     c: "A5D6FF" },
    { t: "    'critical_section':  list(cs or []),",   c: "A5D6FF" },
    { t: "    'waiting_queue':     list(wq or []),",   c: "A5D6FF" },
    { t: "    'resources':   deepcopy(resources),",    c: "A5D6FF" },
    { t: "    'shared_vars': deepcopy(shared_vars),",  c: "A5D6FF" },
    { t: "  }",                                        c: LG },
    { t: "",                                           c: LG },
    { t: "# Peterson entry — P0 defers to P1",         c: "8B949E" },
    { t: "flag[0]=True; turn=1  # I defer to P1",      c: "FFD166" },
    { t: "flag[1]=True; turn=0  # P1: last write wins",c: "FFD166" },
    { t: "# turn==0 → P0 enters CS first",             c: "8B949E" },
    { t: 'emit("enter_cs","P0 enters", ["P0"],["P1"])',c: "A5D6FF" },
  ];
  codeLines.forEach(({ t, c }, i) => {
    T(s, t, { x: 0.5, y: 1.35 + i * 0.195, w: 5.3, h: 0.22,
      fontSize: 9.8, color: c, fontFace: "Courier New", margin: 0 });
  });

  // Side callout cards
  const callouts = [
    { color: CYAN, title: "Deep Copy Required",
      body: "Every mutable object is deep-copied. Without this, all recorded steps point to the same live object and show the final state only." },
    { color: AMB, title: "Peterson's Key Insight",
      body: "Both processes set turn to the OTHER process. Last write wins — so P1's write (turn=0) means P0 enters first. This is Silberschatz §6.3.1." },
    { color: GRN, title: "Waiting Queue",
      body: "waiting_queue is passed per step. The canvas renders these as amber chips below the Shared Resource box, with a dashed entry arrow." },
  ];
  callouts.forEach(({ color, title, body }, i) => {
    const y = 1.0 + i * 1.45;
    card(s, 6.2, y, 3.45, 1.32, color);
    T(s, title, { x: 6.35, y: y + 0.1,  w: 3.15, h: 0.38, fontSize: 12, bold: true, color, fontFace: "Calibri" });
    T(s, body,  { x: 6.35, y: y + 0.52, w: 3.15, h: 0.72, fontSize: 10, color: LG, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("Two of the most important code pieces are shown here. The _step() method is called by every algorithm to record a snapshot. The critical design decision is using Python's deepcopy on all mutable fields — processes dict, resources dict, shared_vars dict. Without deepcopy, every step snapshot would alias the same live object and show only the final state, making the educational step replay completely broken. The Peterson's code shows the turn mechanism: both processes set turn to the other process's index, meaning they each say 'I defer to you'. Since P1 writes last (turn=0), it defers to P0, so P0 enters the critical section first. This is a subtle but important point that's much clearer when you can step through the variable values one at a time.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 9 — SCREENSHOTS & OUTPUT
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Simulation Output — Screenshots");

  const screens = [
    { title: "Phase 1 — Gantt Charts",      color: BLUE, desc: "Multi-algorithm Gantt chart canvas. Pink = Round Robin, Teal = SJF. Metrics table below (CT, TAT, WT, RT per process)." },
    { title: "Phase 2 — Problem Detection", color: AMB,  desc: "Race condition and deadlock badges. Severity rating based on preemption level. Processes involved are highlighted." },
    { title: "Phase 3 — Live Canvas",       color: CYAN, desc: "Green-glowing process inside Shared Resource box. Amber chips in waiting queue below. Dashed upward arrow shows intent to enter." },
    { title: "Phase 4 — Comparison",        color: GRN,  desc: "Score table (0–100 per technique). Bar charts for score vs. overhead. Best technique highlighted with a crown badge." },
  ];

  screens.forEach(({ title, color, desc }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.38 + col * 4.82;
    const y = 1.05 + row * 2.28;
    card(s, x, y, 4.6, 2.1, color);
    // Screenshot placeholder box
    R(s, x + 0.15, y + 0.12, 2.55, 1.38, DEEP, color, 0.04);
    T(s, "[  Screenshot  ]", { x: x + 0.15, y: y + 0.12, w: 2.55, h: 1.38,
      fontSize: 11, color: MG, italic: true, align: "center", valign: "middle", fontFace: "Calibri" });
    T(s, title, { x: x + 2.82, y: y + 0.1, w: 1.62, h: 0.48,
      fontSize: 11, bold: true, color, fontFace: "Calibri", valign: "top" });
    T(s, desc, { x: x + 2.82, y: y + 0.6, w: 1.62, h: 1.38,
      fontSize: 9.5, color: LG, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("These four screenshots represent the main views of the simulator. Phase 1 shows the Gantt chart canvas with colored blocks for each algorithm — the primary algorithm (lowest average wait time) is highlighted. Phase 2 shows the problem detection matrix with severity badges — when you use Round Robin, you see far more red badges than with FCFS. Phase 3 is the most visual: you literally see a process inside the green Shared Resource box and others queued up below in amber. This canvas is drawn with PptxGenJS and updates every step. Phase 4 shows the technique comparison table and bar charts. Mutex Lock typically ranks first because it blocks waiting processes without burning CPU.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 10 — RESULTS & ANALYSIS
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Results & Analysis");

  // Native bar chart
  s.addChart(pres.charts.BAR, [{
    name: "Score / 100",
    labels: ["Mutex", "Monitor", "Bin. Sema.", "Count. Sema.", "Prod-Con", "Readers-W", "Peterson", "Dekker"],
    values: [95, 92, 90, 88, 87, 85, 78, 72],
  }], {
    x: 0.38, y: 0.98, w: 5.8, h: 4.28,
    barDir: "bar",
    chartColors: [BLUE, CYAN, LBL, GRN, GRN, GRN, AMB, AMB],
    chartArea: { fill: { color: MID }, roundedCorners: false },
    catAxisLabelColor: LG,
    valAxisLabelColor: MG,
    valGridLine: { color: "2D3748", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelColor: WHT,
    showLegend: false,
    barGapWidthPct: 40,
  });

  // Key findings
  const findings = [
    { color: GRN,  title: "Blocking > Busy-Wait",
      body: "Mutex and Monitor rank highest. They block waiting processes so the CPU is free for others — no spinning." },
    { color: AMB,  title: "Software Algorithms Limited",
      body: "Peterson and Dekker score lower due to busy-waiting. Both work correctly but waste CPU cycles." },
    { color: CYAN, title: "Scoring from Real Data",
      body: "Scores computed from actual simulation steps, not hardcoded. Mutual exclusion = 50 pts, deadlock-free = 30, correctness = 20." },
  ];
  findings.forEach(({ color, title, body }, i) => {
    const y = 1.0 + i * 1.42;
    card(s, 6.4, y, 3.22, 1.32, color);
    T(s, title, { x: 6.56, y: y + 0.1,  w: 2.9, h: 0.42, fontSize: 12, bold: true, color, fontFace: "Calibri" });
    T(s, body,  { x: 6.56, y: y + 0.54, w: 2.9, h: 0.7,  fontSize: 10, color: LG, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("The results show that blocking primitives consistently outperform busy-wait solutions. Mutex Lock scores 95 out of 100 — it provides strict mutual exclusion, is deadlock-free when used correctly, never burns CPU while waiting, and maintains correct shared counter values. Monitor scores 92 because the high-level abstraction eliminates the possibility of forgetting to acquire the lock. Peterson and Dekker score 78 and 72 respectively — they are correct (mutual exclusion is maintained) but lose points for busy-waiting. The scoring formula weights mutual exclusion at 50 points, deadlock freedom at 30 points, correctness at 20 points, minus an efficiency penalty for busy-wait events.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 11 — CHALLENGES FACED
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Challenges Faced & Solutions");

  const challenges = [
    {
      num: 1, color: RED,
      problem: "Deep Copy Bug",
      issue: "All simulation steps showed the same (final) state regardless of which step was selected.",
      fix: "Added Python deepcopy() to every mutable field in _step(). Algorithm methods mutate live objects — snapshots must be independent copies.",
      label: "Correctness Fix",
    },
    {
      num: 2, color: AMB,
      problem: "Canvas Height Mismatch",
      issue: "The canvas was short (260px) and the rest of the shared resource box area showed as an empty dark background.",
      fix: "Used ResizeObserver on both the canvas wrap and the side panel. When the side panel grew after data loaded, the observer fired _resize() to match the buffer height.",
      label: "Layout Fix",
    },
    {
      num: 3, color: CYAN,
      problem: "Waiting Queue Invisible",
      issue: "The waiting queue section never showed processes even though backend confirmed data was correct.",
      fix: "CSS max-height: 260px on .sync-side-panel clipped all content past the first two sections. Removing the constraint exposed all five side panel sections.",
      label: "CSS Fix",
    },
    {
      num: 4, color: GRN,
      problem: "Schedule ↔ Sync Weaving",
      issue: "CPU Gantt chart and sync events are generated independently with different PID naming conventions.",
      fix: "ExecutionEngine remaps generic PIDs (P0, P1) to real PIDs using Phase 1 execution order, then assigns each sync step to the CPU slice of the matching process.",
      label: "Logic Fix",
    },
  ];

  challenges.forEach(({ num, color, problem, issue, fix, label }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.38 + col * 4.82;
    const y = 1.05 + row * 2.22;
    card(s, x, y, 4.6, 2.08, color);
    numCircle(s, x + 0.18, y + 0.17, num, color);
    T(s, problem, { x: x + 0.75, y: y + 0.08, w: 3.6, h: 0.4,
      fontSize: 13, bold: true, color: WHT, fontFace: "Calibri" });
    R(s, x + 0.75, y + 0.52, 1.4, 0.22, color, color, 0.04);
    T(s, label, { x: x + 0.75, y: y + 0.52, w: 1.4, h: 0.22,
      fontSize: 8.5, bold: true, color: BG, align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });
    T(s, "Issue:  " + issue, { x: x + 0.18, y: y + 0.78, w: 4.22, h: 0.58,
      fontSize: 9.5, color: MG, fontFace: "Calibri", valign: "top" });
    T(s, "Fix:  " + fix, { x: x + 0.18, y: y + 1.38, w: 4.22, h: 0.6,
      fontSize: 9.5, color: LG, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("Four significant challenges came up during development. The deep copy bug was the hardest to diagnose because everything worked at first glance — the simulation ran, steps were recorded, and playback started. But every step showed identical state. The root cause was that Python dictionaries and lists are passed by reference, so all 30 steps in the list were pointing to the same live objects. The canvas height issue was a classic CSS vs JavaScript conflict — setting canvas.height as a JS attribute overrides CSS height. The waiting queue issue was purely a max-height constraint in CSS that we didn't notice. The weaving problem was the most complex algorithmically and required careful handling of edge cases like sync steps that span multiple CPU slices.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 12 — LEARNING OUTCOMES
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Learning Outcomes");

  // Left column: Technical
  card(s, 0.38, 1.02, 4.6, 4.28, BLUE);
  T(s, "Technical Skills", { x: 0.55, y: 1.1, w: 4.25, h: 0.5,
    fontSize: 15, bold: true, color: LBL, fontFace: "Calibri" });
  hline(s, 0.55, 1.6, 4.2, BLUE, 1);

  const techSkills = [
    "Python Flask REST API design",
    "HTML5 Canvas API — drawing, scaling, ResizeObserver",
    "Deep-copy simulation snapshot correctness",
    "Discrete-event simulation engine architecture",
    "Algorithm dispatch tables (clean extensibility)",
    "JSON-driven step-replay playback systems",
    "CSS layout debugging — max-height clipping",
  ];
  techSkills.forEach((skill, i) => {
    T(s, [{ text: "▸  ", options: { color: BLUE, bold: true } }, { text: skill, options: { color: LG } }],
      { x: 0.5, y: 1.72 + i * 0.5, w: 4.3, h: 0.46, fontSize: 11, fontFace: "Calibri", valign: "top" });
  });

  // Right column: Conceptual
  card(s, 5.22, 1.02, 4.6, 4.28, CYAN);
  T(s, "Conceptual Understanding", { x: 5.38, y: 1.1, w: 4.25, h: 0.5,
    fontSize: 15, bold: true, color: CYAN, fontFace: "Calibri" });
  hline(s, 5.38, 1.6, 4.2, CYAN, 1);

  const conceptSkills = [
    "Why preemption causes more race conditions",
    "mutex ownership vs. semaphore flexibility",
    "Peterson's turn mechanism — last-write-wins logic",
    "Counting semaphore modeling resource pools",
    "Producer-Consumer three-semaphore solution",
    "Scoring: mutual exclusion > deadlock > correctness",
    "How scheduling interleaving drives sync problems",
  ];
  conceptSkills.forEach((skill, i) => {
    T(s, [{ text: "▸  ", options: { color: CYAN, bold: true } }, { text: skill, options: { color: LG } }],
      { x: 5.3, y: 1.72 + i * 0.5, w: 4.35, h: 0.46, fontSize: 11, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("This project gave us two categories of learning. Technically, we learned how to build a proper REST API with Flask, how to use the HTML5 Canvas API for custom visualizations, and how important deep-copy correctness is in simulation code. The ResizeObserver approach for matching canvas height to dynamic content was something new. Conceptually, the biggest insight was that preemption and synchronization problems are directly linked — you can see this in the results when you switch from FCFS to Round Robin in Phase 1 and watch the Phase 2 problem count increase. We also gained a much clearer understanding of why mutex has ownership but semaphore does not, and what the practical consequences of that difference are.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 13 — CONCLUSION
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Conclusion");

  T(s, "The simulator successfully demonstrates all targeted OS concepts in an interactive, visually connected pipeline that makes the cause-and-effect chain from scheduling to synchronization fully traceable.",
    { x: 0.45, y: 0.95, w: 9.1, h: 0.6, fontSize: 12.5, italic: true, color: MG, fontFace: "Calibri" });

  const achievements = [
    { color: BLUE, icon: "✓", title: "4-Phase Pipeline",
      body: "Scheduling → Problem Detection → Synchronization → Analysis all connected on the same process data." },
    { color: CYAN, icon: "✓", title: "10 Algorithms Simulated",
      body: "Peterson, Dekker, Mutex, Binary/Counting Semaphore, Producer-Consumer, Readers-Writers, Monitor, Race Demo, Deadlock Demo." },
    { color: GRN,  icon: "✓", title: "Real-Data Scoring",
      body: "Technique scores computed from actual simulation metrics — mutual exclusion, deadlock freedom, efficiency — not hardcoded values." },
    { color: AMB,  icon: "✓", title: "Step-by-Step Playback",
      body: "34+ steps per simulation. Play, pause, step-forward, rewind, and jump to any step on the timeline. Full system state visible every tick." },
  ];

  achievements.forEach(({ color, title, body }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.38 + col * 4.82;
    const y = 1.72 + row * 1.9;
    card(s, x, y, 4.6, 1.72, color);
    // Check icon circle
    oval(s, x + 0.18, y + 0.18, 0.4, 0.4, color, 0);
    T(s, "✓", { x: x + 0.18, y: y + 0.18, w: 0.4, h: 0.4,
      fontSize: 13, bold: true, color: BG, align: "center", valign: "middle", fontFace: "Calibri" });
    T(s, title, { x: x + 0.72, y: y + 0.1, w: 3.7, h: 0.52,
      fontSize: 13, bold: true, color: WHT, fontFace: "Calibri" });
    T(s, body, { x: x + 0.18, y: y + 0.68, w: 4.22, h: 0.95,
      fontSize: 10.5, color: LG, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("The project achieved all four objectives. The four-phase pipeline is fully functional and connected — Phase 1 output feeds directly into Phase 2 detection, and Phase 1 process data is used for Phase 3 simulation. All ten synchronization mechanisms are implemented from scratch in Python with proper step-by-step state snapshots. The scoring system uses real simulation data and the weighting is grounded in OS theory: mutual exclusion is the primary goal, deadlock freedom is critical, correctness is measured against expected values. The step playback system proved to be the most educationally valuable feature — being able to pause at exactly the moment a process enters the critical section and see every other variable value at that instant is something no textbook diagram can replicate.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 14 — FUTURE ENHANCEMENTS
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  slideTitle(s, "Future Enhancements");

  const enhancements = [
    { n: 1, color: BLUE, title: "True Concurrent Mode",
      body: "Replace the discrete-event simulation with a real multi-threaded execution (Python threading or asyncio) to demonstrate genuine non-determinism — where the same code produces a different wrong answer every run." },
    { n: 2, color: CYAN, title: "Lamport's Bakery Algorithm",
      body: "Extend Peterson's software ME approach to N processes using Lamport's Bakery algorithm (1974), completing the progression from 2-process to N-process software solutions." },
    { n: 3, color: AMB,  title: "AI-Powered Explanation",
      body: "Integrate the already-wired OpenAI API endpoint (build_llm_context is complete) to generate plain-English step explanations, making the simulator usable without prior OS knowledge." },
    { n: 4, color: GRN,  title: "Memory Management Module",
      body: "Add Phase 5 covering paging, page replacement algorithms (FIFO, LRU, Optimal), and TLB simulation — completing the full process lifecycle from scheduling to memory." },
  ];

  enhancements.forEach(({ n, color, title, body }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.38 + col * 4.82;
    const y = 1.1  + row * 2.2;
    card(s, x, y, 4.6, 2.02, color);
    numCircle(s, x + 0.2, y + 0.18, n, color);
    T(s, title, { x: x + 0.78, y: y + 0.1, w: 3.65, h: 0.55,
      fontSize: 13, bold: true, color: WHT, fontFace: "Calibri" });
    T(s, body, { x: x + 0.2, y: y + 0.72, w: 4.2, h: 1.2,
      fontSize: 11, color: LG, fontFace: "Calibri", valign: "top" });
  });

  s.addNotes("Four meaningful extensions are planned. True concurrent mode is the most impactful — right now the simulation serializes events for clarity, but a real thread-based mode would show genuine race conditions where the output is different every single run, which is impossible to demonstrate with a deterministic simulation. Lamport's Bakery would make the software solutions section complete — Peterson and Dekker for 2 processes, Bakery for N. The AI explanation feature is mostly infrastructure-ready: the build_llm_context method already formats all results as a structured text block for the LLM. Memory management would turn the simulator into a complete OS concepts platform covering all the major topics from a standard OS course.");
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 15 — THANK YOU / Q&A
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };

  // Decorative orbs
  oval(s,  7.2, -1.4, 5.5, 5.5, BLUE,  55);
  oval(s, -2.0,  1.8, 5.0, 5.0, CYAN,  85);
  oval(s,  3.8,  4.5, 2.5, 2.5, BLUE,  70);

  T(s, "Thank You", { x: 0.5, y: 0.75, w: 9, h: 1.5,
    fontSize: 68, bold: true, color: WHT, align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });
  T(s, "Questions & Discussion", { x: 0.5, y: 2.25, w: 9, h: 0.6,
    fontSize: 24, italic: true, color: CYAN, align: "center", valign: "middle", margin: 0, fontFace: "Calibri" });

  hline(s, 2.5, 2.95, 5, BLUE, 1);

  // Student cards
  R(s, 1.5, 3.18, 3.0, 1.55, MID, BLUE);
  T(s, [
    { text: "Syed Hassan Bukhari\n", options: { bold: true, color: WHT, breakLine: true } },
    { text: "23FA-040-SE\n", options: { color: CYAN, breakLine: true } },
    { text: "hassanbk2003@gmail.com", options: { color: MG } },
  ], { x: 1.55, y: 3.22, w: 2.9, h: 1.45, fontSize: 11.5, align: "center", valign: "middle", fontFace: "Calibri" });

  R(s, 5.5, 3.18, 3.0, 1.55, MID, CYAN);
  T(s, [
    { text: "Huzaifa Ali Khan\n", options: { bold: true, color: WHT, breakLine: true } },
    { text: "24SP-032-SE\n", options: { color: CYAN, breakLine: true } },
    { text: "Dept. of CS  •  Spring 2026", options: { color: MG } },
  ], { x: 5.55, y: 3.22, w: 2.9, h: 1.45, fontSize: 11.5, align: "center", valign: "middle", fontFace: "Calibri" });

  T(s, "Operating System  |  Software Engineering Batch 2024  |  Section A", {
    x: 0.5, y: 4.9, w: 9, h: 0.35, fontSize: 10, color: MG,
    align: "center", valign: "middle", italic: true, fontFace: "Calibri" });

  s.addNotes("Thank you for your time. We are happy to take any questions. Some areas you might want to ask about: How the step snapshot deep-copy system works and why it was necessary. How the schedule-sync weaving algorithm assigns sync events to CPU slices. Why blocking primitives score higher than busy-wait solutions in the analysis. What the difference is between a mutex with ownership and a binary semaphore without ownership. How the Phase 2 problem detection determines race conditions from a CPU schedule. We are also happy to do a live demo of the simulator if time permits.");
}

// ═══════════════════════════════════════════════════════════════════════════
// WRITE FILE
// ═══════════════════════════════════════════════════════════════════════════
pres.writeFile({ fileName: "OS_Project_Presentation.pptx" })
  .then(() => console.log("Presentation saved: OS_Project_Presentation.pptx"))
  .catch(e  => { console.error("Error:", e.message); process.exit(1); });
