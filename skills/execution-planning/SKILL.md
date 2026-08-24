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
- **Audits & adversarial verification → highest tier, and a *different* agent than wrote the code.** A judge that misses a real defect is the costly failure (it ships), so never audit with the executor tier, and never let a lane audit its own code or the orchestrator audit its own plan. A cheap mid-tier pre-sweep (greps, metrics) can *feed* the auditor, but the verdict is top-tier.
- The orchestrator **reviews every diff regardless of the lane's model** — a cheaper executor never means unreviewed output.
- *Rationale:* pay for intelligence where it changes the outcome; don't pay for it where the spec removes the ambiguity.

## Partition to keep merges clean

- Split lanes **by directory/service** so they touch disjoint files — most conflicts simply never arise.
- The cross-cutting files are the conflict hotspots: dependency manifest, DI registration, i18n strings, shared DB schema, and **the plan file itself**. Give each an owner or serialize edits to it.

## Waves and integration checkpoints

- Order lanes by dependency into **waves**; within a lane, do the checkpoint-subset tasks first and **defer the tails**.
- **Integration checkpoints (ICs)** are explicit barriers — named tasks that must be green before anyone proceeds past them. This is where contract mismatches surface and get fixed, on a real end-to-end slice, not in isolation.

## Audit gates

Integration checkpoints prove the slice *works*; audit gates prove it's *sound*. Run both at each checkpoint (or on a fixed cadence), each by a **fresh, independent agent** — never the lane that wrote the code, never the orchestrator on its own plan:

- **Architecture/code audit** — the merged diff since the last gate against the `clean-code` rubric (SOLID, design seams, tests, comments). Output findings with `file:line` + severity. **Verify before fixing:** confirm each finding, turn it into a remediation task, and **re-audit after it lands** — swapping a foundational impl (fakes→real, in-memory→persistent) amplifies any latent consumer bug, so the safe order is fix-consumers-*then*-swap.
- **Plan audit** — the plan itself: is every task still executable from Files·Spec·Acceptance by a fresh agent? Any sequencing/integration-order hazard? Contracts still complete? Trackers honest (no optimistic ticks, no merged-but-unticked drift)?

Findings feed back as tasks, not just notes — an unactioned audit is theatre.

## One integrator merges

- **Only the orchestrator merges** — serially, resolving conflicts, and gating on the **merged tree** (`git merge --no-ff --no-commit` → lint + full tests → `git commit`, or `git merge --abort`). Green-in-isolation can be red-combined; that is the failure the gate exists to catch.
- **True merges (`--no-ff`), never squash** — squashing orphans a lane's atomic commits, so deleting the branch afterwards destroys that history. A real merge makes them ancestors of `main`, which is what makes branch cleanup safe. See `git-workflow` § Merge discipline for the full rule.
- Lane agents commit freely on their own `feat/lane-*` branch inside an isolated worktree; they never merge into each other or into main. **They run their gate in the foreground** — a backgrounded suite is how a lane ends a session with nothing committed and failures nobody has read.
- **Landing a lane includes removing its worktree and branch** (`git worktree remove` + `git branch -d`). A worktree that outlives its landing makes the round's true state unreadable — the next session cannot tell in-flight from finished. See `git-workflow` § Release-candidate branches.
- **No `Co-Authored-By:` trailer, and no squashing** — repeat both verbatim in every agent brief. A spawned agent follows its harness defaults unless the brief overrides them, and these are the two that silently violate the operator's history.
- **When the batch ships as one verified artifact** (a beta cut handed to device testing), the alternative is a `rc/<version>` branch that lanes land on by *rebase + fast-forward*, keeping main frozen and the history linear — `git-workflow` § Release-candidate branches. It gates twice per lane instead of once, and rewrites shas, so **tick the tracker after the fast-forward, never off the lane branch**.

## Fresh context per agent — the brief is load-bearing

