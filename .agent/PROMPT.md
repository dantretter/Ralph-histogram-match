> ⛔ **ONE TASK PER INVOCATION** — Complete one task from @.agent/tasks.json, commit, output `<promise>TASK-{ID}:DONE</promise>`, and STOP. Do NOT start the next task. Do NOT use parallel agents for multiple tasks.

## Overview

You are implementing the project described in @.agent/prd/SUMMARY.md

## Required Setup

This is a Python CLI tool. No server needs to run.

1. Create the venv once if `.venv/` is missing: `python3 -m venv .venv`
2. Install deps if `requirements.txt` exists: `.venv/bin/pip install -r requirements.txt`

Run all Python tools through `.venv/bin/` (`.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`).

## Before Starting

Check @.agent/STEERING.md for critical work. Complete items in sequence, remove when done. Only proceed to implement tasks if no critical work pending.

## Task Flow

Tasks are listed in @.agent/tasks.json

1. Pick highest-priority task with `passes: false` in `tasks.json`
2. Read full spec: `.agent/tasks/TASK-${ID}.json`
3. Check existing dir structure in @.agent/STRUCTURE.md
4. Implement steps by step according to spec and write unit test
5. Run `.venv/bin/ruff check --fix src tests` then `.venv/bin/ruff format src tests`.
6. Run `.venv/bin/pytest` from the repo root.
7. All tests must pass. Broke unrelated test? Fix it before proceeding.
8. When tests pass, set `passes: true` in `tasks.json` for the task you completed.
9. Log entry → `.agent/logs/LOG.md` (date, brief summary, newest at the top)
10. Update `.agent/STRUCTURE.md` if dirs changed. Exclude dotfiles, tests and config.
11. Commit changes, using the Conventional Commit format.

## Rules

- **CRITICAL**: Only work on **ONE task per invocation**. After committing the task, output `<promise>TASK-{ID}:DONE</promise>` and **STOP immediately**. Do NOT read the next task. Do NOT continue working. Your response **must END** after the promise tag. Any output after it is a violation.
- Kill all background processes before outputting the promise tag.
- No git init/remote changes. **No git push**.
- Check the last 5 tasks in `.agent/logs/LOG.md` for past work
- **CRITICAL**: When **ALL** tasks pass → output `<promise>COMPLETE</promise>` and **nothing else**.

## Help Tags

Try solving tasks yourself first.
When stuck after all possible solutions exhausted, output one of the following tags:

1. **BLOCKED** — technical issues: Python/venv broken, pytest won't run, deps won't install, env issues, no network, service outages, invalid/missing credentials. Output:

```
<promise>BLOCKED:brief description</promise>
```

**Exit immediately (no workarounds) for environment constraints you cannot fix from inside the sandbox:**

- `Blocked by network policy` → firewall, only user can change from host
- Missing/invalid credentials or API keys
- Required system service unavailable
- Hardware/arch incompatibility with no known fix

These are not bugs. No amount of retries, alternative downloads, or package managers will help. Output BLOCKED on first failure.

2. **DECIDE** — need human input: lib choices, architecture, unclear requirements, breaking changes. Output:

```
<promise>DECIDE:question (Option A vs B)</promise>
```
