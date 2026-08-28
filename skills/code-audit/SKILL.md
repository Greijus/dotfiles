---
name: code-audit
description: Use this skill to audit a whole codebase against engineering principles — measure it, score it on named axes with the evidence cited, and turn the findings into a phased remediation plan that gets executed, device-verified and re-scored. Covers measure-never-estimate provenance, re-measuring before remediating because findings grow, turning structural claims into executable checks with a shrink-only allowlist, naming what must not be touched, converting every finding into enforcement rather than prose, ordering phases by dependency, and deferring the operator's calls instead of guessing them. Trigger on "audit this codebase", "architecture audit", "score the architecture", "how healthy is this code", "technical debt assessment", "code quality assessment", "remediation plan", "where is the debt", "re-audit", or "what are this codebase's weak points". NOT for reviewing a diff, a branch or a PR — that is the built-in `/code-review`.
---

# code-audit

Audit a **whole codebase** against engineering principles, score it, and leave behind a phased
plan that is actually executed and re-scored. Generalized from the pray-app architecture audit
(2026-08-21 → 2026-08-27): 11 findings, 8 phases, 38 commits, 1,131 → 1,937 tests, 4.1 → 4.7.

**Not a diff review.** Reviewing changed lines for bugs and cleanups is Claude Code's built-in
`/code-review` — reach for that on a PR, a branch, or "review my changes". This one reads the
whole tree at a pinned commit and produces a scored plan document.

## When to reach for this

A codebase that has grown past the point anyone holds in their head, before a refactor push, or
when the operator asks how healthy it is. It is a **deliberate, invoked procedure**, not a
background posture — a couple of days of work, not a pre-commit check. A single "should I split
this?" call is `clean-code`; one subsystem's second-order effects are `blast-radius-map`.

## 1. Measure, never estimate

Every number in the audit is a command's output, with the command shown. "Roughly 20 files" is
not a finding; `111 of 274` is. Recipes per stack → `references/measurement-recipes.md`.

- **Pin the provenance in the header**: branch, commit sha, date, version. A score without a sha
  cannot be re-checked or disputed.
- **Audit a committed tree or a clean `git archive` export**, never a dirty working tree —
  uncommitted work colours the read and nobody can reproduce it later.
- Read the *whole* tree, not the parts you expect to find problems in. In the pray case a third
  of `lib/` was invisible to the first pass and hid two real findings.

## 2. Numbers rot — re-measure before you remediate

An audit is a photograph. Six days later, in that same repo, formatter drift had gone 111 → 154
files, the profile aggregate 28 → 32 fields, and a rule flagged with three violation sites had
grown a fourth.

- **Re-run every measurement before the first remediation commit**, and record both columns:
  *at the audit* and *now*.
- **Growth between audit and fix is evidence for the finding, not a nuisance.** The drift
  continuing while the plan sat unstarted is the thesis — nothing enforces the rule — playing out
  in real time. Say so in the finding.
- Where a finding's magnitude shrank because other work closed it, say that too, and drop it.

## 3. A claim you cannot execute is a hypothesis

The pray audit asserted "zero cross-feature imports" as an exceptional property. Phase 3 turned
it into a test and found **17 real edges**.

- **Bias every structural claim toward an executable check** — an import test, a lint, a grep
  with an asserted count. If it cannot be executed, mark it as read, not as measured.
- **Being disproved by your own test is a success.** Correct the audit in place, dated, rather
  than quietly dropping the claim — the correction is the most credible thing in the document.
- **Freeze known-acceptable violations in an explicit allowlist** that fails the suite on a *new*
  entry **and on a stale one**. A list that can only shrink is a ratchet; one that only rejects
  additions rots into permanent debt.

## 4. Name what is exceptional

A short § **What is already exceptional**, before the findings. The instinct on an audit is to
"improve" something load-bearing; naming it — and *why* it is that way — is what stops that. In
pray it protected an append-only history design, a deliberate ISP split, and a one-entry-point
LLM guardrail. Anything listed here needs a decision to change, not a refactor.

**Hold this list to § 3 hardest.** Every entry is a claim, and a flattering claim is the one
nobody re-checks — pray's wrong "zero cross-feature imports" lived here, not in the findings.

## 5. Enforcement over prose — the disposition of every finding

**The central lesson.** Every pray finding was a case where the knowledge was already written
down and nothing checked it — the fake-duplication rule was in `clean-code`, *using that exact
file as its worked example*, and the file grew 261 → 362 lines anyway.

So for every finding ask: **what would have caught this automatically?**

- Expressible as a lint, a CI step, an import test, a coverage assertion → **move it there**. That
  is the fix, and it belongs in the plan as a task.
- Only then, if genuinely uncheckable, is it a judgement call worth writing down.
- **Adding a paragraph to a document nobody's tooling reads is not a remediation.** Recommend a
  skill or doc edit only where the skill is genuinely *silent*, never as the primary fix.

