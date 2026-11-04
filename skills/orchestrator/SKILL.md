---
name: orchestrator
description: Use this skill whenever the operator puts you in the orchestrator seat for a session — running an existing plan by spawning model-matched agents in isolated worktrees, keeping your own context lean by delegating the plumbing, reviewing what comes back, and landing lane work onto rc/ or main. Covers the delegate-don't-do rule, what may and may not enter the orchestrator's context, model routing per task, writing and auditing the spawn brief, supervising lanes, running audit gates with fresh agents, being the single integrator who rebases/merges and resolves conflicts, keeping the plan's status trackers true in real time as lanes land, and sweeping every document the round touched before the round is called done. Trigger on "you're the orchestrator", "act as orchestrator", "orchestrate this", "spawn agents for this", "delegate this", "run the plan", "run these lanes", "land the lanes", "review the agents' work", "keep your context lean", or any session that starts by declaring the role. The runtime half of `execution-planning`.
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
- **Carry the operator's words, not your summary of them.** A lane that answers an operator
  request gets the item's `Operator (<date>): "<verbatim>"` · `Call:` · `Beyond the ask:` lines
  (`execution-planning` § Task anatomy), and the brief says: *list in your report anything you
  add beyond the quote; write "Operator" in a commit message only before their verbatim words;
  stop and report instead of changing a recorded operator ruling.* You survey or flag each
  Beyond-the-ask line when the lane lands.
- **Agents run their gate in the foreground.** Backgrounded, a lane ends the session with nothing
  committed and failures nobody has read.
- Your context accumulates lane **summaries and diffs**, not their transcripts.

### Tests cost the machine, not just the lane

The suite runs on the operator's laptop — the same cores and memory that hold the editor, the
browser and every other session. *Five lanes each running the full suite at once (2026-09-22,
pray-app backlog-21) swapped a 4-core / 8 GB machine for a morning, produced two load-only
flakes, and each flake bought another full run.* `testlock` now rations heavy runs machine-wide
(`device-verification` § Sharing the device and the checkout), so a lane that ignores this waits
instead of colliding — but waiting is still the morning gone. Spend the budget on purpose:

- **Iterate on the tests the lane owns; gate on the suite once.** The brief names the test
  files that mirror the lane's Files (plus `test/architecture/`) and says: run those while
  fixing, and the full suite exactly once, as the final gate before reporting. A lane that
  reruns the suite after every edit is the smell.
- **Never re-run a red suite whole.** Re-run the failing file alone first. A test that passes
  alone on a busy machine is *probably* a load flake: record the failure message, report it as
  a flake rather than dropping it, and do not burn another full run on it. It is not a pass —
  your gate on the integrated tree runs the whole suite again, and that is where an
  order-dependent failure hiding behind "passes alone" gets caught.
- **Size the wave from `testlock status`, not from the plan.** `slots: n/cap` says how many
  lanes can gate at once. Spawn no more lanes than the cap plus one, stagger the rest, and put
  the slot line in every brief so the lane expects to wait.
- **Your gate on the integrated tree is the one that counts**, and you land lanes serially
  anyway — so lane gates are pre-checks, and the `-j` cap is the machine's, not yours to raise.
- **Before the round's push, run every step the CI workflow runs, not just the suite.** Tests a
  project skips by default (pray-app's tagged `research` harnesses) and the build proofs run only
  in CI, so no lane gate sees them: *pray-app round 20 — a lane's locator change broke a research
  probe that 14 green lane gates never ran; the local run of the workflow's steps caught it.*
- **Hosted CI runs only on the branches a build ships from; lanes gate locally, once.**
  Operator, 2026-11-04 (survey): *"Hosted on rc/ only"*. *Round 26 spent ~785 of the 2,000 free
  minutes in three days, 84% of them on lane and language branches whose result never ships —
  lanes pushing two or three times, and language branches red on purpose until complete.* So the
  workflow's push trigger lists `rc/**` and `master` only, and lanes **do not push**: worktrees
  share the repo's refs, so the integrator lands a lane straight from its local branch. A lane
  iterates on its targeted tests and runs the project's local mirror of the CI job **once**, as
  its final gate, under `testlock run checkout` (pray-app: `bash tool/ci_local.sh`, kept in step
  with `ci.yml` by a drift test), and reports its tail and its sha. A branch that is red on
  purpose (a language being translated) runs targeted tests only, and the full local gate once,
  when it is complete. The integrator's gate on the rebased tree stays local too, and the pushed
  RC's hosted run is the clean-room check, including the rc-only steps (the APK build proof,
  codegen freshness). The cost is laptop time, rationed by `testlock`'s slots — size waves by
  `testlock status`, as above.
