---
name: execution-planning
description: Use this skill when planning a build too large for one session or one context window — turning it into a phased execution plan that a high-intelligence orchestrator runs by spawning model-matched agents across parallel lanes in isolated git worktrees. Covers the serial-spine/parallel-ribs shape, freezing contracts as the barrier that buys parallelism, routing the right model to each task, integration checkpoints, single-integrator merges, and durable trackers that survive context loss. Trigger when asked to plan a multi-feature build, scope work into parallel lanes, decide which model runs which task, or write/structure an execution or implementation plan.
---

# execution-planning

GenX Labs' method for builds too big to hold in one session: the highest-capability model **orchestrates** — it plans, freezes the shared surface, spawns cheaper model-matched agents to build parallel lanes, then reviews and integrates. Proven on the pray-app build.

## When to reach for this

Only when a build spans many features/files that won't fit one context window or one sitting. A single feature — just build it; this ceremony is pure overhead below that threshold.

## Shape: serial spine, then parallel ribs

- **Phase 0 is serial** — one session, no parallelism. It lays foundations (scaffold, models, persistence, DI, CI) **and freezes the interface contracts** the parallel work codes against.
- Lanes run in parallel **only after the spine is frozen**.
- *Smell:* starting lanes before the shared foundation is stable → they collide and redo each other's work. *Fix:* finish and freeze the spine first.

## Freeze the contracts — this is what buys the parallelism

The single highest-leverage move. Before spawning anything:

- Define abstract interfaces (+ the model/data types) for **every** service in one place, and **freeze them**. Lanes code against the frozen contract and mock it — so they never block on each other's progress.
- A contract change mid-build is an **orchestrator** decision, never a lane's — one lane can't move a type another lane depends on.
- Without frozen contracts, lanes constantly renegotiate shared types and serialize anyway.

## Route the model to the task

The orchestrator assigns each lane a model matched to the work's difficulty:

- **Highest tier (e.g. Opus):** intricate semantics, safety/theology/correctness-critical logic, anything hard to verify or expensive to get wrong. Personally review these prompts.
- **Mid tier (e.g. Sonnet):** high-volume translation (design→UI) and precisely-spec'd mechanical work where the spec already pins the answer.
- The orchestrator **reviews every diff regardless of the lane's model** — a cheaper executor never means unreviewed output.
- *Rationale:* pay for intelligence where it changes the outcome; don't pay for it where the spec removes the ambiguity.

## Partition to keep merges clean

- Split lanes **by directory/service** so they touch disjoint files — most conflicts simply never arise.
- The cross-cutting files are the conflict hotspots: dependency manifest, DI registration, i18n strings, shared DB schema, and **the plan file itself**. Give each an owner or serialize edits to it.

## Waves and integration checkpoints

- Order lanes by dependency into **waves**; within a lane, do the checkpoint-subset tasks first and **defer the tails**.
- **Integration checkpoints (ICs)** are explicit barriers — named tasks that must be green before anyone proceeds past them. This is where contract mismatches surface and get fixed, on a real end-to-end slice, not in isolation.

## One integrator merges

- **Only the orchestrator merges** — serially, running lint + test before each merge, resolving conflicts, **squashing each lane to one clean commit**. (Squash by default; a raw merge commit per lane muddies history.)
- Lane agents commit freely on their own `feat/lane-*` branch inside an isolated worktree; they never merge into each other or into main.

## Fresh context per agent — the brief is load-bearing

- Each spawned agent starts with an **empty context**. It knows only what the spawn prompt + cited spec + frozen contract tell it. Write the brief **self-contained**; frozen contracts are what keep it short.
- The orchestrator's context accumulates lane **summaries and diffs**, not their transcripts — so it can supervise many lanes without filling up.

## The plan is durable memory

- Track progress with **checkboxes in a committed plan file**. It survives context compaction and session loss — the durable spine of a multi-session build.
- Watch for **tracker drift:** unmerged lane work isn't reflected in the boxes, so "not ticked" ≠ "not started" — check the worktrees/branches for true status. The orchestrator owns ticking, which also keeps the plan file off the merge-hotspot list.

## Task anatomy

Every task carries three fields: **Files** (what it touches) · **Spec** (source of truth, cited) · **Acceptance** (the testable done-condition). Check the box only when acceptance holds and tests pass. A task a fresh-context agent can't execute from these three alone is under-specified — fix the task, not the agent.

## Not covered here

SOLID/testing/CI → `clean-code`. Flutter layout → `flutter-mvp`. Commits/branches/PRs → `git-workflow`. Deterministic multi-agent *scripts* (programmatic fan-out/verify pipelines) → the Workflow tool, a different mechanism from this human-readable planning discipline.