## 6. Score it

Nine axes, half-point granularity, **every score citing the evidence that set it** — SOLID (five
sub-axes scored separately and averaged), coupling & layering, maintainability, extensibility,
testing, documentation, failure handling, design-system fidelity, build & release hygiene. Full
rubric, worked example and per-axis evidence → `references/scoring-rubric.md`. Two rules keep the
scores honest:

- **An axis that cannot structurally reach 5 carries an explicit ceiling note** (pray: failure
  handling caps at 4.5 — real crash reporting needs a backend the local-only rule forbids).
- **A deliberate trade scores below 5 without being a defect.** The 49 service-locator call sites
  were docked *and kept*, documented as the reason the widget tests are cheap.

The axis list is a strong default, not a straitjacket: drop one the project has no surface for,
add one where a whole risk class lives (migration, security, i18n, performance) — and say which
you changed, or the next re-audit cannot be compared to this one.

## 7. Order the plan by dependency, not severity

Each phase makes the next one safe. In pray: harden the analyzer → settle the formatter → turn
the invariants into tests → *then* move code. The highest-severity finding was phase 5, fifth.

**Write the ordering rationale into each phase** ("why first", "why third") — otherwise the next
reader re-sorts it by severity and starts with the riskiest refactor on an unguarded tree.

Where a phase is about to move a subsystem that has already cost a surprise fix twice, make a
**blast-radius map its phase-0 item** and read it before the code moves → `blast-radius-map`. In
pray that item rewrote the shape of the riskiest phase before a line changed.

## 8. Some things only hardware can prove

1,900 passing tests were blind to two real defects; mocked boundaries prove nothing about real
platform behaviour. Any phase touching platform channels, permissions, persistence or launch
earns a **verification table**: what is forced, *how* to force it, and what a pass looks like.
How to force and prove it → `device-verification`. A row is `⭐` only when it was forced for
real; "would presumably work" is not a row.

## 9. Re-score after the work — measured, not predicted

Carry three columns: **was · predicted · measured after**. Where measured parts from predicted,
**explain it in the doc**. That is the point of re-scoring, and it is where the audit learns
something: pray's LSP hit 4.5 rather than 5 because the fakes got *larger* — the 150-line target
was the wrong metric for the right goal, and duplicated *rules* were the actual defect.

## 10. Defer decisions, don't guess them

Close with a decisions table — **recommendation first, alternative stated**, one row per call
that is the operator's alone: content and theological judgements, product copy, scope-widening,
anything with a taste component, and the actions only they take (version marker commits, merging
to a frozen branch). Ask them as a tap-to-answer survey, never a paragraph → `operator-surveys`.

## Output contract

**One plan doc under `docs/plans/`** — H1, then the tracker table with nothing above it, then
scope & provenance · score · what is exceptional · findings · phases · verification · open
decisions · deliberately not doing. Skeleton, with the guidance for each section, in
`references/audit-template.md`.

Ids take **word prefixes** — `finding-3`, `verification-2`, `decision-1` — and phase items stay
`<phase>.<item>`. Never a new letter series. Tracker-table, glyph and numbering rules are
`execution-planning`'s § Numbering: follow them, don't restate them.

A published artifact of the same content is an optional **second** deliverable for the operator's
reading — never a replacement for the committed doc.

## Re-audit mode

When an audit already exists, do **not** start a new document:

- **Re-measure every number** and add the *now* column.
- **Diff the verdict** — does each axis score still hold on the new lines?
- **Read what the first pass never covered.** New subsystems are where the blind findings are.
- **Correct errors in place, dated and marked** (⚠️ *corrected by phase 3, 2026-08-27*), never
  silently.
- New findings get the next free `finding-N` and their own phase at the end; ids are never reused.

## Running the plan

The audit is not done when the doc is written. → `execution-planning` for structuring it into
lanes and `orchestrator` for running them, `git-workflow` for how each lane lands, `clean-code`
for the rubric the remediation itself is held to.

## Why this skill exists at all

The pray audit's own conclusion was *"do not write a new skill for any of this"* — because the
rule that would have prevented its largest finding was already written down and ignored. That
holds, and it is the reason this skill is a **procedure you invoke**, not a rule you hope loads.
It earns its place only as long as its findings keep converting into lints, CI steps and tests.
**The day an audit's remediation is mostly documentation edits, the audit failed.**

## Not covered here

SOLID detail, design seams, the bug-fix blast-radius sweep, the CI template → `clean-code`.
Diff/PR review → the built-in `/code-review`. Mapping one subsystem's second-order effects →
`blast-radius-map`. Plan structure, ids and trackers → `execution-planning`; running the plan →
`orchestrator`; landing lanes → `git-workflow`. Forcing procedures and device passes →
`device-verification`. Asking the operator → `operator-surveys`.
