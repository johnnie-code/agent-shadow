# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-21 - CLI Input Validation and Key Masking UX
**Learning:** When users edit critical configuration variables in an interactive CLI (like default AI providers or numerical limits), missing validation can lead to malformed config files that crash subsequent application boots. In addition, using non-standard prompting parameters (like password=True in Typer) can cause silent test runner crashes; using the standard hide_input=True ensures robust input masking and universal framework compatibility.
**Action:** Always wrap interactive prompts in strict type-and-value validation loops with helpful error explanations, and mask sensitive credentials with standard, compliant prompt attributes.

## 2026-08-08 - Interactive CLI Configuration Status Indicators and Key Retention UX
**Learning:** For interactive CLI settings, displaying real-time status indicators (e.g., whether API keys are missing or set) on the top-level selection screen allows users to immediately grasp their configuration state without diving into nested submenus. Furthermore, appending `(already set, press Enter to keep current)` to prompts ensures that users can confidently skip fields without risking accidental deletion or overwrite of configured credentials.
**Action:** Always provide visual state hints on root menus of CLI interactive tools, and design modification prompts with safe, clear retention instructions.
