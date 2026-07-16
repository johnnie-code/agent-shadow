# Project Shadow: User & Command Line Guide

This guide describes how to run and manage Shadow on Android (Termux) or standard Linux distributions.

## Command Line Commands

Verify commands by running:
`shadow [COMMAND]`

### Core Commands

| Command | Description |
|---|---|
| `shadow start` | Start the background FastAPI API server daemon |
| `shadow stop` | Stop any background running Shadow API server daemon |
| `shadow status` | Display system database state, metrics, and recent decision logs |
| `shadow mission` | Parse `mission.md` file and synchronize structured goal objects |
| `shadow goals` | List active mission goals and project track states |
| `shadow tasks` | List and prioritize currently queued action items |
| `shadow execute [ID]` | Execute a single task matching its safety clearance |
| `shadow approvals` | Review, approve, or reject Safety Level 2 hold actions |
| `shadow search [QUERY]` | Perform search over long-term memories and conversation audits |
| `shadow memory` | Display persistent memory block counts and category metadata |
| `shadow opportunities` | Trigger web scans and extract new matched opportunities |
| `shadow schedule` | Display registered interval and event-based scheduler cadences |
| `shadow providers` | List active, configured default, and mock AI Providers |
| `shadow plugins` | List discovered dynamic core tools, plugins, and skills |
| `shadow reflect` | Trigger manual strategic evening reflection audit |
| `shadow update` | Reload configuration settings, reload database schema, and update goals |

## TUI Dashboard

Start the live terminal-friendly layout:
`python -m shadow.cli.tui`

It displays:
- Active Core Metrics & States (CPU, running processes, memory blocks, etc.)
- Mission Goals Progress Tracking
- High Priority Task Queue
- Dynamic Decision & Event Logs
