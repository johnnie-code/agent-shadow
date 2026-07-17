# PROJECT SHADOW

PROJECT SHADOW is a production-grade, autonomous AI Agent Operating System designed to run entirely on Android through Termux.

Rather than functioning as a traditional chatbot, Shadow acts as a persistent, goal-driven digital chief of staff. It continuously understands the user's long-term mission, monitors projects, discovers real-world opportunities, generates execution plans, and safely performs autonomous work while keeping the user in control of sensitive actions.

Shadow is designed around a simple philosophy:

«An AI should not wait to be asked. It should understand your mission, identify what moves it forward, and proactively help achieve it.»

---

## Production Installation on Termux (Android)

PROJECT SHADOW is fully optimized for a fresh, clean Termux installation. To bypass manual Rust compilation of native dependencies (such as `pydantic-core`) which can run out of memory or take up to 15 minutes, the installation leverages specialized precompiled Android wheel indexes for both **Python 3.12 and Python 3.13**.

### Quick Start (Automated Bootstrap)

We provide an automated bootstrap installer that handles all required package updates, dependencies, virtual environments, database initialization, and system verification.

To install, clone the repository and run:

```bash
# Clone the repository
git clone https://github.com/yourusername/shadow-os.git
cd shadow-os

# Make the installer executable and run it
chmod +x install.sh
./install.sh
```

### Manual Installation Step-by-Step

If you prefer to set up the environment manually, follow these instructions:

1. **Update and Install System Packages:**
   ```bash
   pkg update -y
   pkg upgrade -y
   pkg install -y python git
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip setuptools wheel
   ```

3. **Install Dependencies using Precompiled Android Wheels:**
   ```bash
   # Install pydantic-core via the precompiled wheel index for Termux to avoid compilation failures
   pip install pydantic-core --extra-index-url https://eutalix.github.io/android-pydantic-core/

   # Install Project Shadow in editable mode
   pip install -e . --extra-index-url https://eutalix.github.io/android-pydantic-core/
   ```

4. **Initialize Database:**
   ```bash
   shadow update
   ```

---

## Command Line Interface & Usage

Ensure your virtual environment is active before running commands:
```bash
source venv/bin/activate
```

### 1. Verification & Help
Verify that the CLI is launching correctly:
```bash
shadow --help
# Or alternatively
python3 -m shadow.cli.main --help
```

### 2. Managing the Background Daemon (FastAPI Server)
Start/stop the FastAPI background API daemon:
```bash
# Start the background daemon
shadow start --background

# Verify background daemon state
curl http://127.0.0.1:8000/status

# Stop the background daemon
shadow stop
```

### 3. Launching the Interactive TUI Dashboard
Launch the real-time Rich dashboard console:
```bash
python3 -m shadow.cli.tui
```

### 4. System & Tasks Control
Query status, mission, and priorities:
```bash
# Check database and logs status
shadow status

# Sync mission.md structure to local structured DB
shadow mission

# List active structured goals
shadow goals

# Prioritize and list queued action tasks
shadow tasks

# Trigger execution of a specific task
shadow execute <task_id>

# Perform evening strategic audit and reflection
shadow reflect
```

---

## Running Tests

Verify the complete test suite using pytest inside the virtual environment:
```bash
pip install pytest pytest-asyncio
python3 -m pytest tests/
```

---

## Troubleshooting on Termux

### Rust Build Failures with `pydantic-core`
If you encounter compilation errors or freezes while installing `pydantic` or `pydantic-core`, it means `pip` is attempting to build native Rust extensions from scratch.
* **Fix:** Ensure you pass `--extra-index-url https://eutalix.github.io/android-pydantic-core/` when running `pip install` or run `./install.sh` which automatically routes these installations to precompiled Termux `.whl` binaries.

### Executable Command `shadow` Not Found
If the `shadow` command is not available in your path after editable installation:
* **Fix:** Make sure you activated your virtual environment (`source venv/bin/activate`). If you are running outside a virtual environment, add Python's user bin directory to your `$PATH` (typically `export PATH="$HOME/.local/bin:$PATH"`). Alternatively, use `python3 -m shadow.cli.main` instead.

### Address Already in Use (Port 8000/8089)
If the background API server fails to bind:
* **Fix:** Use the stop command `shadow stop` to shut down any background instances, or run `fuser -k 8000/tcp` to free up the port.

---

## Core Capabilities

### Mission Intelligence
Shadow continuously monitors `mission.md`, which defines the user's identity, long-term goals, values, projects, interests, habits, and constraints. Instead of treating these as static notes, Shadow converts them into structured knowledge that drives every planning and execution decision.

### Autonomous Goal Engine
Shadow transforms high-level ambitions into executable roadmaps. For every goal, it can:
- Generate milestones
- Break milestones into tasks
- Track progress
- Discover blockers
- Update priorities
- Adapt plans as circumstances change

### Opportunity Discovery
Shadow proactively searches for opportunities aligned with the user's mission, including:
- Scholarships
- Hackathons
- Robotics competitions
- AI news
- Research papers
- Open-source projects
- Remote jobs
- Internships
- Grants
- Startup funding
- Learning resources

Every discovery is automatically analyzed, scored, and converted into actionable work.

### Multi-Agent Operating System
Shadow consists of specialized AI agents working together through an event-driven architecture.
Current agents include:
- Planner, Research, Coding, Review, Testing, Documentation, Deployment, Learning, Opportunity, and Reflection.

Each agent has its own responsibilities, permissions, tools, and memory while collaborating through a shared execution framework.

### Memory System
Shadow maintains persistent long-term memory using SQLite with WAL mode.
Memory includes:
- Goals, Projects, Conversations, Reflections, Preferences, Research, Lessons learned, Decisions, and Execution history.

The system is designed for future semantic memory expansion without changing the underlying architecture.

### Android Automation
Running entirely inside Termux, Shadow integrates with Android using `termux-api`.
Supported capabilities include:
- Notifications, Clipboard, Camera, GPS, Wi-Fi, Bluetooth, Application launching, File management, Battery monitoring, and Terminal execution.

All actions are governed by a permission-based safety model.

### Safety Model
Every action belongs to one of three execution levels.
* **Level 0:** Safe, read-only operations executed automatically.
* **Level 1:** Low-risk local actions that may be executed autonomously.
* **Level 2:** High-impact actions requiring explicit user approval (deployments, remote changes, etc.).

### Event-Driven Architecture
Shadow reacts to events instead of relying solely on polling. Examples include:
- Mission updates, System startup, Wi-Fi connection, Charging state, Git activity, Scheduled routines, and User idle periods.

This enables efficient background operation with minimal battery consumption.

### Rich Terminal Experience
Shadow provides:
- Interactive CLI
- Live Rich dashboard
- Background daemon
- FastAPI server
- Structured logging
- Real-time status monitoring
- Agent activity visualization

---

## Technology Stack

- Python 3.12+ / 3.13+
- FastAPI
- SQLite (WAL)
- AsyncIO
- Typer
- Rich
- Watchdog
- Termux API
- HTTPX
- Pydantic

---

## Long-Term Vision

Shadow is being developed as a lightweight AI operating system that evolves alongside its user. Rather than simply responding to prompts, it continuously learns, plans, researches, reflects, and executes work that advances the user's long-term mission.

The ultimate objective is to create an AI companion that functions as a proactive second brain—one capable of understanding goals, adapting strategies, coordinating specialized agents, and helping users accomplish ambitious, multi-year objectives while remaining efficient enough to run directly on an Android phone.