- **If even the RC's run cannot answer** — queued past ten minutes, or failed with no step
  started and a billing or spending-limit annotation — the allowance is spent or Actions is down.
  Do not wait it out: gate the RC locally with the same mirror, write one line in the round file
  — *CI allowance hit on <date>, RC gated locally* — and survey the operator once about paying
  for the overage.

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

**Before spawning a lane on a store-regulated surface, check its task has a `Store check:` line (`execution-planning` § Task anatomy, `store-compliance`). No line, no spawn.**

Integration checkpoints prove the slice *works*; audit gates prove it's *sound*. Run both at each
checkpoint (or on a fixed cadence), each by a **fresh, independent agent** — never the lane that
wrote the code, never you on your own plan:

- **Architecture/code audit** — run the built-in **`/code-review`** on the lane branch or the
  merged diff since the last gate (`/code-review high <branch|path>`). It returns structured
  findings **without the diff entering your context**, which is exactly what § Your context is the
  scarce resource is protecting — so reviewing a lane by reading its diff yourself is the mistake
  this bullet exists to prevent. Raise the effort level for a foundational lane or a wide blast
  radius. What it does not judge — design seams, whether a test proves an effect or an artifact,
  comment intent — goes to a fresh agent against the `clean-code` rubric. Findings carry
  `file:line` + severity. **Verify before fixing:** confirm each finding, turn it into a
  remediation task, and **re-audit after it lands** — swapping a foundational impl (fakes→real,
  in-memory→persistent) amplifies any latent consumer bug, so the safe order is
  fix-consumers-*then*-swap.
- **Plan audit** — the plan itself: is every task still executable from Files·Spec·Acceptance by a
  fresh agent? Any sequencing/integration-order hazard? Contracts still complete? Trackers honest
  (no optimistic ticks, no merged-but-unticked drift)? Does every item that answers the operator
  quote them verbatim, and is every Beyond-the-ask line surveyed or flagged?

**`/code-review ultra` is operator-triggered and billed — you cannot launch it**, so never attempt
it via Bash or the Skill tool. When a lane earns one (a data migration, a data-loss surface, the
last gate before a beta cut), recommend it in a survey and keep working on whatever the answer
doesn't block.

Findings feed back as tasks, not just notes — an unactioned audit is theatre.

These are **round gates on a diff**. Auditing a whole codebase against principles, scoring it and
planning the remediation is a different, deliberately-invoked procedure → `code-audit`.

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
- **You own the tracker** — see § Keep the record current. Ticking being yours is also what keeps
  the plan file off the merge-hotspot list.

## Keep the record current

The plan is what the operator reads on a phone and what the next fresh-context session acts on.
**A tracker that only becomes true at the end of the round is false for the whole round.**

- **Tick at every landing, not at the end.** The fast-forward and the tracker edit are one unit of
  work — a lane is not landed until its boxes say so. Per *landing*, not per commit: batching that
  way is what keeps the bookkeeping from outweighing the fixes (`execution-planning` § The plan is
  durable memory).
- **Mark an item `⊡` the moment work starts on it**, in the same edit that lands the half. An
  item being built reads exactly like an item nobody has begun, and that is how a session
  re-plans work that is already half done.
- **Never tick ahead of the gate.** `✅` means the suite is green on the integrated tree; `⭐`
  means a device proved it. When in doubt the lower glyph is the honest one.
