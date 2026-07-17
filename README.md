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

## Termux Installation Guide

PROJECT SHADOW is fully optimized to run natively in a clean Termux environment on Android. Below are the step-by-step instructions to install, verify, and run the platform.

### Prerequisites

To ensure compatibility with Python 3.12 and Python 3.13 on Android, PROJECT SHADOW leverages a precompiled wheel index for native extensions (such as `pydantic-core`), eliminating the need for a complex local Rust compiler setup.

### Automated One-Command Installation

You can run the production-grade, idempotent automated bootstrap installer script to set up everything automatically:

```bash
pkg install wget -y
wget -qO- https://raw.githubusercontent.com/johnnie-code/agent-shadow/main/install.sh | bash
```

Alternatively, if you have already cloned the repository:

```bash
chmod +x install.sh
./install.sh
```

The bootstrap installer script will automatically:
1. Update Termux packages
2. Install required system dependencies (`git`, `python`, `termux-api`, `sqlite`, `ndk-sysroot`, `clang`, `make`)
3. Set up the Python virtual environment (`.venv`)
4. Detect Termux and install pinned dependencies using the precompiled Android wheel index for `pydantic-core`
5. Initialize the SQLite database with WAL mode
6. Synchronize goals from `mission.md`
7. Create a global command wrapper so `shadow` is accessible from anywhere in your Termux terminal.

---

### Manual/Developer Installation (Editable Mode)

For development or manual installation:

1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/johnnie-code/agent-shadow.git
   cd agent-shadow
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies and package in editable mode using the precompiled wheel index:
   ```bash
   pip install --upgrade pip
   pip install --extra-index-url https://eutalix.github.io/android-pydantic-core/ -e .
   ```

   *Or using `uv` if installed:*
   ```bash
   uv pip install --extra-index-url https://eutalix.github.io/android-pydantic-core/ -e .
   ```

---

### Verifying the Installation

After installation, verify that the entrypoints and services launch correctly:

#### 1. CLI Commands Verification
Ensure the console entrypoint and main module execute successfully:
- Global launcher command:
  ```bash
  shadow --help
  ```
- Direct module command:
  ```bash
  python -m shadow.cli.main --help
  ```

#### 2. Starting FastAPI Server (Daemon)
To boot the FastAPI server daemon in the background or foreground:
- Foreground:
  ```bash
  shadow start --port 8000
  ```
- Background:
  ```bash
  shadow start --port 8000 --background
  ```
- Query system status:
  ```bash
  shadow status
  ```
- Stopping background daemon:
  ```bash
  shadow stop
  ```

#### 3. Launching the Rich TUI Dashboard
The interactive terminal dashboard can be launched from any terminal tab:
```bash
shadow tui
```

#### 4. Running the Pytest Suite
Run the full test suite from the repository root:
```bash
python -m pytest tests/
```

---

### Troubleshooting & Compatibility Notes

#### Python 3.13 Support on Termux
Termux default Python package is Python 3.13. Standard `pydantic-core` compiles from source, which fails on Termux without a heavy Rust toolchain and appropriate compiler flags. We support Python 3.13 natively by using `--extra-index-url https://eutalix.github.io/android-pydantic-core/` which supplies prebuilt Android wheels (`cp313-android`) of `pydantic-core`.

#### Typer and Click Warnings
To prevent `'make_metavar' signature compatibility errors` when using older versions of typer with newer click, the `click` dependency is strictly pinned to `8.1.8`. Do not manually upgrade click to a newer version.

#### Termux:API Integration
If the battery or notification integrations fail, ensure you have:
1. Installed the `Termux:API` app from F-Droid.
2. Installed the corresponding package inside Termux:
   ```bash
   pkg install termux-api
   ```