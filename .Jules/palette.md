# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-19 - Robust Interactive Loop Validation and Required Prompt Skips
**Learning:** When using interactive CLI settings loops, accepting unvalidated input can cause downstream silent crashes or configuration corruptions. Furthermore, prompting for optional secret credentials (like API keys) without a standard default/skip path forces the user into terminal deadlocks. Providing explicit skip instructions and robust local validation loops prevents configuration errors while maintaining seamless navigation flow.
**Action:** Always wrap interactive menu field edits in robust validation loops with instant feedback, and use default values (e.g. `default=""` and `hide_input=True`) for secret key prompts to allow optional skip-on-empty behavior.
