# Audit doc skeleton

Copy into `docs/plans/<name>-audit.md`. Order is fixed — the tracker table is the first thing
under the H1, because the operator opens this on a phone to see where the work is
(`execution-planning` § Numbering and the phase table). Delete the file when the last phase lands.

```markdown
# Plan: <subject> audit & remediation

| # | Phase | Items | Status |
|---|-------|-------|--------|
| 1 | <makes phase 2 safe> | ☐ 1.1 · ☐ 1.2 | not started |
| 2 | <…> | ☐ 2.1 | not started |

☐ not started · ⊡ ongoing · ✅ implemented · ⭐ verified on hardware · ⊘ investigated, no change

> **Ordered by dependency, not by severity** — each phase makes the next one safe. <One line on
> the total shape and cost.> Nothing here is a ship gate: the codebase scores **X.X/5** as it
> stands, and <the closest thing to a user-visible defect>.

## Scope and provenance

Audited **`<branch>` @ `<sha>` — <version>**, on a clean `git archive` export rather than a
working tree, so nothing uncommitted could colour the read. Excluded: `*.g.dart`, `l10n/`,
`build/`. Every number is measured, not estimated:

| Measurement | at the audit (`<sha>`) | on `<branch>` @ `<sha>` |
|---|---|---|
| <gate> | <output> | <output — the re-measure column, added before remediation starts> |

## The score

| Axis | Was | Predicted | **Measured after** | What actually moved it |
|---|---|---|---|---|
| **SOLID** (SRP · OCP · LSP · ISP · DIP) | | | | finding ids |
| … | | | | |
| **Overall** | | | | |

**Where the measured score parts from the prediction, and why.** <The honest paragraph. This is
the point of re-scoring.>

**Axes that deliberately stop short of 5.** <Ceiling notes, with the constraint that caps each.>

**Priced trades this plan does not move.** <Scored below 5 on purpose; what the trade buys and
where that is documented.>

## What is already exceptional

Named because the instinct on an audit is to "improve" something load-bearing.

- **<Property>.** <Why it is that way, and what breaks if someone "improves" it.>

## Findings

| # | Severity | Finding | Closed by |
|---|---|---|---|
| `finding-1` | 🚨 high | **<One-line claim.>** <Measured evidence, file:line, and what it costs.> | phase N |
| `finding-2` | medium | … | **not planned** — see § Deliberately not doing |

## Phase N — <name>

**Why here:** <what it makes safe for the phases after it>.

- **N.1** <task — Files · Spec · Acceptance, per `execution-planning` § Task anatomy>
- **N.2** …

## Device verification — phase N ⭐

Run on <device + build id>. Mocked channels prove none of this; every row was forced for real.

| # | Forced how | Result |
|---|---|---|
| `verification-1` | <exact command / taps> | ⭐ <what a pass looked like> |

**Not device-verifiable, deliberately skipped:** <what, and why it is not worth a pass.>

## Open decisions

Everything below was deferred rather than guessed. **Recommendation first in every row.**

| # | Decision | Recommended | The alternative |
|---|---|---|---|
| `decision-1` | <the call, with the measurement behind it> | **<recommendation>** — <why> | <the alternative, stated fairly> |

**Actions only the operator takes:** <version marker commits, fast-forwarding a frozen branch.>

## Deliberately not doing

Recorded so none is re-litigated.

| Item | Why it stands |
|---|---|
| **`finding-N` — <name>** | <why it is not worth a phase> |
```

## Notes on filling it in

- **Ids are word-prefixed and never reused**: `finding-3`, `verification-2`, `decision-1`. Phase
  items are `<phase>.<item>`. Never start a letter series.
- **A finding names the phase that closes it**, or says `not planned` and appears in
  § Deliberately not doing. A finding with neither is an orphan.
- **Corrections stay visible**: ⚠️ *corrected by phase 3 (2026-08-27): the audit's zero-count was
  a measurement error.* Silently editing a wrong claim destroys the document's credibility.
- **Tick honestly, in the same edit that lands the work** — half-built is `⊡` today, not `☐`.
- A published artifact of the same content is an optional second deliverable for reading
  comfort; the committed doc stays the source of truth.