- Each spawned agent starts with an **empty context**. It knows only what the spawn prompt + cited spec + frozen contract tell it. Write the brief **self-contained**; frozen contracts are what keep it short.
- The orchestrator's context accumulates lane **summaries and diffs**, not their transcripts — so it can supervise many lanes without filling up.

### Audit the brief against the live repo before spawning

A spawn prompt is executed literally by an agent with no way to notice it is wrong. Auditing one round's handoff found **five** instructions that would each have cost a lane: a branch rename that was local-only, a lane seam that was not actually disjoint, a search task whose answer already existed, a grep that would have "fixed" deliberate prose, and a stale test-count baseline that would have made every lane's gate result meaningless. Before spawning, verify against the repo as it is *right now*:

- **Run the baseline yourself.** A baseline that is already red turns every lane's "green" into a guess.
- **Prove file-disjointness with `git grep`**, not by feature name — "you own Settings" is exactly the shorthand that produces a collision.
- **Delete tasks whose answer you already have**, and flag the known traps in the ones you keep.
- **Check the git state the prompt asserts** — branch, upstream, tip sha.

## Numbering and the phase table — the GenX standard

**Everything is numbered. `R` is the only letter in the scheme, and only as a round prefix.**

| Kind of id | Form | Example |
|---|---|---|
| Plan item | `<phase>.<item>` | `4.2` — phase 4, item 2 |
| Round finding | `R<round>-<phase>.<item>` | **`R3-1.1`** — round 3, phase 1, item 1 |
| Round finding, flat round | `R<round>-<item>` | `R10-2` |
| Series no round owns | `<word>-<item>` | `backlog-8`, `verification-3` |

Phase 4's items are 4.1, 4.2, 4.3 — never `B5`, `X12`, `W3`. **Never start a letter series**, for
any reason: not for a plan, not for a round's findings, not for a device checklist, not for a
deferred backlog, and *especially* not because a neighbouring doc already has one. After a few
rounds nobody can tell `W3` from `X3` from `B3`, every cross-reference becomes a lookup, and the
operator ends up repairing the docs by hand. If a letter feels necessary, what the scheme
actually needs is **another number level** (`R3-1.1.2`), not another alphabet.

Cite round findings **round-qualified** — `R3-1.1`, never a bare `1.1` — because a bare item
number is ambiguous the moment it leaves its own round's file. Ids are never reused.

**Legacy letter ids are frozen history, not a precedent.** Where an old series (`F#`, `X#`, `Z#`,
`V#`, `L#`…) is stamped into commit messages it cannot be renamed, so quote it verbatim when
citing that commit — and do not extend it, mirror it, or take it as licence to open a new one.

**Every plan opens with its tracker table — the very first thing under the H1, above everything
else.** Not below a framing blockquote, not below a RESUME block, not below "why this exists",
not below an overview, a status paragraph, or a "this file replaces…" note. The operator opens a
plan to see *where the work is*, usually on a phone, and anything above the table is something
they have to scroll past to get the one answer they came for. **This applies to every tracked
doc, not just plans** — a round file, an open-items list and a consolidated history all open with
their own table on the same terms.

```markdown
# Plan: <name>

| # | Phase | Items | Status |
|---|-------|-------|--------|
| 1 | Fix the wiring | ✅ 1.1 · ⊡ 1.2 · ☐ 1.3 | ongoing |
| 2 | Safety | ⭐ 2.1 · ✅ 2.2 | implemented |

☐ not started · ⊡ ongoing · ✅ implemented · ⭐ verified on hardware

<!-- everything else below: RESUME, framing, why, sequencing, tracker detail -->
```

**Order below the table is fixed:** the table, then the glyph legend, then a **RESUME** block if
the plan has been wound down, then the framing/why, then the detail. RESUME sits *underneath* the
table because it answers "how do I restart" — a question you only ask after you know where the
work stopped, which is what the table just told you.

