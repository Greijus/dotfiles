---
name: wind-down
description: Use this skill to gracefully suspend an in-flight multi-agent build for later resume — end of a session, or any "stop for now / wind down / pause the build / we'll finish tomorrow" moment. Covers halting agents at safe commit boundaries without interrupting a critical task, snapshotting an executive status report, ticking only truly-done trackers, and writing a self-contained RESUME block into the execution plan so a fresh-context orchestrator (even in a brand-new session) can restart every lane exactly where it left off. Trigger on "wind down", "stop for today", "pause the work", "park this", "we'll resume later", or wrapping up a build session. The inverse of `execution-planning`.
---

# wind-down

The graceful inverse of `execution-planning`: suspend an in-flight multi-agent build so a **fresh session with no memory of this one** can resume it — zero work lost, no half-done error propagated. The handoff is the plan file, never your context.

## When to reach for this

Winding down a session that spawned parallel lanes/agents and isn't finished. For a solo task with nothing running, just commit and stop — this runbook is for the multi-agent case.

## 1. Quiesce agents — safe boundary, never mid-critical-task

Signal each running lane/agent to halt **at its next safe boundary**, then wait for it to get there. Do not hard-kill.

- A safe boundary is a **clean commit** with a compiling (ideally green) tree.
- **Never interrupt a critical section:** an in-progress commit, merge, DB migration, push, or a test run writing artifacts. Interrupting these corrupts state or leaves a half-merge.
- If an agent is mid-task, tell it to either finish the current atomic unit or **shelve** it — a `wip:` commit or a stash — at the next boundary. Nothing uncommitted is left in a worktree.
- Leave locked worktrees intact; a locked worktree preserves its state for resume.

## 2. Snapshot the executive report

Capture the state both **the operator reads** (status) and **the orchestrator reads** (to resume):

- `master` sha + whether it's green.
- Per lane: branch, HEAD sha, working-tree state (clean / wip-committed / stashed), and % of its tasks done.
- What's **merged** vs **in-flight** vs **not-started**; the current wave; the next integration checkpoint.
- **Open findings/known bugs** — anything that must be fixed before a given lane resumes, so errors don't propagate down it.

## 3. Tick honestly, then write the RESUME block

- Tick a tracker checkbox **only** where acceptance holds and tests pass. Never tick in-flight work — an optimistic tick is a lie the next session acts on.
- Add a prominent **`## RESUME (wound down <absolute-date>)`** section near the top of the execution plan (right after the status line). This is the crux — it must let a fresh-context orchestrator restart with no operator re-explanation. For **each paused lane** it states:
  - **branch + HEAD sha**, and worktree to reuse (or recreate).
  - **the exact next task(s)** — task id + one line, not "continue".
  - **model** to spawn it with, and **do-this-first** steps (e.g. "rebase on master; run analyze+test; then B.4").
  - any **blocking dependency or open bug** that must clear before it resumes.
- Also record: what's merged, the current wave, and the next checkpoint — so the orchestrator rebuilds the picture from the plan alone.

## 4. Leave the repo safe

- Everything committed or explicitly stashed — nothing uncommitted survives only in a dead session.
- **Push all branches to origin** as backup (per the build's commit policy).
- If `master` is **red**, do not pretend otherwise — make "fix the red tree" the very first line of the RESUME block, with the failing command.

## 5. The fresh-context test

Before you stop, ask: *could a brand-new session, reading only the RESUME block + the report and nothing else, restart every lane correctly?* If not, the block is under-specified — fix it now. Same discipline as task anatomy in `execution-planning`: if a fresh agent can't act on it, it's not done.

## Not covered here

How the plan/lanes were structured → `execution-planning`. WIP-commit / stash / push mechanics → `git-workflow`. Resuming is just re-reading the RESUME block and re-spawning per `execution-planning`.
