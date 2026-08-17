---
name: blast-radius-map
description: Write and maintain a short "if you change X, also check Y" map for a subsystem that has already cost a surprise fix more than once. Produces one object card per moving part (Shape, Connected to, Hits/Does not hit, Surfaces, See — cited to a file and dated) plus an effects index. NOT for a single bug fix — that's clean-code's blast-radius sweep. NOT for planning a build — that's execution-planning. Trigger only on "map <subsystem>", "what would changing X hit", "this keeps breaking in surprising places", or when a fix round finds a second/third regression in the same feature.
---

# blast-radius-map

A tiny, distilled slice of Interpretable Context Methodology's "system map" form — scoped to exactly the part of it that tested true on this project: recording second-order effects a subsystem has, so the next fix doesn't rediscover them by grepping or by breaking again.

## When to reach for this — and when not to

Reach for it only when a subsystem has **already cost a surprise fix twice**. The pray-app Focus Mode grayscale logic is the canonical example: three corrective commits in a row (Z10, Z11, Z12), the last one caused by a code path in an unrelated file (`ZenRuleGrayscale.kt`) waking up because of a permission grant made by a *different* toggle's flow. That is exactly the kind of hit a map exists to record.

Do **not** reach for it:
- On a normal bug fix — `clean-code`'s "sweep the blast radius" bullet (grep the constant, heal the shared widget, check the sibling surface) already covers a one-off.
- To document a subsystem pre-emptively "because it might get confusing." Three real surprises beat seven imagined ones — this is scaffolding, not architecture, and it rots the moment nobody re-verifies it.
- For a whole app or a whole `lib/` tree. One map per subsystem, made only once that subsystem has earned it.

## Where it lives

One file per subsystem, e.g. `docs/product/<subsystem>-map.md`, next to the spec it maps (`focus-mode.md` → `focus-mode-map.md`). Not a `map/` folder with its own routing catalog — that's ceremony a single-card subsystem doesn't need. Add one line to the project's `CLAUDE.md` doc index pointing at it once it exists.

## The object card

One card per moving part (a class, a service, a flag — not a file if the file holds several). Copy this shape:

```markdown
### <Name> — <one sentence: what it is and why this shape>

**Universe:** live | leftover | ghost
<!-- live = in force, implement/cite against it.
     leftover = present but not the main path; touch only if that path is in scope.
     ghost = named/filed but not wired — a stub, a dead type, a disabled route. Never implement against a ghost. -->

**Shape** — the load-bearing fields/state, cited: `path/to/file.dart:42`

**Connected to** — owns / owned-by / triggered-by, each a link to another card or a file:line

**If you change this**
- Hits: <files/behaviors that break or must change too, each cited>
- Does not hit: <the obvious next guess that is actually wrong — name it so nobody re-checks it>

**Surfaces** — who reads/writes this (which screens, which service, which platform channel)

**See** — the one source file that owns this fact

**Verified:** <date>, <commit sha or branch> — a card claiming `verified` without both is worthless; mark it `stale` instead.
```

## Process

1. **Inventory, don't write cards yet.** List the files the subsystem actually touches (grep by feature keyword across `lib/`, platform channels, tests). Classify each: is it live, leftover, or a ghost like `ZenRuleGrayscale.kt` — present, compiled, but deliberately dead?
2. **One card per moving part**, not per file. Cluster by how you'd ask the question ("what greys the screen") not by folder layout.
3. **Fill Hits/Does not hit from the actual regression history if there is one** — Z12's commit message already states the five-hop chain that broke; that chain *is* the card content, not a re-derivation.
4. **Write the effects index last** — a short list at the top or bottom of the file: "changing the Focus Mode toggle → also open: device-grayscale card, focus-onset-alarm card, DND-access-grant note." It only points at cards; it never restates them.
5. **Re-verify before trusting it.** A stale card with a confident date is worse than no card — if you haven't rechecked the citation this session, don't call it `verified`.

## Walk test

Before trusting a map, check: can someone with no memory of the subsystem open the card and correctly predict the next regression's shape — without opening the source first? If not, the card is missing the one non-obvious link, not more prose.

## Not covered here

A single bug's blast radius → `clean-code` § Fixing a bug. Per-lane "what to read for this task" → `execution-planning`'s Reference/Do-not-load lines. Proving the fix survives the device → `device-verification`.
