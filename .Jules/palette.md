# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-21 - CLI Input Validation and Key Masking UX
**Learning:** When users edit critical configuration variables in an interactive CLI (like default AI providers or numerical limits), missing validation can lead to malformed config files that crash subsequent application boots. In addition, using non-standard prompting parameters (like password=True in Typer) can cause silent test runner crashes; using the standard hide_input=True ensures robust input masking and universal framework compatibility.
**Action:** Always wrap interactive prompts in strict type-and-value validation loops with helpful error explanations, and mask sensitive credentials with standard, compliant prompt attributes.

## 2026-08-06 - Rich-powered CLI/TUI Dashboard Table Design Patterns
**Learning:** CLI/TUI dashboard tables constructed with `rich.table.Table` are prone to visual truncation or text-wrapping distortion under confined terminal window states (such as on small displays or mobile terminals like Termux). Applying consistent high-contrast colors to borders and headers, enabling explicit ellipsis/truncation, and implementing structured, tag-styled empty/placeholder cells rather than unstyled text or generic defaults drastically improves UI coherence and interface professionalism.
**Action:** When designing or updating tables in a Rich-powered CLI or TUI dashboard, always define high-contrast colored header and border styles, explicitly enable column ellipsis truncation (`overflow="ellipsis"`), and format empty states using structured placeholder text decorated with muted `[dim]` or color tags.
