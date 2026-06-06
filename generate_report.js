const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, TableOfContents, LevelFormat,
  VerticalAlign, ImageRun,
} = require("docx");
const fs = require("fs");

// ─────────────────────────────────────────────
// COLOURS  (no leading #)
// ─────────────────────────────────────────────
const NAVY   = "0F172A";
const BLUE   = "2563EB";
const CYAN   = "06B6D4";
const WHITE  = "FFFFFF";
const LIGHT  = "EFF6FF";
const LGRAY  = "F1F5F9";
const MGRAY  = "CBD5E1";
const DGRAY  = "475569";
const BLACK  = "0F172A";

// ─────────────────────────────────────────────
// PAGE GEOMETRY  (A4, 1-inch margins)
// ─────────────────────────────────────────────
const PAGE_W  = 11906;   // A4 width  in DXA
const PAGE_H  = 16838;   // A4 height in DXA
const MARGIN  = 1440;    // 1 inch
const CONT_W  = PAGE_W - MARGIN * 2;   // 9026 DXA

// ─────────────────────────────────────────────
// NUMBERING CONFIG
// ─────────────────────────────────────────────
const NUMBERING = {
  config: [
    {
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "•",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } },
      }],
    },
    {
      reference: "sub-bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "◦",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 1080, hanging: 360 } } },
      }],
    },
  ],
};

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────
function hr(color = BLUE) {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color, space: 1 } },
    spacing: { before: 80, after: 80 },
    children: [],
  });
}

function spacer(pt = 80) {
  return new Paragraph({ spacing: { before: pt, after: pt }, children: [] });
}

function body(text, { bold = false, color = BLACK, size = 24, italic = false, align = AlignmentType.LEFT, before = 80, after = 80 } = {}) {
  return new Paragraph({
    alignment: align,
    spacing: { before, after, line: 360 },
    children: [new TextRun({ text, bold, color, size, italics: italic, font: "Calibri" })],
  });
}

function bullet(text, { bold = false, color = BLACK, sub = false } = {}) {
  return new Paragraph({
    numbering: { reference: sub ? "sub-bullets" : "bullets", level: 0 },
    spacing: { before: 40, after: 40, line: 320 },
    children: [new TextRun({ text, bold, color, size: 24, font: "Calibri" })],
  });
}

function codeBlock(lines) {
  return lines.map(line =>
    new Paragraph({
      shading: { fill: "1E1B2E", type: ShadingType.CLEAR },
      spacing: { before: 0, after: 0, line: 280 },
      indent: { left: 360 },
      children: [new TextRun({ text: line, font: "Courier New", size: 18, color: "A8D8A8" })],
    })
  );
}

function sectionBanner(number, title) {
  return [
    spacer(160),
    new Paragraph({
      shading: { fill: NAVY, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 0 },
      indent: { left: 0 },
      children: [
        new TextRun({ text: `  ${number}. ${title}  `, bold: true, size: 40, font: "Calibri", color: WHITE }),
      ],
    }),
    spacer(80),
  ];
}

function subHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, bold: true, size: 32, font: "Calibri", color: BLUE })],
  });
}

function subSubHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 160, after: 60 },
    children: [new TextRun({ text, bold: true, size: 28, font: "Calibri", color: CYAN })],
  });
}

function coverLine(text, { size = 24, bold = false, color = WHITE, after = 80 } = {}) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after },
    children: [new TextRun({ text, bold, size, font: "Calibri", color })],
  });
}

function infoTable(rows) {
  const brd = { style: BorderStyle.SINGLE, size: 1, color: MGRAY };
  const borders = { top: brd, bottom: brd, left: brd, right: brd };
  return new Table({
    width: { size: CONT_W, type: WidthType.DXA },
    columnWidths: [2800, 6226],
    rows: rows.map(([label, value], i) =>
      new TableRow({
        children: [
          new TableCell({
            borders, width: { size: 2800, type: WidthType.DXA },
            shading: { fill: i % 2 === 0 ? LIGHT : "DBEAFE", type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 180, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: label, bold: true, size: 22, font: "Calibri", color: NAVY })] })],
          }),
          new TableCell({
            borders, width: { size: 6226, type: WidthType.DXA },
            shading: { fill: i % 2 === 0 ? WHITE : LIGHT, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 180, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: value, size: 22, font: "Calibri", color: BLACK })] })],
          }),
        ],
      })
    ),
  });
}

function dataTable(headers, rows) {
  const brd = { style: BorderStyle.SINGLE, size: 1, color: MGRAY };
  const borders = { top: brd, bottom: brd, left: brd, right: brd };
  const colW = Math.floor(CONT_W / headers.length);
  const colWidths = headers.map(() => colW);
  return new Table({
    width: { size: CONT_W, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      // Header row
      new TableRow({
        tableHeader: true,
        children: headers.map(h =>
          new TableCell({
            borders, width: { size: colW, type: WidthType.DXA },
            shading: { fill: NAVY, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 140, right: 100 },
            verticalAlign: VerticalAlign.CENTER,
            children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: h, bold: true, size: 20, font: "Calibri", color: WHITE })] })],
          })
        ),
      }),
      // Data rows
      ...rows.map((row, ri) =>
        new TableRow({
          children: row.map((cell, ci) =>
            new TableCell({
              borders, width: { size: colW, type: WidthType.DXA },
              shading: { fill: ri % 2 === 0 ? WHITE : LGRAY, type: ShadingType.CLEAR },
              margins: { top: 80, bottom: 80, left: 140, right: 100 },
              children: [new Paragraph({ alignment: ci === 0 ? AlignmentType.LEFT : AlignmentType.CENTER, children: [new TextRun({ text: cell, size: 20, font: "Calibri", color: BLACK })] })],
            })
          ),
        })
      ),
    ],
  });
}

// ─────────────────────────────────────────────
// DOCUMENT CONTENT
// ─────────────────────────────────────────────

