# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-21 - CLI Input Validation and Key Masking UX
**Learning:** When users edit critical configuration variables in an interactive CLI (like default AI providers or numerical limits), missing validation can lead to malformed config files that crash subsequent application boots. In addition, using non-standard prompting parameters (like password=True in Typer) can cause silent test runner crashes; using the standard hide_input=True ensures robust input masking and universal framework compatibility.
**Action:** Always wrap interactive prompts in strict type-and-value validation loops with helpful error explanations, and mask sensitive credentials with standard, compliant prompt attributes.

## 2026-07-30 - CLI Integration Test Reference Desynchronization
**Learning:** CLI and diagnostic integration tests that mock/patch environment variables or verify CLI commands can suffer from flaky failures and state leakage across the test suite if commands or configuration singletons are imported at the module level. This is because other tests might dynamically modify or mask `sys.modules`, desynchronizing cached variables or module references.
**Action:** Always dynamically import target CLI command/app objects locally inside individual test functions, reset module-level singletons directly via `sys.modules`, and use scoped pytest autouse fixtures to restore both disk files and in-memory `os.environ` keys starting with prefix namespaces.
