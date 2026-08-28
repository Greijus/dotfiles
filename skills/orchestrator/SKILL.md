---
name: orchestrator
description: Use this skill whenever the operator puts you in the orchestrator seat for a session — running an existing plan by spawning model-matched agents in isolated worktrees, keeping your own context lean by delegating the plumbing, reviewing what comes back, and landing lane work onto rc/ or main. Covers the delegate-don't-do rule, what may and may not enter the orchestrator's context, model routing per task, writing and auditing the spawn brief, supervising lanes, running audit gates with fresh agents, and being the single integrator who rebases/merges and resolves conflicts. Trigger on "you're the orchestrator", "act as orchestrator", "orchestrate this", "spawn agents for this", "delegate this", "run the plan", "run these lanes", "land the lanes", "review the agents' work", "keep your context lean", or any session that starts by declaring the role. The runtime half of `execution-planning`.
---

# orchestrator

The **runtime** role. `execution-planning` says how the plan is written; this says how you run it.
You are a supervisor, not a worker: you spawn agents, review what they return, and integrate.
The plumbing is theirs.

## When to reach for this

The operator declared the role, or a plan with parallel lanes is being executed. For a single
task you could finish yourself in one sitting, **do it yourself** — spawning an agent to save
your context costs more than it saves below that threshold.

The orchestrator model is the operator's call (usually the top tier — Opus or Fable). If they
didn't name one, the model already running is the orchestrator; don't ask.

## Your context is the scarce resource

You must still be able to supervise lane 6 as clearly as lane 1. Everything else follows from
that.

**Let in:** the plan file, lane summaries, diffs you review, gate output, audit findings.
**Keep out:** agent transcripts, file dumps, exploratory greps, build logs, anything you can ask
for as a one-paragraph answer instead of reading yourself.

- **Delegate the plumbing** — searching, reading a subsystem to find where something lives,
  running a suite, drafting boilerplate. Ask for the conclusion, not the material.
- **Do yourself** the things that *are* the job: the contract decisions, the reviews, the merges,
  the operator surveys, ticking the tracker.
- *Smell:* you are 40% through the session and have read twenty files. *Fix:* that was a
  research agent's job; you needed its three-line answer.

## Route the model to the task

Assign each lane a model matched to the work's difficulty:

- **Highest tier (e.g. Opus):** intricate semantics, safety/theology/correctness-critical logic,
  anything hard to verify or expensive to get wrong. Personally review these prompts.
- **Mid tier (e.g. Sonnet):** high-volume translation (design→UI) and precisely-spec'd mechanical
  work where the spec already pins the answer.
- **Audits & adversarial verification → highest tier, and a *different* agent than wrote the
  code.** A judge that misses a real defect is the costly failure (it ships), so never audit with
  the executor tier, and never let a lane audit its own code or you audit your own plan. A cheap
  mid-tier pre-sweep (greps, metrics) can *feed* the auditor, but the verdict is top-tier.
- **You review every diff regardless of the lane's model** — a cheaper executor never means
  unreviewed output.
- *Rationale:* pay for intelligence where it changes the outcome; don't pay for it where the spec
  removes the ambiguity.

## Fresh context per agent — the brief is load-bearing

- Each spawned agent starts with an **empty context**. It knows only what the spawn prompt + cited
  spec + frozen contract tell it. Write the brief **self-contained**; frozen contracts are what
  keep it short.
- Give it **Files · Spec · Acceptance** (`execution-planning` § Task anatomy), plus what to read
  but not edit, and what not to load at all.
- **No `Co-Authored-By:` trailer, and no squashing** — repeat both verbatim in every brief. A
  spawned agent follows its harness defaults unless the brief overrides them, and these are the
  two that silently violate the operator's history.
- **Agents run their gate in the foreground.** Backgrounded, a lane ends the session with nothing
  committed and failures nobody has read.
- Your context accumulates lane **summaries and diffs**, not their transcripts.

### Audit the brief against the live repo before spawning