**The table is only worth having if it is true at the moment it is read.** An item that is
half-built is `⊡`, today, in the same edit that lands the half — not `☐` until it is finished.
Leaving a started item unticked is the most common way a plan lies, because it reads exactly like
work nobody has begun, and the next session re-plans it from scratch.

**Item glyphs** — one per item, so the row shows progress without opening anything:

| Glyph | Means |
|---|---|
| ☐ | not started |
| ⊡ | ongoing |
| ✅ | implemented (code landed, gate green) |
| ⭐ | **verified** — proved on real hardware, not just tested |

**Phase status** is one of `not started · ongoing · implemented · verified · closed`. The
distinction that earns its keep is **implemented ≠ verified ≠ closed**: implemented means the
gate is green, verified means a device proved it (`device-verification`), closed means nothing is
outstanding — including the operator's own follow-ups. A phase whose code landed but whose device
pass has not run is `implemented`, and saying so is the whole point.

The table is a **summary of the tracker, not a second source of truth** — the per-item detail
stays in one § Tracker section, and both are updated in the same edit. Two places that can
disagree is one place too many; if the table starts drifting, delete it rather than reconcile it.

## The plan is durable memory

- Track progress with **checkboxes in a committed plan file**. It survives context compaction and session loss — the durable spine of a multi-session build.
- Watch for **tracker drift:** unmerged lane work isn't reflected in the boxes, so "not ticked" ≠ "not started" — check the worktrees/branches for true status. The orchestrator owns ticking, which also keeps the plan file off the merge-hotspot list.
- **Record only what git cannot derive.** A status table restating which version `main` is at, or where a round's work lives, is a second source of truth that drifts and then needs its own reconciliation commits. On pray-app plan bookkeeping ran at ~1.9 docs commits per fix commit; batching ticks per *landing* rather than per fix keeps the drift safety and halves the noise.
- **A written procedure is code — run it before you record it.** Anything a later reader will execute (a forcing recipe, a repro, a setup script) is verified by executing it, not by writing it carefully.
- **Durable claims carry a date, and get re-checked before they block anything.** *A feature was written off as impossible on platform research that a single OS release had already made obsolete; the "impossible" was repeated as fact for two rounds.*

## Task anatomy

Every task carries three fields: **Files** (what it touches) · **Spec** (source of truth, cited) · **Acceptance** (the testable done-condition). Check the box only when acceptance holds and tests pass. A task a fresh-context agent can't execute from these three alone is under-specified — fix the task, not the agent.

**Files is what the lane edits. Say separately what it must read but not edit, and what to skip:**

```
Reference (load): docs/product/<spec>.md § <section>
Do NOT load: <sibling rounds>, <unrelated docs>
```

A fresh-context agent otherwise either re-derives the spec location from prose scattered across the round file, or slurps sibling rounds/docs it doesn't need. Two lines, not a new section.

Two ways a Spec is not actually frozen, both of which cost a lane:

- **It contains an undecided product call, or two sections that contradict each other.** Never spawn a lane on one — ask the operator and settle it first. Guessing wastes the lane whichever way you guess. *One round lost a full rebuild to a spec whose § Behaviour and § Settings disagreed; the wrong reading was built first.*
- **It only describes the blank-slate user.** Anything with counters, streaks, history or migrations states its behavior for the user who *already has data* — mid-run adoption, past-the-target, dead or expired state. Otherwise real history keeps arriving as a brand-new product question: one mechanic was re-specced in three consecutive rounds for exactly this reason.

Acceptance criteria can be wrong too — when a device check disagrees with the accept line, suspect both.

## Not covered here

SOLID/testing/CI → `clean-code`. Flutter layout → `flutter-mvp`. Commits/branches/PRs → `git-workflow`. Deterministic multi-agent *scripts* (programmatic fan-out/verify pipelines) → the Workflow tool, a different mechanism from this human-readable planning discipline. A subsystem whose blast radius keeps surprising lanes across rounds → `blast-radius-map`, which persists the Hits/Does-not-hit list this skill's Reference line only states per-task.
