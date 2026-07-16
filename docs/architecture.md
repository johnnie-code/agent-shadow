# Project Shadow: System Architecture

Shadow is a lightweight, autonomous, goal-driven agent operating system designed to run entirely on Android via Termux.

## System Topology Overview

```
                      +-------------------+
                      |    mission.md     |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   Goals Engine    |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  Scheduler & Event|
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   Opportunity     |
                      |     Scanner       |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |   Task Generator  |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  Priority Engine  |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  Execution Engine |
                      +-------------------+
                                |
                                v
                      +-------------------+
                      |  Memory (SQLite)  |
                      +-------------------+
```

## Subsystem Details

### 1. Goals Engine & Analyzer
- Automatically monitors and parses the `mission.md` markdown file sections (Identity, Long-Term Goals, Current Projects, Core Values, Constraints, Preferences).
- Synchronizes changes incrementally into structural Goals inside the database.

### 2. Event System & Scheduler
- Asynchronous, non-polling EventBus (`shadow/core/events.py`) routing specific system-level and resource events.
- An Interval and Event-Driven Scheduler (`shadow/core/scheduler.py`) to trigger periodic web research, evening reflection audits, and repository scans.

### 3. Tool System & Android Automation
- Rich, schema-validated extensible Tools with strict Safety Levels:
  - **Level 0 (Read-only)**: Wi-Fi scan, Bluetooth scan, GPS locate, Web search, File read.
  - **Level 1 (Local writes)**: Local file write, Clipboard write, Notification send.
  - **Level 2 (Requires approval)**: Camera capture, terminal execution, App Launcher, Git push.
- Automatic tool registry discovery dynamically detects new subclasses.

### 4. Memory System
- SQLite with WAL journal mode. Holds conversation records, preferences, projects history, lessons learned, and structured decision logs.

### 5. Multi-Agent & Skills System
- 10 Specialized Agents: Planner, Research, Coding, Review, Testing, Documentation, Deployment, Learning, Opportunity, and Reflection.
- Parameterized SkillsRegistry supporting version metadata, example guides, and custom templates.