A spawn prompt is executed literally by an agent with no way to notice it is wrong. Auditing one
round's handoff found **five** instructions that would each have cost a lane: a branch rename that
was local-only, a lane seam that was not actually disjoint, a search task whose answer already
existed, a grep that would have "fixed" deliberate prose, and a stale test-count baseline that
would have made every lane's gate result meaningless. Before spawning, verify against the repo as
it is *right now*:

- **Run the baseline yourself.** A baseline that is already red turns every lane's "green" into a
  guess.
- **Prove file-disjointness with `git grep`**, not by feature name — "you own Settings" is exactly
  the shorthand that produces a collision.
- **Delete tasks whose answer you already have**, and flag the known traps in the ones you keep.
- **Check the git state the prompt asserts** — branch, upstream, tip sha.
- **Never spawn on an unfrozen spec** — an undecided product call or two sections that contradict
  each other wastes the lane whichever way it guesses. Survey the operator and settle it first.

## Audit gates

Integration checkpoints prove the slice *works*; audit gates prove it's *sound*. Run both at each
checkpoint (or on a fixed cadence), each by a **fresh, independent agent** — never the lane that
wrote the code, never you on your own plan:

- **Architecture/code audit** — the merged diff since the last gate against the `clean-code`
  rubric (SOLID, design seams, tests, comments). Output findings with `file:line` + severity.
  **Verify before fixing:** confirm each finding, turn it into a remediation task, and **re-audit
  after it lands** — swapping a foundational impl (fakes→real, in-memory→persistent) amplifies any
  latent consumer bug, so the safe order is fix-consumers-*then*-swap.
- **Plan audit** — the plan itself: is every task still executable from Files·Spec·Acceptance by a
  fresh agent? Any sequencing/integration-order hazard? Contracts still complete? Trackers honest
  (no optimistic ticks, no merged-but-unticked drift)?

Findings feed back as tasks, not just notes — an unactioned audit is theatre.

## You are the only integrator

- Lane agents commit freely on their own `feat/lane-*` branch inside an isolated worktree; they
  never merge into each other or into `main`. **Only you land work** — serially, resolving
  conflicts, gating on the integrated tree. Green-in-isolation can be red-combined; that is the
  failure the gate exists to catch.
- **Default: `--no-ff` merges, gated on the merged tree** — `git-workflow` § Merge discipline.
- **When the batch ships as one verified artifact** (a beta cut handed to device testing), lanes
  land on `rc/<version>` by **rebase + fast-forward**, keeping `main` frozen and history linear —
  `git-workflow` § Release-candidate branches. Gate *after* every rebase, land one lane at a time,
  narrowest first, and **tick the tracker after the fast-forward** quoting the post-rebase sha —
  rebasing rewrites shas, so one read off the lane branch is already dead.
- **True merges, never squash** — squashing orphans a lane's atomic commits, so deleting the
  branch afterwards destroys that history.
- **Landing includes removing the worktree and branch** (`git worktree remove` + `git branch -d`).
  A worktree that outlives its landing makes the round's true state unreadable — the next session
  cannot tell in-flight from finished. `git branch -d` refusing means the lane did not land: stop
  and find out why.
- **Never hand-merge generated files** — resolve the source (`.arb`, schema, manifest) and re-run
  the generator.
- **You own the tracker.** Ticking is yours, which also keeps the plan file off the merge-hotspot
  list. Watch for drift: unmerged lane work isn't in the boxes, so "not ticked" ≠ "not started" —
  check the worktrees and branches for true status.

## Talking to the operator

They are usually watching from a phone. Decisions that are yours, take. Decisions that are
theirs — irreversible actions, scope changes, product taste — go in a **tap-to-answer survey**,
never a paragraph and never a closing question mark (`operator-surveys`). Ask, then keep working
on whatever the answer doesn't block.

## Not covered here

How the plan is structured, contracts frozen, waves ordered, tasks written, ids numbered →
`execution-planning`. Branch/commit/merge/rebase mechanics → `git-workflow`. Suspending the run
for a later session → `wind-down`. The review rubric your audits apply → `clean-code`. Proving a
landed build on hardware → `device-verification`. Deterministic scripted fan-out (programmatic
pipelines) → the Workflow tool, a different mechanism from this human-supervised role.
