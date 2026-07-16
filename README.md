# PROJECT SHADOW — Autonomous Goal-Driven Agent Operating System for Android (Termux)

PROJECT SHADOW is a production-grade, highly optimized, lightweight autonomous AI agent operating system designed to run entirely on Android mobile devices inside the Termux environment.

Shadow operates as an elite chief of staff, software engineer, researcher, and scheduler. It continuously parses your long-term life mission, discovers high-value real-world opportunities (such as scholarships, hackathons, and remote jobs), translates them into granular action tasks, and executes safe tasks automatically while holding sensitive Level 2 tasks for explicit human approval.

## Subsystem Architecture & Features

1. **Goal Analyzer & Parser**: Monitors `mission.md` dynamically. Breaks down sections (Identity, Long-Term Goals, Current Projects, Core Values, Constraints, Preferences) into structured database records.
2. **Event System & Scheduler**: Asyncio event-driven and resource-aware interval scheduler coordinating actions based on triggers (Wi-Fi connected, morning, night, system start, and file updates).
3. **Multi-Agent Engine**: Houses 10 specialized agent roles (Planner, Research, Coding, Review, Testing, Documentation, Deployment, Learning, Opportunity, and Reflection) using structured JSON protocols.
4. **Android Tool Automation Layer**: Integrated support for mobile actions using `termux-api` (Wi-Fi, Bluetooth, GPS, Application Launcher, Camera, Clipboard, and Notifications) mapped to precise safety levels.
5. **Memory System**: SQLite back-end running WAL journaling mode for optimal concurrent performance. Stores searchable history, pref configurations, and long-term daily reflections.
6. **Polished CLI & Rich TUI Dashboard**: Feature-complete terminal command manager and real-time dashboard layout displaying core status, queues, memory blocks, and decision feeds.

## Documentation References

- [System Architecture Specification](docs/architecture.md)
- [User Guide & CLI Commands List](docs/user_guide.md)

## Quick Start

1. Initialize database and parse initial mission file:
   ```bash
   python -m shadow.cli.main mission
   ```

2. Start the daemon API server in the background:
   ```bash
   python -m shadow.cli.main start --background
   ```

3. Query system status and check active goals:
   ```bash
   python -m shadow.cli.main status
   python -m shadow.cli.main goals
   ```

4. Launch the gorgeous integrated live TUI Dashboard:
   ```bash
   python -m shadow.cli.tui
   ```

## Development and Verification

The repository contains extensive unit and integration tests under `tests/`. Verify changes using pytest:
```bash
python -m pytest tests/
```
