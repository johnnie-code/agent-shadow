# GHOST SANDBOX OS COMPUTER — PRODUCTION ARCHITECTURE

This document outlines the design, security, and usage model of Ghost's hardened, private isolated **Sandbox Computer**.

---

## 1. Design & Workspace Isolation

The sandbox environment provides a dedicated virtual workspace separate from the host device. Multiple concurrent sandboxes are supported under individual directories.

### Workspace Directory Layout

Every sandbox is located at `~/.shadow/sandboxes/<sandbox_id>/` and contains the following structural segments:

```
~/.shadow/sandboxes/<sandbox_id>/
  ├── workspace/           # The active project code & real Git state (never shared)
  ├── snapshots/           # Directory-level checkpoints for rollback operations
  ├── logs/                # Real-time stdout, stderr, execution timers, and background job history
  ├── artifacts/           # Collected outputs: test coverage, APK, lint, screenshots, etc.
  ├── cache/               # Dynamic dependency artifacts
  ├── terminal_history.txt # Logged terminal inputs with secrets scrubbed out
  ├── meta.json            # Dynamic resource usages, branch states, and installed software indices
  └── ai_notebook.json     # Ghost's persistent progress tracking
```

---

## 2. Execution & Process Lifecycle

### Hardened Terminal Execution
All sandbox commands are run using asynchronous subprocess interfaces pinned to the relative `workspace/` path. Standard inputs, outputs, errors, durations, and exit statuses are written securely.

### Background Job Manager ( survives CLI Exits )
Long-running jobs are managed by an asynchronous background daemon that keeps processes alive after the CLI or interactive TUI exits:
- `jobs`: lists all active background jobs
- `jobs-start`: spawns detached background process groups with logged output
- `logs`: fetches background execution output streams
- `cancel`: terminates runaway process groups
- `resume`: triggers paused process threads

---

## 3. Safe File Synchronization

Modifications are never merged to the host silently. The `FileSyncManager` uses a multi-stage validation framework:

1. **Conflict Detection**: Checks if host files have changed since the sandbox was initialized.
2. **Preview Changes**: Generates a complete preview of modifications, insertions, or deletions with standard unified file diffs.
3. **Backup Generation**: Automatically creates rollback snapshots of target host file paths prior to merging.
4. **Merge Sync**: Overwrites host files only upon manual CLI/policy approval.
5. **Sync Rollback**: Completely reverts sync copies if compilation errors or unexpected runtime regressions occur.

---

## 4. Headless Browser Automation & Visual Audits

Subsystem utilizes `playwright` chromium capabilities for rendering pages, filling form fields, clicking select targets, checking API requests, and taking screenshots.

If binaries or node libraries are absent, the system falls back dynamically to a high-fidelity DOM layout simulation to verify visual properties and test structures cleanly on standard platforms (e.g. mobile Termux).

---

## 5. Specialized Android/Gradle Operations

- **Manifest Validation**: Inspects `AndroidManifest.xml` for package namespace conventions, API permissions, backup configurations, and activity structures.
- **Compose Audits**: Evaluates `@Composable` sizing values to detect hardcoded constraints and visual responsive overlap layout failures.
- **Real Compilation**: Executes local gradlew wrapper instructions (`assembleDebug`, `connectedCheck`, `lint`) with adaptive output routing.

---

## 6. Security Model & Bounds Isolation

- **Traversal Prevention**: Strict absolute path boundaries prevent sandbox execution from altering, reading, or destroying elements outside of `~/.shadow/sandboxes/`.
- **Credential Scrubbing**: Regex patterns scrub API keys, tokens, and passwords from logs, metrics, history records, and notebooks.
- **Isolated Environment Variables**: Injects runtime parameters (`SANDBOX_ID`, `CACHE_DIR`) scoped uniquely to active execution.

---

## 7. Extensible Plugin System

Provides registration pathways to scale sandbox features without modification:
```python
from shadow.core.plugins import plugin_registry

# Register custom language compiler handlers
plugin_registry.register_runtime("rust", cargo_run_handler)

# Register GPU AI worker nodes
plugin_registry.register_gpu_executor("cuda_cluster", gpu_executor)
```
