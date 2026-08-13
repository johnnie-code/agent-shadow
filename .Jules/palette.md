# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-21 - CLI Input Validation and Key Masking UX
**Learning:** When users edit critical configuration variables in an interactive CLI (like default AI providers or numerical limits), missing validation can lead to malformed config files that crash subsequent application boots. In addition, using non-standard prompting parameters (like password=True in Typer) can cause silent test runner crashes; using the standard hide_input=True ensures robust input masking and universal framework compatibility.
**Action:** Always wrap interactive prompts in strict type-and-value validation loops with helpful error explanations, and mask sensitive credentials with standard, compliant prompt attributes.

## 2026-08-13 - Instant Configuration Reloads and Test Isolation UX
**Learning:** In interactive CLI sessions (such as nested menus), setting configuration options on disk (e.g. inside a `.env` file) without instantly updating `os.environ` causes a stale UI state because the running process continues to refer to old cached values. When writing unit tests for interactive loop prompts under standard test runners, we must also explicitly purge target variables from `os.environ` to ensure total state isolation.
**Action:** Always synchronize disk-written configurations with live `os.environ` keys during the same session, and manually isolate environment variables in test cases to prevent cross-test leakage.
