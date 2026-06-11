/** Plain-language sync explanations for students */

const SyncInsights = {
  ACTION_HELP: {
    schedule_plan: "The CPU schedule is fixed. Each process will run in order; synchronization happens inside those CPU time slices.",
    cpu_dispatch: "The scheduler placed a process on the CPU. It can now execute instructions.",
    cpu_release: "This process finished its CPU time slice. Another process may run next.",
    cpu_idle: "CPU is idle — no process is running at this moment.",
    init: "Simulation starts. Shared resources and process states are initialized.",
    request_cs: "A process wants to enter the critical section (shared resource).",
    request_lock: "A process tries to acquire the lock (mutex).",
    acquire: "Lock acquired — this process may enter the critical section safely.",
    blocked: "Process is blocked because another process holds the lock.",
    waiting: "Process is in the waiting queue for the resource.",
    enter_cs: "Process entered the critical section — only one should be inside at a time.",
    critical_section: "Inside critical section — shared variable is being updated safely.",
    release: "Lock released — waiting processes may proceed.",
    exit_cs: "Left critical section — resource is free for others.",
    P_wait: "Semaphore P() — process waits if no resource available.",
    V_signal: "Semaphore V() — signals that a resource was released.",
    block: "Blocked on semaphore until another process signals.",
    wakeup: "A blocked process was woken and can continue.",
    deadlock: "Deadlock: processes wait forever in a circle — system cannot progress.",
    hold_wait: "A process holds one resource while requesting another — the hold-and-wait condition.",
    livelock: "Livelock: processes keep reacting to each other but make no progress — active, yet stuck.",
    intent: "Both processes signal that they want the critical section at the same time.",
    conflict: "Each process sees the other's flag — a collision is detected.",
    yield: "Both processes politely back off and retry — with symmetric timing the collision repeats.",
    starvation: "Starvation: a process is bypassed indefinitely while others keep winning the resource.",
    request: "Processes request entry to the critical section.",
    busy_wait: "Busy waiting: the process spins in a loop testing the lock — every test wastes a CPU cycle.",
    resolve: "The problem is resolved — asymmetry, aging, or a blocking primitive restores progress.",
    done: "Simulation finished for this algorithm.",
    terminate: "All scheduling and synchronization steps are complete.",
  },

  PHASE_HELP: {
    scheduling: "CPU Scheduling",
    sync_during_execution: "Sync During CPU",
    complete: "Complete",
  },

  explainStep(step) {
    const action = step.action || "step";
    const base = this.ACTION_HELP[action] || step.message || "Process state updated.";
    const pid = step.active_cpu || step.scheduled_process;
    const inCs = (step.critical_section || []).join(", ") || "none";
    const wq = (step.waiting_queue || []).length
      ? step.waiting_queue.join(" → ")
      : "empty";

    let html = `<p class="explain-main">${base}</p>`;
    html += `<ul class="explain-facts">`;
    if (pid) html += `<li><strong>On CPU:</strong> ${pid}</li>`;
    if (step.phase) {
      html += `<li><strong>Phase:</strong> ${this.PHASE_HELP[step.phase] || step.phase}</li>`;
    }
    html += `<li><strong>Critical section:</strong> ${inCs}</li>`;
    html += `<li><strong>Waiting queue:</strong> ${wq}</li>`;
    if (step.cpu_interval) {
      html += `<li><strong>CPU time:</strong> t=${step.cpu_interval.start} to t=${step.cpu_interval.end}</li>`;
    }
    html += `</ul>`;
    return html;
  },

  summarizeRun(steps, algoName) {
    const syncSteps = steps.filter((s) => s.phase === "sync_during_execution");
    const csSteps = steps.filter((s) => (s.critical_section || []).length > 0);
    const blocked = steps.filter((s) =>
      ["blocked", "block", "wait", "busy_wait", "write_block"].includes(s.action)
    );
    const onCpu = steps.filter((s) => s.action === "cpu_dispatch").length;

    // Mutual exclusion: check whether any two processes were ever BOTH
    // in the critical_section at the same time (ME violation).
    // A single-process CS entry is fine; concurrent entries are the violation.
    const meViolation = steps.some(s => (s.critical_section || []).length > 1);
    // Also honour the backend's explicit mutual_exclusion flag from the summary
    // (e.g. race_condition demo explicitly sets mutual_exclusion: false).
    const backendME = steps.length > 0
      ? steps[steps.length - 1]?.shared_vars?.mutual_exclusion
      : undefined;
    const mutualExclusion = backendME !== undefined
      ? Boolean(backendME)
      : (!meViolation && csSteps.length > 0);

    return {
      algo: algoName,
      totalSteps: steps.length,
      syncSteps: syncSteps.length,
      csEntries: csSteps.length,
      blockEvents: blocked.length,
      cpuSlices: onCpu,
      mutualExclusion,
    };
  },

  renderFlowDiagram(step) {
    const el = document.getElementById("sync-flow-diagram");
    if (!el) return;

    const inCs = (step.critical_section || []).length > 0;
    const waiting = (step.waiting_queue || []).length > 0;
    const stages = [
      { label: "CPU", active: !!step.active_cpu || step.action === "cpu_dispatch" },
      { label: "Request", active: ["request_cs", "request_lock", "P_wait"].includes(step.action) },
      { label: "Wait", active: waiting || ["blocked", "block", "wait"].includes(step.action) },
      { label: "Critical Section", active: inCs },
      { label: "Release", active: ["release", "exit_cs", "V_signal"].includes(step.action) },
    ];

    el.innerHTML = `
      <div class="flow-track">
        ${stages
          .map(
            (s, i) => `
          <div class="flow-node ${s.active ? "active" : ""}">
            <div class="flow-circle">${i + 1}</div>
            <div class="flow-label">${s.label}</div>
          </div>
          ${i < stages.length - 1 ? '<div class="flow-arrow">→</div>' : ""}`
          )
          .join("")}
      </div>`;
  },
  renderExplainPanel(step) {
    const panel = document.getElementById("sync-step-explain");
    if (panel) panel.innerHTML = this.explainStep(step);
    this.renderFlowDiagram(step);
  },

  renderRunSummary(summary) {
    const el = document.getElementById("sync-run-summary");
    if (!el || !summary) return;
    // Compact inline strip — lives inside the Live Execution card, no extra card height
    el.innerHTML = `
      <div class="summary-grid">
        <div class="sum-card"><span>Algo</span><strong>${summary.algo}</strong></div>
        <div class="sum-card"><span>Steps</span><strong>${summary.totalSteps}</strong></div>
        <div class="sum-card"><span>CS entries</span><strong>${summary.csEntries}</strong></div>
        <div class="sum-card"><span>Wait events</span><strong>${summary.blockEvents}</strong></div>
        <div class="sum-card"><span>CPU slices</span><strong>${summary.cpuSlices}</strong></div>
      </div>`;
  },
};
