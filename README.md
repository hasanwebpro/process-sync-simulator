# Process Synchronization Simulator

Educational full-stack simulator for **Operating Systems** courses — process synchronization, CPU scheduling, and intelligent comparative analysis.

## Features

### Module 1: Process Synchronization (Main)
- Peterson's Solution, Dekker's Algorithm
- Mutex locks, Binary & Counting semaphores
- Producer–Consumer, Readers–Writers, Monitor
- Race condition demo (unsafe vs mutex-corrected)
- Deadlock demonstration
- Real-time states: Ready, Running, Waiting, Blocked, Terminated
- Step-by-step, auto-play, pause, adjustable speed
- Canvas visualization of critical section and locks

### Module 2: CPU Scheduling (Supporting)
- FCFS, SJF, SRTF, Round Robin, Priority
- Gantt charts, performance metrics (TAT, WT, RT, throughput)
- Compare-all scheduling algorithms

### Module 3: Analysis & Intelligence
- Rule-based algorithm comparison and rankings
- Starvation/deadlock detection in reports
- Optional OpenAI explanations (`OPENAI_API_KEY` in `.env`)

## Tech Stack

| Layer | Stack |
|-------|--------|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Charts | Chart.js |
| Visualization | HTML5 Canvas |

## Quick Start

```bash
cd process-sync-simulator
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Optional AI Explanations

Create `.env` in the project root:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

Without an API key, the system uses the built-in rule-based analysis engine.

## Project Structure

```
process-sync-simulator/
├── app.py                 # Flask routes
├── engine/
│   ├── sync_engine.py     # Synchronization simulations
│   ├── scheduler.py       # CPU scheduling algorithms
│   └── analyzer.py        # Analysis & AI module
├── templates/index.html
├── static/css/style.css
└── static/js/             # Dashboard & visualizations
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sync/algorithms` | List sync algorithms |
| POST | `/api/sync/run` | Run one sync simulation |
| GET | `/api/scheduler/algorithms` | List scheduling algorithms |
| POST | `/api/scheduler/run` | Run one scheduler |
| POST | `/api/pipeline/phase1` | Run CPU scheduling (multi-algorithm) |
| POST | `/api/pipeline/phase2` | Run synchronization (multi-algorithm, requires phase1 result) |
| POST | `/api/pipeline/phase3` | Generate analysis report (requires phase1 + phase2 results) |
| POST | `/api/pipeline/full` | Run all three phases in one request |

## Course Usage

1. **Synchronization tab** — Pick an algorithm, configure processes, run and step through execution.
2. **CPU Scheduling tab** — Enter process AT/BT/priority, run FCFS/RR/etc., view Gantt chart and metrics.
3. **Analysis tab** — Compare algorithms and read recommendations for your report.

---

*OS Course Project — Process Synchronization Simulator*
