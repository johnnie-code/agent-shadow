# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-21 - CLI Input Validation and Key Masking UX
**Learning:** When users edit critical configuration variables in an interactive CLI (like default AI providers or numerical limits), missing validation can lead to malformed config files that crash subsequent application boots. In addition, using non-standard prompting parameters (like password=True in Typer) can cause silent test runner crashes; using the standard hide_input=True ensures robust input masking and universal framework compatibility.
**Action:** Always wrap interactive prompts in strict type-and-value validation loops with helpful error explanations, and mask sensitive credentials with standard, compliant prompt attributes.

## 2026-10-13 - Rich TUI Table Visual Contrast and Layout Stability
**Learning:** In terminal dashboard layouts using Rich tables within multi-column splits, unbounded cell content can wrap unpredictably and deform adjacent panels on narrow terminal windows. Furthermore, default unstyled headers have poor contrast in certain terminal color schemes, and blank cells in empty states look like rendering bugs or missing data. Setting explicit header and border styles, enabling `overflow="ellipsis"` on text columns, and filling empty states with structured dim placeholders across all columns ensures visual hierarchy, legibility, and layout stability.
**Action:** When designing Rich tables for TUI dashboards, specify distinct `header_style` and `border_style`, enable `overflow="ellipsis"` on variable-width columns, and provide structured placeholder text with `[dim]` styling for empty table rows.