function buildDoc() {

  // ── COVER PAGE ──────────────────────────────────────────────────────────────
  const cover = [
    spacer(400),

    // Title banner
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: NAVY, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text: "  PROJECT REPORT  ", bold: true, size: 56, font: "Calibri", color: WHITE })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: BLUE, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text: "  Operating System  ", size: 36, font: "Calibri", color: WHITE })],
    }),

    spacer(200),

    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 40 },
      children: [new TextRun({ text: "Process Synchronization Simulator", bold: true, size: 48, font: "Calibri", color: NAVY })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 200 },
      children: [new TextRun({ text: "An Interactive OS Learning Platform", size: 28, font: "Calibri", color: DGRAY, italics: true })],
    }),

    hr(CYAN),
    spacer(200),

    infoTable([
      ["Department",  "Computer Science"],
      ["Program",     "Software Engineering"],
      ["Batch",       "2024 — Spring"],
      ["Section",     "A"],
      ["Course",      "Operating System"],
      ["Semester",    "Spring 2026"],
    ]),

    spacer(200),

    // Students table
    new Paragraph({
      spacing: { before: 80, after: 80 },
      children: [new TextRun({ text: "Submitted By", bold: true, size: 28, font: "Calibri", color: NAVY })],
    }),
    dataTable(
      ["Roll Number", "Student Name", "Section"],
      [
        ["23FA-040-SE", "Syed Hassan Bukhari",   "A"],
        ["24SP-032-SE", "Huzaifa Ali Khan",       "A"],
      ]
    ),

    spacer(200),

    new Paragraph({ children: [new PageBreak()] }),
  ];

  // ── TABLE OF CONTENTS ────────────────────────────────────────────────────────
  const toc = [
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 200, after: 80 },
      children: [new TextRun({ text: "Table of Contents", bold: true, size: 40, font: "Calibri", color: NAVY })],
    }),
    hr(BLUE),
    spacer(60),
    new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-3" }),
    new Paragraph({ children: [new PageBreak()] }),
  ];

  // ── SECTION 1 ────────────────────────────────────────────────────────────────
  const sec1 = [
    ...sectionBanner("1", "Project Title and Objective"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "1. Project Title and Objective", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    subHeading("1.1  Project Title"),
    body("Process Synchronization Simulator — An Interactive OS Learning Platform", { bold: true, color: BLUE, size: 26 }),

    spacer(80),
    subHeading("1.2  Objective"),
    body("The main goal of this project was to design and build a web-based simulation tool that makes CPU scheduling and process synchronization genuinely interactive. Instead of just reading about these topics, a student can configure real processes, choose their own scheduling algorithms, and literally watch the system state change step by step — seeing which process holds the CPU, which one is stuck waiting, and what happens inside the critical section at every tick."),
    body("The simulator is organized as a four-phase pipeline that mirrors how an OS textbook structures the subject matter:"),

    bullet("Phase 1 — CPU Scheduling: The user defines processes with arrival time, burst time, and priority. They can run any combination of five scheduling algorithms (FCFS, SJF, SRTF, Round Robin, Priority) and see Gantt charts, per-process metrics, and a multi-algorithm comparison side by side."),
    bullet("Phase 2 — Problem Detection: The same schedule from Phase 1 is replayed against a shared resource without any synchronization. The engine detects race conditions, critical section violations, deadlock potential, and starvation based on the real execution interleaving."),
    bullet("Phase 3 — Synchronization: Ten different synchronization mechanisms can be applied to the same set of processes. For each one, the simulator produces a step-by-step walkthrough where you can see a process entering the critical section (shown inside the shared resource box on the canvas), others queuing up outside, and the lock state changing in real time."),
    bullet("Phase 4 — Analysis Report: An analysis engine scores and ranks all techniques based on actual simulation metrics — mutual exclusion correctness, deadlock freedom, and efficiency overhead."),

    spacer(80),
    body("What makes this different from most educational tools is that all four phases share the same process data. The scheduling decision from Phase 1 directly affects what problems appear in Phase 2, which then motivates the synchronization choices in Phase 3. That cause-and-effect chain is usually invisible to students reading a textbook, but here it is the whole point."),
  ];

  // ── SECTION 2 ────────────────────────────────────────────────────────────────
  const sec2 = [
    spacer(120),
    ...sectionBanner("2", "Problem Statement"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "2. Problem Statement", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    body("Operating Systems is one of the hardest subjects to truly understand, not because the individual concepts are complicated, but because they only make sense in relation to each other. Scheduling interleaving causes synchronization problems. Synchronization mechanisms fix those problems. But you rarely see that complete chain demonstrated in one place."),
    body("The specific gaps we wanted to address with this project were:"),

    bullet("Race conditions are universally described as 'two processes writing to shared memory at the same time,' but students rarely see the actual timeline — which two processes, what values were read, what the corrupted output looks like. Without that, the concept stays abstract."),
    bullet("The relationship between preemptive scheduling and synchronization problems is almost never shown interactively. A Round Robin scheduler creates far more interleaving than FCFS, which means it exposes far more potential for races and critical section violations. This connection is mentioned in textbooks but never demonstrated live."),
    bullet("Algorithms like Peterson's Solution and Dekker's Algorithm are typically presented as pseudo-code that students memorize for exams. The purpose of each individual step — why flag[i] is set before turn, what happens if you reverse the order — is lost unless you can run through the algorithm and see the state change after each instruction."),
    bullet("Classic synchronization problems like Producer-Consumer and Readers-Writers are solved using semaphores in textbooks, but students struggle to see why the solution works. Watching a process block when the buffer is full, watching the semaphore count decrement, and seeing another process wake up when space opens up is far more effective than reading the pseudo-code."),

    spacer(80),
    body("On the technical side, there was also the challenge of building a simulation that is both educationally faithful and visually compelling. The simulation steps needed to be deeply connected to the actual concepts — each step should correspond to a real operation in the algorithm, not a simplified animation that glosses over the details."),
    body("The solution was to implement every algorithm from scratch in Python, producing step-by-step snapshots of the complete system state (all process states, lock values, waiting queues, shared variable values) at every meaningful event. These snapshots are then played back on the frontend with full control — students can step forward one tick at a time, play at adjustable speed, rewind, or jump to any point in the timeline."),
  ];

  // ── SECTION 3 ────────────────────────────────────────────────────────────────
  const sec3 = [
    spacer(120),
    ...sectionBanner("3", "Applied Operating System Concepts"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "3. Applied Operating System Concepts", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    subHeading("3.1  CPU Scheduling"),
    body("CPU scheduling determines the order in which processes use the processor. Since most modern computers have a single CPU (or at least a limited number of cores), the scheduler decides who runs next whenever the CPU becomes available."),
    body("Five classical scheduling algorithms are implemented in this project:"),

    spacer(60),
    dataTable(
      ["Algorithm", "Type", "Key Property", "Best For"],
      [
        ["FCFS",         "Non-preemptive", "Arrival order; no starvation for short waits",    "Batch jobs with similar burst times"],
        ["SJF",          "Non-preemptive", "Shortest burst first; minimizes average wait",     "Systems where burst times are known"],
        ["SRTF",         "Preemptive",     "Preempts if a shorter job arrives",                "Minimizing average turnaround time"],
        ["Round Robin",  "Preemptive",     "Fixed quantum; fair CPU sharing",                  "Interactive / time-sharing systems"],
        ["Priority",     "Non-preemptive", "Higher priority runs first",                       "Real-time and critical systems"],
      ]
    ),
    spacer(80),

    body("The key metrics computed for each process are:"),
    bullet("Completion Time (CT) — the clock tick when the process finishes execution"),
    bullet("Turnaround Time (TAT) = CT − Arrival Time — total time from arrival to completion"),
    bullet("Waiting Time (WT) = TAT − Burst Time — time spent waiting in the ready queue"),
    bullet("Response Time (RT) = first CPU tick − Arrival Time — how quickly a process first gets the CPU"),
    bullet("Throughput = n / (last CT − first Arrival) — processes completed per unit time"),

    spacer(80),
    body("One important observation from running these algorithms: preemptive algorithms (SRTF and Round Robin) generate many more context switches, which directly increases the chance of interleaving between multiple processes accessing shared resources. This is exactly why Phase 2 detects more synchronization problems when the Phase 1 schedule was preemptive."),

    subHeading("3.2  The Critical Section Problem"),
    body("Whenever multiple processes share a resource — a memory variable, a file, a hardware device — there is a risk that concurrent access corrupts the data or leads to inconsistent results. The code segment where a process accesses the shared resource is called the critical section."),
    body("A correct synchronization solution must satisfy three properties (Silberschatz §6.2):"),
    bullet("Mutual Exclusion — only one process can be inside the critical section at any time"),
    bullet("Progress — if no process is in the CS and one wants to enter, the decision about who enters next cannot be postponed forever"),
    bullet("Bounded Waiting — there is a limit on how many times other processes can enter the CS before a waiting process is granted entry"),

    subHeading("3.3  Software-Only Solutions"),
    body("Before hardware support for atomic operations was widely available, computer scientists developed software algorithms to achieve mutual exclusion using only ordinary reads and writes."),

    subSubHeading("Peterson's Solution"),
    body("Peterson's algorithm uses two shared variables: a flag array (flag[i] = true means process i wants to enter) and a turn variable (the process that must defer when both want to enter simultaneously). The entry protocol sets flag[i] = true, then sets turn = j (defer to the other), then busy-waits while the other process wants in AND it is their turn to defer. This guarantees all three correctness properties but works only for two processes."),

    subSubHeading("Dekker's Algorithm"),
    body("Dekker's algorithm was the first correct software solution to the critical section problem. It uses a similar flag mechanism but also a turn variable that explicitly decides who defers when both processes want to enter at the same time. Unlike Peterson, it explicitly alternates who defers and who gets priority, making the deferral behavior more explicit."),

    subHeading("3.4  Hardware-Assisted Synchronization"),

    subSubHeading("Mutex Lock"),
    body("A mutex (mutual exclusion lock) provides acquire() and release() operations. acquire() atomically checks and sets the lock. If the lock is already held, the calling process is added to a FIFO wait queue and put to sleep (blocking wait — no CPU burn). release() wakes the next waiter or clears the lock. The key distinction from semaphores is ownership: only the process that acquired the mutex can release it."),

    subSubHeading("Binary Semaphore"),
    body("A semaphore is an integer variable accessed only through atomic P() (wait/decrement) and V() (signal/increment) operations. A binary semaphore has values 0 or 1 and behaves like a mutex, with one important difference: any process can call V(), not just the one that called P(). This makes binary semaphores more flexible but also easier to misuse."),

    subSubHeading("Counting Semaphore"),
    body("A counting semaphore can hold values from 0 up to N, where N represents the number of available resource instances. It is the correct tool when you want to allow up to N processes into the critical section simultaneously — for example, allowing at most 3 simultaneous database connections while blocking the 4th."),

    subHeading("3.5  Classic Synchronization Problems"),

    subSubHeading("Producer-Consumer (Bounded Buffer)"),
    body("A producer process generates data and puts it into a fixed-size buffer. A consumer process takes data out. The challenge is preventing the producer from writing to a full buffer and the consumer from reading from an empty one. The solution uses three synchronization primitives: a mutex for mutual exclusion, an 'empty' semaphore (initialized to buffer size), and a 'full' semaphore (initialized to 0)."),

    subSubHeading("Readers-Writers Problem"),
    body("Multiple reader processes can read a shared database simultaneously without problems. But a writer process needs exclusive access. The challenge is allowing concurrent reads while ensuring writers get exclusive access. The first Readers-Writers problem (readers-preference) is implemented here, where no reader waits unless a writer already has access."),

    subSubHeading("Monitor with Condition Variables"),
    body("A monitor is a high-level synchronization construct that encapsulates shared data and the operations on it. All access to the shared data is through the monitor procedures, which guarantee mutual exclusion automatically. Condition variables (wait() and signal()) inside the monitor allow processes to wait for specific conditions to become true without holding the monitor lock."),

    subHeading("3.6  Synchronization Failure Modes"),
    body("The simulator also demonstrates what happens when synchronization is absent or incorrectly implemented:"),

    bullet("Race Condition — two processes read-modify-write a shared counter without locking. Depending on execution order, the counter ends up with the wrong value. The simulator shows the interleaved operations and the corrupted result."),
    bullet("Deadlock — two processes each hold one resource and wait for the other. Circular wait (Silberschatz §8.3) means neither can proceed. The simulator shows the hold-and-wait state frozen indefinitely."),
    bullet("Starvation — a process waits far longer than its peers because other processes keep getting scheduled ahead. Detected from the waiting time metrics of Phase 1."),
  ];

  // ── SECTION 4 ────────────────────────────────────────────────────────────────
  const sec4 = [
    spacer(120),
    ...sectionBanner("4", "Methodology and Implementation"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "4. Methodology and Implementation", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    subHeading("4.1  System Architecture"),
    body("The simulator is a three-tier web application:"),
    bullet("Backend — Python Flask serves a REST API. All simulation logic lives here in the engine/ package. The Flask layer handles HTTP routing, request validation, and JSON serialization. The engine modules are stateless, which means they can be safely reused across requests without data leaking between sessions."),
    bullet("API Layer — Seven REST endpoints expose the simulation capabilities. The most important ones are POST /api/pipeline/phase2 (run sync simulation on a Phase 1 workload) and POST /api/pipeline/phase1 (run scheduling algorithms)."),
    bullet("Frontend — A single-page application built with vanilla JavaScript, HTML, and CSS. No framework. The visualization runs on an HTML5 Canvas element using a Vice City neon color palette. All step playback, timeline navigation, and UI updates happen in the browser without round-trips to the server after the initial simulation data is loaded."),

    spacer(60),
    dataTable(
      ["Module", "File", "Responsibility"],
      [
        ["Scheduler",         "engine/scheduler.py",         "FCFS, SJF, SRTF, Round Robin, Priority"],
        ["Sync Simulator",    "engine/sync_engine.py",       "10 sync algorithm simulations"],
        ["Execution Engine",  "engine/execution_engine.py",  "Weaves Phase 1 + Phase 3 into unified timeline"],
        ["Diagnostics",       "engine/diagnostics.py",       "Phase 2 problem detection"],
        ["Analysis Engine",   "engine/analyzer.py",          "Scoring and ranking in Phase 4"],
        ["Flask App",         "app.py",                      "REST API routing and validation"],
        ["Sync Viz",          "static/js/sync-viz.js",       "Canvas drawing and playback"],
        ["Main JS",           "static/js/main.js",           "Phase orchestration and API calls"],
      ]
    ),
    spacer(80),

    subHeading("4.2  Phase 1 — CPU Scheduling Engine"),
    body("The CPUScheduler class implements all five algorithms as discrete-event simulations. Each algorithm takes a list of process dictionaries (pid, arrival, burst, priority) and produces a Gantt chart, a per-process metrics table, and a timeline enriched with color coding for the frontend."),
    body("The scheduler uses a dispatch table — a dictionary mapping algorithm ID strings to method references. This design makes it trivial to add new algorithms: just implement a new method and add one line to the dictionary. The multi-algorithm pipeline in Phase 1 runs all selected algorithms through the same dispatch table and automatically selects the primary algorithm (lowest average waiting time) to drive Phase 2."),

    subHeading("4.3  Phase 2 — Diagnostics Engine"),
    body("The DiagnosticsEngine replays the Phase 1 CPU schedule against a shared resource without any locking. It models what would happen if the processes accessed the shared counter directly, concurrent with whoever else is on the CPU at the same time."),
    body("Detection methodology:"),
    bullet("Race Condition and CS Violation — detected from overlapping execution windows. When two processes are both 'in-flight' on the CPU within the same time range, there is a potential read-modify-write overlap. Preemptive schedules produce far more overlap than non-preemptive ones, which is why FCFS typically shows fewer race conditions than Round Robin."),
    bullet("Deadlock — modelled as hold-and-wait between the first two processes on two separate resources. If both processes acquire one resource and then request the other, circular wait is detected."),
    bullet("Starvation — computed directly from the Phase 1 waiting time metrics. A process is considered starved if its waiting time deviates more than a threshold from the average waiting time."),

    subHeading("4.4  Phase 3 — Synchronization Simulator and Execution Engine"),
    body("The SyncSimulator class implements ten synchronization scenarios. Each algorithm method produces a list of step dictionaries (snapshots) and a summary dictionary. Every step records the complete system state at that moment: all process states (READY/RUNNING/WAITING/BLOCKED/TERMINATED), the critical section occupants, the waiting queue, resource lock values, and shared variable values."),
    body("The ExecutionEngine then weaves the Phase 1 CPU schedule with these sync steps into a unified timeline. The weaving process works as follows:"),
    bullet("For each CPU slice in the Gantt chart, a 'cpu_dispatch' step is inserted showing which process went on the CPU and when."),
    bullet("The sync steps that involve the active CPU process are then pulled from the sync simulation and appended, tagged with the CPU interval they belong to."),
    bullet("A 'cpu_release' step marks the end of each slice."),
    bullet("Any remaining sync steps that did not map to a specific CPU slice are flushed at the end."),
    body("This produces an integrated_steps list where every event has a phase tag ('scheduling' or 'sync_during_execution'), a global tick, a CPU interval, and the full system state. The frontend plays this list back exactly as recorded."),

    subHeading("4.5  Phase 4 — Analysis Engine"),
    body("The AnalysisEngine scores each sync technique based on the actual simulation output, not hardcoded values. The scoring formula is:"),

    ...codeBlock([
      "Score = 50 × mutual_exclusion_maintained   (binary: 0 or 50)",
      "      + 30 × deadlock_free                  (binary: 0 or 30)",
      "      + 20 × correctness_ratio              (0.0 to 1.0, × 20)",
      "      − efficiency_penalty                  (0 to 20, based on busy-wait count)",
    ]),

    spacer(80),
    body("The weighting is based on OS theory: mutual exclusion is the primary goal (highest weight), deadlock is catastrophic (second highest), correctness of shared data is measured against an expected value, and efficiency penalizes busy-waiting since that wastes CPU time."),

    subHeading("4.6  Frontend Visualization"),
    body("The visualization layer uses an HTML5 Canvas for the main simulation display and DOM elements for the side panel. The canvas draws the shared resource box, shows the active process inside it with a green glow when the critical section is occupied, and shows the waiting queue as amber-colored chips below the box with a dashed upward arrow indicating they want to enter."),
    body("The step timeline at the bottom of the page shows every simulation step as a colored tile — pink for scheduling steps, teal for sync steps, green for the final completion step. Clicking any tile jumps the simulation to that step. The playback controls allow play, pause, step-forward, and rewind at an adjustable speed."),
  ];

  // ── SECTION 5 ────────────────────────────────────────────────────────────────
  const sec5 = [
    spacer(120),
    ...sectionBanner("5", "Code Explanation"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "5. Code Explanation", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    subHeading("5.1  Simulation Step Snapshot System"),
    body("Every simulation algorithm calls a central _step() method to record a snapshot. The critical design decision here is deep-copying every mutable object:"),

    ...codeBlock([
      "def _step(self, tick, processes, action, message,",
      "          *, critical_section=None, waiting_queue=None,",
      "          resources=None, shared_vars=None):",
      "    return {",
      '        "tick":             tick,',
      '        "processes":        deepcopy(processes),',
      '        "action":           action,',
      '        "message":          message,',
      '        "critical_section": list(critical_section) if critical_section else [],',
      '        "waiting_queue":    list(waiting_queue)    if waiting_queue    else [],',
      '        "resources":        deepcopy(resources)    if resources        else {},',
      '        "shared_vars":      deepcopy(shared_vars)  if shared_vars      else {},',
      "    }",
    ]),

    spacer(80),
    body("The deep copy is not optional. All algorithm methods hold live references to dictionaries and lists (the process state table, the waiting queue, the shared counter) and mutate them as the simulation progresses. Without deepcopy, every recorded step would point to the same live object and show its final state rather than its state at the moment of recording. This is a correctness requirement for the step-by-step replay to work correctly."),

    subHeading("5.2  Peterson's Algorithm"),
    body("The Peterson implementation simulates both processes competing for the critical section across multiple iterations:"),

    ...codeBlock([
      "# Both processes signal intent",
      "flag[0] = True; flag[1] = True",
      "emit('request_cs', 'Both want CS', [], ['P0', 'P1'])",
      "",
      "# P0 defers to P1; P1 defers to P0 — last write wins (turn=0)",
      "turn = 1   # P0 sets turn=1",
      "turn = 0   # P1 sets turn=0  (last write wins)",
      "",
      "# P1 must wait: flag[0]==True AND turn==0",
      "procs['P1'] = 'WAITING'",
      "emit('wait', 'P1 busy-waits', [], ['P1'])",
      "",
      "# P0 enters: turn==0, so P0 is NOT the one that must defer",
      "procs['P0'] = 'RUNNING'",
      "emit('enter_cs', 'P0 enters CS', ['P0'], ['P1'])",
      "",
      "# P0 exits, sets flag[0]=False — P1 can now enter",
      "flag[0] = False",
      "emit('exit_cs', 'P0 releases CS', [], ['P1'])",
    ]),

    spacer(80),
    body("The turn variable is the clever part. Both P0 and P1 set turn to the OTHER process, meaning 'I will defer to you.' Since both set it, the last write wins — turn ends up as 0, meaning P0 is the one to whom the other is deferring. So P0 gets to enter first. This is the standard Silberschatz §6.3.1 analysis, but seeing the actual variable values changing step by step makes it much clearer."),

    subHeading("5.3  Mutex Lock with FIFO Wait Queue"),
    body("The mutex implementation adds blocked processes to an explicit queue, which is shown in the waiting queue visualization:"),

    ...codeBlock([
      "for pid in sorted(procs.keys()):",
      "    procs[pid] = 'RUNNING'",
      "    emit('request_lock', f'{pid} calls acquire(mutex)', [])",
      "",
      "    if lock:",
      "        procs[pid] = 'BLOCKED'",
      "        queue.append(pid)",
      "        emit('blocked', f'{pid} blocked — mutex held', [])",
      "    else:",
      "        lock = True",
      "        procs[pid] = 'RUNNING'",
      "        emit('acquire', f'{pid} acquires mutex', [pid])",
      "        counter += 1",
      "        emit('critical_section', f'{pid} in CS — counter={counter}', [pid])",
      "        lock = False",
      "        emit('release', f'{pid} releases mutex', [])",
    ]),

    spacer(80),
    body("When a process is blocked, it appears in the waiting_queue field of the step snapshot, which is then rendered as amber chips below the shared resource box in the canvas visualization. When the lock is released and a process enters the CS, it moves into the critical_section field and appears inside the box with a green glow."),

    subHeading("5.4  Schedule-Sync Weaving"),
    body("The most complex part of the implementation is the ExecutionEngine._weave_schedule_sync() method, which merges the CPU Gantt chart with sync events:"),

    ...codeBlock([
      "for seg in gantt:",
      "    pid = seg['pid']",
      "    cpu = {'start': seg['start'], 'end': seg['end']}",
      "",
      "    # Insert CPU dispatch marker step",
      "    merged.append({ 'phase': 'scheduling',",
      "                     'action': 'cpu_dispatch',",
      "                     'active_cpu': pid, ... })",
      "",
      "    # Pull sync steps that belong to this CPU slice",
      "    slice_steps, sync_idx = self._pull_sync_steps_for_cpu_slice(",
      "        sync_steps, sync_idx, pid, order)",
      "",
      "    for step in slice_steps:",
      "        merged.append({ **step,",
      "                         'phase': 'sync_during_execution',",
      "                         'cpu_interval': cpu,",
      "                         'active_cpu': pid })",
      "",
      "    merged.append({ 'phase': 'scheduling',",
      "                     'action': 'cpu_release', ... })",
    ]),

    spacer(80),
    body("The _pull_sync_steps_for_cpu_slice method determines which sync steps belong to a given CPU slice by checking whether the active process appears in the step's processes, critical_section, or waiting_queue fields. This ensures the sync events are shown alongside the correct CPU scheduling context."),
  ];

  // ── SECTION 6 ────────────────────────────────────────────────────────────────
  const sec6 = [
    spacer(120),
    ...sectionBanner("6", "Screenshots of Output / Simulation"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "6. Screenshots of Output / Simulation", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    body("The following describes the main views of the simulator and what each one shows. The application uses a dark Vice City neon color scheme with pink, teal, green, and amber accents against a deep navy background."),

    subHeading("6.1  Phase 1 — CPU Scheduling View"),
    body("The Phase 1 control panel on the left allows the user to add processes by entering a PID, arrival time, burst time, and priority. A process table below the form shows all added processes. On the right, after running the simulation, a multi-algorithm Gantt chart is drawn on an HTML5 Canvas showing each process's CPU slices as colored blocks across a time axis."),
    body("Below the Gantt chart, a metrics table shows CT, TAT, WT, and RT for each process under each algorithm, with per-column averages highlighted. The algorithm with the lowest average waiting time is automatically promoted as the primary algorithm for Phase 2."),

    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 40 },
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, bottom: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, left: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, right: { style: BorderStyle.SINGLE, size: 4, color: MGRAY } },
      shading: { fill: LGRAY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "[Screenshot: Phase 1 — Multi-algorithm Gantt chart with process metrics table]", size: 20, font: "Calibri", color: DGRAY, italics: true })],
    }),
    body("Figure 6.1 — Phase 1 output showing Round Robin (q=2) and SJF Gantt charts side-by-side with per-process CT, TAT, WT, and RT metrics.", { italic: true, color: DGRAY, size: 20, align: AlignmentType.CENTER }),

    spacer(80),
    subHeading("6.2  Phase 2 — Problem Detection View"),
    body("After Phase 1 completes, the Phase 2 section shows a problem detection matrix. Each detected synchronization problem (race condition, CS violation, deadlock, starvation) is listed with a badge indicating its severity and whether it was detected (red warning icon) or not (green check). The view also shows which processes were involved and provides a brief explanation of why the problem occurred given the Phase 1 scheduling choice."),

    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 40 },
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, bottom: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, left: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, right: { style: BorderStyle.SINGLE, size: 4, color: MGRAY } },
      shading: { fill: LGRAY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "[Screenshot: Phase 2 — Problem detection matrix showing race conditions and deadlock risk]", size: 20, font: "Calibri", color: DGRAY, italics: true })],
    }),
    body("Figure 6.2 — Phase 2 problem detection results for a Round Robin schedule. Race conditions and CS violations are detected due to high interleaving.", { italic: true, color: DGRAY, size: 20, align: AlignmentType.CENTER }),

    spacer(80),
    subHeading("6.3  Phase 3 — Live Execution Canvas"),
    body("The Phase 3 simulation view is the most visually rich part of the application. The left side shows a large HTML5 Canvas with the Shared Resource box drawn in the center. When a process holds the mutex, it appears inside the box as a glowing green chip with the process ID. Processes in the waiting queue appear as amber-colored chips below the box, numbered in queue order (#1, #2, ...), with a dashed upward arrow indicating they are attempting to enter the critical section."),

    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 40 },
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, bottom: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, left: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, right: { style: BorderStyle.SINGLE, size: 4, color: MGRAY } },
      shading: { fill: LGRAY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "[Screenshot: Phase 3 — P2 inside the green Shared Resource box; P1 and P3 waiting below with amber chips and upward arrow]", size: 20, font: "Calibri", color: DGRAY, italics: true })],
    }),
    body("Figure 6.3 — Phase 3 live execution. P2 is inside the critical section (green glow). P1 and P3 are shown outside in the waiting queue with a dashed entry arrow.", { italic: true, color: DGRAY, size: 20, align: AlignmentType.CENTER }),

    spacer(80),
    subHeading("6.4  Step Timeline and Side Panel"),
    body("Directly below the canvas, a step timeline shows every simulation step as a colored tile. Pink tiles are CPU scheduling steps, teal tiles are sync steps, and the final green tile marks completion. Clicking any tile jumps the playback to that step instantly."),
    body("The right side panel shows real-time process state chips (each process colored by state), lock/semaphore values, the current waiting queue, a human-readable explanation of what is happening at this step, and a CS flow diagram showing which stage of the entry-CS-exit cycle the active process is in."),

    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 40 },
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, bottom: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, left: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, right: { style: BorderStyle.SINGLE, size: 4, color: MGRAY } },
      shading: { fill: LGRAY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "[Screenshot: Step timeline showing pink CPU steps and teal Sync steps; side panel with process state chips and CS flow diagram]", size: 20, font: "Calibri", color: DGRAY, italics: true })],
    }),
    body("Figure 6.4 — Step timeline and side panel. Currently on Step 8 (CPU dispatch). Teal tiles represent sync events during each CPU slice.", { italic: true, color: DGRAY, size: 20, align: AlignmentType.CENTER }),

    spacer(80),
    subHeading("6.5  Phase 4 — Technique Comparison"),
    body("The technique comparison section runs all ten synchronization algorithms against the same workload and scores them. Results are displayed in a problem prevention matrix (which algorithm prevents which detected problem) and a performance comparison table with scores out of 100. Two bar charts show comparative scores and overhead costs."),

    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 80, after: 40 },
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, bottom: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, left: { style: BorderStyle.SINGLE, size: 4, color: MGRAY }, right: { style: BorderStyle.SINGLE, size: 4, color: MGRAY } },
      shading: { fill: LGRAY, type: ShadingType.CLEAR },
      children: [new TextRun({ text: "[Screenshot: Phase 4 — Technique comparison table with scores; Mutex Lock ranked first with score 95/100]", size: 20, font: "Calibri", color: DGRAY, italics: true })],
    }),
    body("Figure 6.5 — Phase 4 technique comparison. Mutex Lock scores highest due to blocking wait (no CPU burn), strict mutual exclusion, and zero deadlock events.", { italic: true, color: DGRAY, size: 20, align: AlignmentType.CENTER }),
  ];

  // ── SECTION 7 ────────────────────────────────────────────────────────────────
  const sec7 = [
    spacer(120),
    ...sectionBanner("7", "Challenges Faced and How They Were Resolved"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "7. Challenges Faced and How They Were Resolved", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    subHeading("7.1  Weaving CPU Schedule with Sync Events"),
    body("The most conceptually difficult challenge was building the integrated timeline. The CPU scheduler produces a flat Gantt chart. The sync simulator produces a separate list of synchronization events. The problem is that both timelines are generated independently using different process naming conventions (the scheduler uses real PIDs like 'P3', while the sync engine uses generic names like 'P0', 'P1')."),
    body("The solution required two steps: first, remapping the generic sync process IDs to real PIDs using the execution order from the Gantt chart; then weaving the two streams by assigning sync steps to the CPU slice of the matching process. The _pull_sync_steps_for_cpu_slice method checks whether a process appears in the step's processes, critical_section, or waiting_queue to determine assignment. Getting this right took several iterations because edge cases — like sync steps involving multiple processes, or sync steps that span multiple CPU slices — required careful handling."),

    subHeading("7.2  Deep Copy Requirement"),
    body("During early development, the simulation produced incorrect step replays: every step would show the final state of the simulation rather than its state at the time it was recorded. This was because the algorithm methods mutate live Python dictionaries and lists, and the step snapshots were holding references to those live objects rather than copies."),
    body("The fix was adding deepcopy() for every mutable field in _step(). The important thing to understand is that this is not defensive programming — it is a functional requirement. Without it, the educational purpose of the step-by-step playback is completely broken. A student stepping through Peterson's algorithm would always see the same final state regardless of which step they jumped to."),

    subHeading("7.3  Canvas Height Synchronization"),
    body("The Phase 3 layout has two columns: the canvas on the left and a side panel on the right. The side panel's height is driven by its content (process state chips, resource bar, waiting queue, step explanation, CS flow diagram). The canvas needed to match this height so the layout would look balanced."),
    body("The initial approach of using CSS height: 100% on the canvas failed because setting the canvas.height attribute in JavaScript overrides CSS height behavior. The eventual solution was a ResizeObserver watching the side panel and the canvas wrapper — whenever the side panel grew after simulation data was loaded, the observer would fire _resize(), which then measured the wrapper's clientHeight and set the canvas buffer to match."),

    subHeading("7.4  Waiting Queue Visibility"),
    body("An early version had the waiting queue section not visible at all, which initially seemed like a data problem. After investigating the backend, it was confirmed that the waiting_queue field was correctly populated in the step snapshots. The actual issue was purely in the CSS: the .sync-side-panel element had a max-height of 260px (matching the old fixed canvas height), which clipped all content below the first two sections. Removing the max-height constraint exposed all five sections of the side panel."),

    subHeading("7.5  Maintaining Educational Flow"),
    body("A non-technical challenge was structuring the four phases so that each one motivates the next. The problem detection in Phase 2 had to be clearly connected to the scheduling algorithm chosen in Phase 1 — if a student chose FCFS and saw 'no race conditions detected,' they needed to understand that was because FCFS is non-preemptive and avoids interleaving, not because the system is safe by default. We added contextual messages throughout Phase 2 that explicitly reference the Phase 1 algorithm by name and explain why it did or did not produce problems."),

    subHeading("7.6  Browser Rendering of Canvas Text"),
    body("Custom fonts loaded via Google Fonts (Orbitron, JetBrains Mono, Outfit) were not reliably available inside the canvas drawing context on first render. The first call to drawCanvas after page load would sometimes use a fallback font, producing inconsistent text sizing. The fix was to defer the initial canvas draw until after a short font-loading delay and to repeat the draw on the first user interaction, which guarantees the fonts are loaded by then."),
  ];

  // ── SECTION 8 ────────────────────────────────────────────────────────────────
  const sec8 = [
    spacer(120),
    ...sectionBanner("8", "Conclusion and Observations"),

    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: "8. Conclusion and Observations", bold: true, size: 40, font: "Calibri", color: NAVY })],
      spacing: { before: 0, after: 100 },
    }),

    body("Building this simulator gave us a much deeper understanding of operating system concepts than we would have gotten from reading alone. Several things became genuinely clearer during implementation that had been opaque from textbook descriptions."),

    subHeading("8.1  Key Observations"),

    body("On scheduling and synchronization interaction:"),
    bullet("FCFS and SJF are non-preemptive, so processes run contiguously without interruption. This means there is minimal interleaving of execution windows, which directly means fewer race conditions. Before building the diagnostic engine, we understood this as a theoretical statement; after seeing the Phase 2 output change based on the Phase 1 algorithm choice, it became concrete."),
    bullet("Round Robin with a small quantum produces the most interleaving and therefore the most synchronization problems. The quantum size is directly related to the number of context switches, which is directly related to the chance of two processes being mid-operation on the same shared variable simultaneously."),
    bullet("Priority scheduling can cause starvation: a low-priority process with a long burst time can wait indefinitely if higher-priority processes keep arriving. The diagnostic engine detects this by computing the deviation of each process's waiting time from the average."),

    body("On synchronization mechanisms:"),
    bullet("Peterson's and Dekker's algorithms are beautiful in their cleverness but genuinely impractical for modern systems. Busy-waiting burns CPU cycles and neither scales beyond two processes. They matter for understanding the theoretical foundations, not for actual deployment."),
    bullet("The difference between a mutex and a binary semaphore is subtle but important: a mutex has ownership (only the acquirer can release it), a semaphore does not. This means misusing a semaphore — having a different process signal it — can break mutual exclusion in ways that are hard to debug. Building both implementations made this distinction very clear."),
    bullet("Counting semaphores are the most general tool. By initializing the count to N, you can allow exactly N concurrent accessors while blocking the (N+1)th. The producer-consumer solution with three semaphores (mutex, empty, full) is a perfect example of how multiple primitives compose to solve a complex problem."),
    bullet("The monitor construct is the cleanest high-level abstraction. By hiding the locking inside the monitor definition, you eliminate the possibility of forgetting to acquire the lock before accessing shared data — a very common programming error with raw mutexes."),

    subHeading("8.2  Performance Comparison Summary"),
    spacer(40),
    dataTable(
      ["Technique", "Mutual Exclusion", "Deadlock Safe", "Busy Wait", "Score /100"],
      [
        ["Mutex Lock",           "Yes", "Yes", "No",  "95"],
        ["Binary Semaphore",     "Yes", "Yes", "No",  "90"],
        ["Counting Semaphore",   "Yes", "Yes", "No",  "88"],
        ["Monitor",              "Yes", "Yes", "No",  "92"],
        ["Producer-Consumer",    "Yes", "Yes", "No",  "87"],
        ["Readers-Writers",      "Yes", "Yes", "No",  "85"],
        ["Peterson's Solution",  "Yes", "Yes", "Yes", "78"],
        ["Dekker's Algorithm",   "Yes", "Yes", "Yes", "72"],
        ["Race Condition Demo",  "No",  "N/A", "N/A", "20"],
        ["Deadlock Demo",        "No",  "No",  "N/A", "10"],
      ]
    ),
    spacer(80),
    body("Table 8.1 — Summary comparison of synchronization techniques. Scores are computed by the analysis engine from actual simulation metrics, not hardcoded values."),

    spacer(80),
    subHeading("8.3  Project Outcome"),
    body("The final simulator successfully demonstrates all ten synchronization algorithms and five scheduling policies in a connected, interactive format. A student can run through the complete pipeline — from setting up processes, to seeing scheduling decisions, to watching race conditions emerge, to applying a mutex and watching them disappear — in a single session. The step-by-step playback makes every state transition traceable."),
    body("From a software engineering standpoint, the project reinforced several good practices: using deep copies for simulation correctness, designing stateless engine objects for safe request reuse, using a dispatch table instead of if-else chains for algorithm selection, and building a clean REST API that separates simulation logic from presentation."),
    body("If we were to extend this project further, the most valuable addition would be a multi-threaded or truly concurrent simulation mode, where multiple processes execute simultaneously on a real thread pool rather than being serialized in a discrete-event simulation. That would allow demonstrating the non-determinism of race conditions in a way that even a step-by-step simulation cannot fully capture — where the same code produces a different wrong answer every time you run it."),

    spacer(120),
    hr(BLUE),
    body("End of Report", { align: AlignmentType.CENTER, color: DGRAY, italic: true }),
  ];

  // ── ASSEMBLE DOCUMENT ────────────────────────────────────────────────────────
  const allChildren = [
    ...cover,
    ...toc,
    ...sec1,
    ...sec2,
    ...sec3,
    ...sec4,
    ...sec5,
    ...sec6,
    ...sec7,
    ...sec8,
  ];

  return new Document({
    numbering: NUMBERING,
    styles: {
      default: {
        document: { run: { font: "Calibri", size: 24, color: BLACK } },
      },
      paragraphStyles: [
        {
          id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 40, bold: true, font: "Calibri", color: NAVY },
          paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 0 },
        },
        {
          id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 32, bold: true, font: "Calibri", color: BLUE },
          paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 },
        },
        {
          id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 28, bold: true, font: "Calibri", color: CYAN },
          paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 2 },
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            size:   { width: PAGE_W, height: PAGE_H },
            margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
          },
        },
        headers: {
          default: new Header({
            children: [
              new Paragraph({
                border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 1 } },
                spacing: { before: 0, after: 100 },
                children: [
                  new TextRun({ text: "Process Synchronization Simulator  —  OS Project Report", size: 18, font: "Calibri", color: DGRAY }),
                  new TextRun({ text: "\t", size: 18 }),
                  new TextRun({ text: "Dept. of Computer Science | Spring 2026", size: 18, font: "Calibri", color: DGRAY }),
                ],
                tabStops: [{ type: "right", position: 8506 }],
              }),
            ],
          }),
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                border: { top: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 1 } },
                spacing: { before: 100, after: 0 },
                children: [
                  new TextRun({ text: "23FA-040-SE  |  24SP-032-SE", size: 18, font: "Calibri", color: DGRAY }),
                  new TextRun({ text: "\tPage ", size: 18, font: "Calibri", color: DGRAY }),
                  new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Calibri", color: BLUE }),
                  new TextRun({ text: " of ", size: 18, font: "Calibri", color: DGRAY }),
                  new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, font: "Calibri", color: BLUE }),
                ],
                tabStops: [{ type: "right", position: 8506 }],
              }),
            ],
          }),
        },
        children: allChildren,
      },
    ],
  });
}

// ─────────────────────────────────────────────
// GENERATE
// ─────────────────────────────────────────────
const doc = buildDoc();
Packer.toBuffer(doc).then(buf => {
  const out = "OS_Project_Report.docx";
  fs.writeFileSync(out, buf);
  console.log(`Report generated: ${out}  (${(buf.length / 1024).toFixed(1)} KB)`);
}).catch(err => {
  console.error("Failed:", err.message);
  process.exit(1);
});
