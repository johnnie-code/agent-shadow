# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-21 - CLI Input Validation and Key Masking UX
**Learning:** When users edit critical configuration variables in an interactive CLI (like default AI providers or numerical limits), missing validation can lead to malformed config files that crash subsequent application boots. In addition, using non-standard prompting parameters (like password=True in Typer) can cause silent test runner crashes; using the standard hide_input=True ensures robust input masking and universal framework compatibility.
**Action:** Always wrap interactive prompts in strict type-and-value validation loops with helpful error explanations, and mask sensitive credentials with standard, compliant prompt attributes.

## 2026-10-14 - Rich TUI Dashboard Table Styling and Empty State UX
**Learning:** Terminal dashboard tables without explicit header/border styling and column truncation overflow settings look unpolished and can wrap awkwardly across narrow terminal displays. Furthermore, empty table states rendered with plain string messages across a single cell look unaligned; styling empty rows with muted tags `[dim]...[/dim]` and dash placeholders (`—`) across all columns preserves table alignment and hierarchy.
**Action:** Always configure Rich `Table` objects with high-contrast header/border styles, set `overflow="ellipsis"` on columns, and structure empty state rows with muted placeholder tags across all table columns.
