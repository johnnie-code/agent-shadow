PROJECT SHADOW

PROJECT SHADOW is a production-grade, autonomous AI Agent Operating System designed to run entirely on Android through Termux.

Rather than functioning as a traditional chatbot, Shadow acts as a persistent, goal-driven digital chief of staff. It continuously understands the user's long-term mission, monitors projects, discovers real-world opportunities, generates execution plans, and safely performs autonomous work while keeping the user in control of sensitive actions.

Shadow is designed around a simple philosophy:

«An AI should not wait to be asked. It should understand your mission, identify what moves it forward, and proactively help achieve it.»

---

Core Capabilities

Mission Intelligence

Shadow continuously monitors "mission.md", which defines the user's identity, long-term goals, values, projects, interests, habits, and constraints.

Instead of treating these as static notes, Shadow converts them into structured knowledge that drives every planning and execution decision.

---

Autonomous Goal Engine

Shadow transforms high-level ambitions into executable roadmaps.

For every goal it can:

- Generate milestones
- Break milestones into tasks
- Track progress
- Discover blockers
- Update priorities
- Adapt plans as circumstances change

---

Opportunity Discovery

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

---

Multi-Agent Operating System

Shadow consists of specialized AI agents working together through an event-driven architecture.

Current agents include:

- Planner
- Research
- Coding
- Review
- Testing
- Documentation
- Deployment
- Learning
- Opportunity
- Reflection

Each agent has its own responsibilities, permissions, tools, and memory while collaborating through a shared execution framework.

---

Memory System

Shadow maintains persistent long-term memory using SQLite with WAL mode.

Memory includes:

- Goals
- Projects
- Conversations
- Reflections
- Preferences
- Research
- Lessons learned
- Decisions
- Execution history

The system is designed for future semantic memory expansion without changing the underlying architecture.

---

Android Automation

Running entirely inside Termux, Shadow integrates with Android using "termux-api".

Supported capabilities include:

- Notifications
- Clipboard
- Camera
- GPS
- Wi-Fi
- Bluetooth
- Application launching
- File management
- Battery monitoring
- Terminal execution

All actions are governed by a permission-based safety model.

---

Safety Model

Every action belongs to one of three execution levels.

Level 0
Safe, read-only operations executed automatically.

Level 1
Low-risk local actions that may be executed autonomously.

Level 2
High-impact actions requiring explicit user approval, such as deployments, remote changes, financial operations, or destructive commands.

---

Event-Driven Architecture

Shadow reacts to events instead of relying solely on polling.

Examples include:

- Mission updates
- System startup
- Wi-Fi connection
- Charging state
- Git activity
- Scheduled routines
- User idle periods
- Custom events

This enables efficient background operation with minimal battery consumption.

---

Rich Terminal Experience

Shadow provides:

- Interactive CLI
- Live Rich dashboard
- Background daemon
- FastAPI server
- Structured logging
- Real-time status monitoring
- Agent activity visualization

---

Technology Stack

- Python 3.12+
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

Long-Term Vision

Shadow is being developed as a lightweight AI operating system that evolves alongside its user.

Rather than simply responding to prompts, it continuously learns, plans, researches, reflects, and executes work that advances the user's long-term mission.

The ultimate objective is to create an AI companion that functions as a proactive second brain—one capable of understanding goals, adapting strategies, coordinating specialized agents, and helping users accomplish ambitious, multi-year objectives while remaining efficient enough to run directly on an Android phone.

---

## Production Installation (Native System-Wide CLI)

Shadow behaves like a real native utility rather than a standard Python project. After a simple installation, you can execute the `shadow` command globally from any directory without manually activating virtual environments or invoking Python.

### Quick Install

Install Shadow with a single command inside Termux or any Linux terminal:

```bash
./install.sh
```

The installer will:
1. Automatically update package indexes and install required packages (`python`, `git`, `sqlite`) if running in Termux.
2. Build an isolated virtual environment at `~/.shadow/venv/` and install Shadow along with all its Python dependencies.
3. Establish a production-grade file hierarchy:
   - `~/.shadow/config/` (System preferences and configuration)
   - `~/.shadow/backups/` (Auto-backups for database & mission files)
   - `~/.shadow/logs/` (Daemon and structured decision logs)
   - `~/.shadow/mission.md` (Active, user-managed mission context file)
   - `~/.shadow/shadow.db` (High-performance SQLite database in WAL mode)
4. Expose a fast, global launcher at `$PREFIX/bin/shadow` (or fallbacks like `~/.local/bin/shadow`).
5. Configure intelligent tab completion for your shell (`bash`, `zsh`, `fish`).
6. Initialize the SQLite database tables and perform a final validation.

---

## Command Line Interface (CLI)

Shadow is managed entirely via the `shadow` CLI command:

### Core Commands
* `shadow status`: Query active daemon status and database statistics.
* `shadow mission`: Parse and synchronize your `~/.shadow/mission.md` goals to the structured database.
* `shadow goals`: List your active goals and projects.
* `shadow tasks`: Display prioritized, queued action items.
* `shadow execute <task_id>`: Safely trigger execution of a specific task.
* `shadow approvals`: Review and approve/reject Safety Level 2 hold actions.
* `shadow opportunities`: Trigger a real-time web scan to discover new opportunities.
* `shadow memory`: View high-levelPersistent Memory statistics.
* `shadow search <query>`: Search your sqlite memories and learning insights index.
* `shadow reflect`: Run evening reflection audits.
* `shadow tui`: Launch the real-time interactive terminal dashboard.

### Daemon Service Management
The FastAPI/Uvicorn background server can run as an independent daemon that survives terminal sessions:
* `shadow daemon start` (or `shadow start`): Detach and start the API background daemon on port 8000.
* `shadow daemon stop` (or `shadow stop`): Gracefully stop the running background daemon.
* `shadow daemon restart`: Restart the background daemon process.
* `shadow daemon status`: Verify whether the daemon is online, healthy, and responsive.

### Administrative Tools
* `shadow doctor`: Run complete self-repair diagnostics (automatically identifies and heals broken virtual environments, missing package dependencies, corrupted databases, missing configurations, missing mission files, or launcher execution permissions).
* `shadow update`: Securely update to the latest release (creates automatic time-stamped backups of your database/configurations, pulls updates from Git, upgrades venv packages safely, and verifies the update—performing automatic rolling back to your previous stable state if verification fails).
* `shadow uninstall`: Safely uninstall Shadow, offering options to preserve or delete your databases and configuration directories.
