================================================================
  PROCESS SYNCHRONIZATION SIMULATOR
  Operating System Lab Project — Spring 2026
  Department of Computer Science

  Developed by:
    Syed Hassan Bukhari   (23FA-040-SE)
    Huzaifa Ali Khan      (24SP-032-SE)
================================================================


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO RUN  (3 steps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Extract this ZIP file anywhere on your computer
     (Desktop, USB drive, Documents — anywhere is fine)

  2. Open the extracted folder  "ProcessSyncSimulator"

  3. Double-click  Start.bat

  That's it. The browser will open automatically.

  FIRST RUN NOTE:
    The first time you run Start.bat it will download and install
    the required packages (~1-2 minutes, needs internet once).
    Every run after that opens in about 3 seconds, no internet needed.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SYSTEM REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Operating System : Windows 10 or Windows 11  (64-bit)
  Internet         : Required for first run only (downloads Python
                     and packages automatically if not installed)
  Browser          : Any modern browser (Chrome, Edge, Firefox)
  Python           : Installed automatically if not found


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SOFTWARE DEPENDENCIES  (installed automatically)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Language    : Python 3.11
  Framework   : Flask 3.x  (web server and REST API)
  Utilities   : python-dotenv  (environment configuration)

  All packages are listed in requirements.txt and are installed
  automatically on first run into an isolated environment.
  Nothing is installed into your system Python.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO COMPILE / BUILD FROM SOURCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  If you have Python already installed and prefer to run manually:

  1. Open Command Prompt or PowerShell
  2. Navigate to this folder:
       cd path\to\ProcessSyncSimulator
  3. Install dependencies:
       pip install -r requirements.txt
  4. Run the application:
       python app.py
  5. Open your browser and go to:
       http://127.0.0.1:5000

  Source code is also available on GitHub:
    https://github.com/hasanwebpro/process-sync-simulator


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  USAGE INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  The simulator has 4 phases. Work through them in order:

  ── PHASE 1 : CPU SCHEDULING ────────────────────────────────
    1. Add processes using the form on the left
       (set PID, Arrival Time, Burst Time, Priority)
    2. Select one or more scheduling algorithms:
         FCFS, SJF, SRTF, Round Robin, Priority
    3. Set the time quantum (for Round Robin)
    4. Click  "Run Scheduling"
    5. View the Gantt chart and metrics table
       (CT, TAT, Waiting Time, Response Time per process)
    6. Click  "Proceed to Phase 2"

  ── PHASE 2 : PROBLEM DETECTION ─────────────────────────────
    The simulator replays your Phase 1 schedule without any
    synchronization and detects:
      • Race Conditions
      • Critical Section Violations
      • Deadlock potential
      • Starvation
    No input needed — results appear automatically.
    Click  "Proceed to Phase 3"

  ── PHASE 3 : SYNCHRONIZATION ───────────────────────────────
    1. Select a synchronization algorithm from the dropdown:
         Peterson's Solution, Dekker's Algorithm,
         Mutex Lock, Binary Semaphore, Counting Semaphore,
         Producer-Consumer, Readers-Writers, Monitor,
         Race Condition Demo, Deadlock Demo
    2. Adjust iterations, buffer size, semaphore slots
    3. Click  "Simulate"
    4. Use the playback controls:
         ▶  Play       — auto-play all steps
         ⏸  Pause      — pause playback
         +1 Step       — advance one step at a time
         ⏮  Rewind     — go back to the start
    5. Watch the canvas:
         Green glow = process inside the critical section
         Amber chips = processes waiting to enter
    6. Click any step in the timeline to jump to it

  ── PHASE 4 : ANALYSIS ──────────────────────────────────────
    Click  "Compare All Techniques"
    The simulator runs all algorithms on your workload and:
      • Scores each technique (0-100)
      • Shows which problems each one prevents
      • Ranks them by performance


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TO STOP THE SIMULATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Close the black command window that opened with Start.bat
  OR press Ctrl+C inside that window.
  The browser tab can be closed separately.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Browser does not open automatically?
    → Open your browser manually and go to: http://127.0.0.1:5000

  "Download failed" error on first run?
    → Check your internet connection and run Start.bat again.
    → The download only happens once.

  "Package installation failed"?
    → Check internet connection.
    → Delete the file  _runtime\.deps_ok  then run Start.bat again.

  Port 5000 already in use?
    → Close any other Flask apps running on port 5000,
      then run Start.bat again.

  Antivirus blocks Start.bat?
    → Right-click Start.bat → Properties → Unblock → OK
      Then run it again.

  Still not working?
    → Contact: hassanbk2003@gmail.com


================================================================
  PROJECT INFORMATION
================================================================

  Title     : Process Synchronization Simulator
  Course    : Operating System
  Batch     : Software Engineering 2024 (Spring)
  Section   : A
  Semester  : Spring 2026

  Algorithms implemented:
    Scheduling   : FCFS, SJF, SRTF, Round Robin, Priority
    Sync         : Peterson, Dekker, Mutex, Binary Semaphore,
                   Counting Semaphore, Producer-Consumer,
                   Readers-Writers, Monitor, Race Condition,
                   Deadlock Demo

  GitHub : https://github.com/hasanwebpro/process-sync-simulator

================================================================