- **A rebase invalidates any sha you recorded early** — tick after the fast-forward, quoting the
  post-rebase sha (`git-workflow` § Release-candidate branches).
- **Watch for drift in the other direction too:** unmerged lane work isn't in the boxes, so "not
  ticked" ≠ "not started" — check the worktrees and branches for the true state.

**Close every round with a documentation sweep** — a task with an owner, before the round is
declared done, never a hope. Walk what the round touched and make it true:

- the **plan / round file** — statuses, what landed differently from the plan and *why* (an item
  closed by investigation with no code change is a result, not a gap);
- **specs and product docs** whose described behaviour the round changed — the diff that changes
  behaviour owns the line describing it (`clean-code`);
- **blast-radius maps** the round invalidated — re-verify the cards it touched, dated
  (`blast-radius-map`);
- **open items and decisions** — new operator calls added, answered ones struck;
- the **version marker**, if a build was cut (`beta-versioning`).

Then state plainly what is *still not true*: the owed device pass, the unanswered decision, the
item that closed at 198 lines against a 150-line target. A round that ends "mostly accurate"
opens the next one with a reconciliation pass nobody planned.

## Decision authority — agents make no calls

Operator, 2026-10-28: *"considering the recent regressions, no agent should make any own calls,
they have to communicate and ask for permission of orchestrator, orchestrator ask me or makes the
calls if I have given it permission."* The regressions it answers: `3cb6230d` reversed a recorded
ruling unasked, `49209383` widened a prompt rule past the ask and credited it to the operator.

**A lane agent decides nothing the brief does not pin.** It is a *call* if a reviewer could
reasonably ask "who decided that?" — product behaviour, any user-facing wording, scope past the
item, a file outside the brief's Files, an expected value the spec does not state, weakening,
skipping or deleting a test, accepting a failure as a flake, touching a recorded ruling. On a
call the agent **stops, commits nothing that depends on it, and ends its turn** with:

```
DECISION NEEDED: <one line>
Options: A) … B) …   Recommended: <A|B>, because <one line>
Blocked: <what waits on it>   Not blocked: <what it already finished>
```

Mechanics are not calls: following the file's existing idiom, naming a private helper, ordering
imports, fixing a typo the agent itself introduced. When unsure, it is a call.

**The orchestrator answers through `SendMessage`** to the same agent, so its context survives —
never by spawning a fresh one to redo the work. Before answering it decides who owns the call:

- **The operator delegated it** — a standing permission written in the round file's
  `Permissions:` line (who, date, verbatim scope). Decide, then record the call under that line:
  what was decided, under which permission. A permission is never inferred from a past answer to
  a similar question, and never widened by the orchestrator.
- **Anything else is the operator's** → one tap-to-answer survey (`operator-surveys`), batched with
  whatever else is pending; keep the unblocked lanes running meanwhile. The orchestrator applies
  the same test to its own work: a call it is about to make without a written permission is a
  survey.

Every brief carries this section's rule **verbatim** — the `DECISION NEEDED` block included —
because a spawned agent follows its harness defaults, and those default to deciding.

## Talking to the operator

They are usually watching from a phone. Decisions they delegated to you in writing, take
(§ Decision authority); every other decision — irreversible actions, scope changes, product
taste, wording, a lane's `DECISION NEEDED` — goes in a **tap-to-answer survey**, never a
paragraph and never a closing question mark (`operator-surveys`). Ask, then keep working on
whatever the answer doesn't block.

## Not covered here

How the plan is structured, contracts frozen, waves ordered, tasks written, ids numbered →
`execution-planning`. Branch/commit/merge/rebase mechanics → `git-workflow`. Suspending the run
for a later session → `wind-down`. The review rubric your audits apply → `clean-code`. Proving a
landed build on hardware → `device-verification`. Deterministic scripted fan-out (programmatic
pipelines) → the Workflow tool, a different mechanism from this human-supervised role.
