---
name: system-design
description: DORMANT CHARTER — not yet an active skill. Do NOT trigger for ordinary architecture, SOLID, "should I split this", or Flutter-layout questions — those belong to clean-code, flutter-mvp, and execution-planning. Trigger ONLY when the operator explicitly crosses a trip-wire: adding the first backend/service boundary, splitting the codebase into a second package/module, introducing a sync or offline-conflict layer, or asking to activate this skill / start an ADR log. Until then it stays a charter, not a rulebook.
---

# system-design

> **Status: NOT ACTIVE — charter only.** This file reserves the name and records intent. Do not treat its contents as house rules yet; there is nothing to apply until the trip-wire fires.

## Why dormant

Whole-system architecture rules written today would generalize from a single instance each — the speculative-structure smell `flutter-mvp` warns against. One backend, one package, one storage model is not a pattern. Wait for the second.

## The four zoom levels (where this sits)

- Statement/function → CLAUDE.md Universal Principles
- Class/file (one job, testable seams) → `clean-code`
- Stack layout (where a Flutter file goes) → `flutter-mvp`
- Build structure (parallel lanes, frozen contracts) → `execution-planning`
- **Whole running system (arrows between components, and *why*) → this skill**

`clean-code` governs the *inside* of a component; `system-design` governs the *boundaries between* them — decisions no single file owns and that are expensive to reverse.

## Trip-wire — activate when the FIRST of these lands

- A **backend / external-service boundary** (e.g. Supabase) — shared state leaves the device.
- A **second package or module** — the dependency direction between them now needs a rule.
- A **sync / offline-conflict layer** — "which write wins" becomes a real question.
- The operator asks to **start an ADR log** or build this skill out.

Any one of these means n≥2 on a system-level concern. Then write the skill.

## What it will cover (when activated)

- **Decision records (ADRs).** Lightweight "chose X over Y because Z, on date D." Write these FIRST — retroactively capture the decisions already made below, so they stop being relitigated.
- **Boundaries & the dependency rule.** Module/package split; dependencies point inward (UI → services → data, never back). When a folder earns its own package.
- **Storage & state model.** Event-log vs. mutable rows; what's stored vs. derived; migration discipline.
- **External boundaries / "one door" rules.** All-X-goes-through-one-service seams; provider-swap points; the backend boundary.
- **Cross-cutting concerns as a system.** i18n, feature gating, failure/fallback strategy, privacy/data-egress.
- **Offline/sync strategy.** Only once a backend exists.

## Seed material already in pray-app

Concrete starting points for the future author — each currently an n=1 decision:

- **Event sourcing:** `prayer_completions` is an append-only log; challenge counters are *derived* from it, not stored.
- **One-door LLM boundary:** all generation goes through `PrayerGenerationService`.
- **Component seams:** `FeatureGate`, `ReminderScheduler`, `ThemeService` — swappable impls behind abstractions (see `clean-code` § Design seams).
- **Guardrails as architecture:** WEB-only scripture, curated-verse injection, local-first, "no answer/prayer text leaves the device except the Gemini prompt."

## Until active

System-level concerns route to their current homes: component seams → `clean-code`; layering/layout → `flutter-mvp`; build orchestration → `execution-planning`; project-specific decisions → the project's `docs/` and `CLAUDE.md`. When activating, keep the name **`system-design`** — `architecture` collides with `clean-code`'s trigger.
