# Palette's UX/a11y Journal

This journal documents critical, reusable UX and accessibility insights discovered during development.

## 2026-07-18 - Interactive CLI Loop Configuration UX
**Learning:** Terminal CLI users are highly sensitive to commands that exit immediately after applying a single change when they have multiple changes to perform. Wrapping interactive text-based setup menus in clean input/evaluation loops significantly reduces terminal re-entry fatigue and improves navigation accessibility.
**Action:** Always design text-based configurations and settings commands with loops that re-evaluate and display fresh values, supporting explicit exit choices.

## 2026-07-20 - Testing Interactive CLI Passwords UX
**Learning:** Testing interactive console loops with password masking inputs (e.g. `Prompt.ask(..., password=True)`) using `typer.testing.CliRunner` or similar test runners will block/hang indefinitely. This happens because `getpass.getpass` expects an interactive TTY and blocks on redirected `sys.stdin` streams.
**Action:** Always mock/patch `getpass.getpass` in the test suite when verifying CLI configuration commands that prompt for masked credentials.
