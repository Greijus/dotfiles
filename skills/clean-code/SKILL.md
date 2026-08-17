---
name: clean-code
description: Use this skill whenever writing a new function, class, or feature, FIXING A BUG, making an architecture or "should I split this" call, or writing/reviewing unit tests and CI setup in any GenX Labs project. Covers SOLID principles with smell→fix guidance, the minimal-comment rule, the blast-radius discipline for bug fixes, the test-the-effect rule, and the GitHub Actions CI template that gates merges. Trigger for any new code being written, any bug fix or defect investigation ("fix this", "it's broken", "this doesn't work", a device-test finding, a fix round), architecture review, test writing, or CI pipeline changes.
---

# clean-code

Cross-language discipline for maintainable, testable code. Applies to every stack; language-specific style still lives in `flutter-mvp` (or a future web skill).

## Comments

Self-explanatory names and small functions eliminate most comments. When one is genuinely needed:
- Explain WHY (a constraint, a workaround, a non-obvious tradeoff) — never WHAT.
- Max 1–2 lines. If it needs more, the code is the problem — refactor instead of documenting around it.
- No commented-out code, no restating the function name in prose.

**A comment that states behavior is a contract** — back it with code and a test, or delete it. When a fix changes behavior, the comment describing the old behavior is part of that diff. And a comment that contradicts its code is a bug report: read the two against each other when diagnosing. *A lifecycle comment promised "…or a new day begun" that nothing implemented, and a highlight commented "the blurred white disc" was painted 30% black — both were the diagnosis, sitting in plain sight.*

## SOLID

Five smells to catch during implementation or review — not a checklist to prove upfront.

- **Single Responsibility** — one reason to change. *Smell:* the name has "and" in it, or a change for reason A also touches code reason B depends on. *Fix:* split along the reasons for change.
- **Open/Closed** — extend with new code, don't edit already-tested paths. *Smell:* a `switch`/`if-else` chain that grows every time a case is added. *Fix:* polymorphism or a strategy map keyed by the varying case.
- **Liskov Substitution** — a subtype must be swappable for its base type with no surprises. *Smell:* an override that throws, no-ops, or narrows what the base type promised. *Fix:* the contract was wrong — split the interface instead of special-casing the subtype.
- **Interface Segregation** — small, focused interfaces over one fat one. *Smell:* an implementer stubs out methods it never uses. *Fix:* split the interface along actual usage.
- **Dependency Inversion** — depend on abstractions; inject dependencies instead of reaching for a global/singleton or constructing a concrete dependency inline. *Smell:* a class can't be unit-tested without a real database/network/widget tree. *Fix:* pass the dependency in and let the caller wire the concrete type.

## Design seams

A seam is an abstraction placed on purpose so the concrete side can be swapped without touching callers — the proactive form of Dependency Inversion. Put one exactly where reality changes under you:

- **Externals the tests can't run** — the clock, randomness, network, notifications, the asset/file bundle. Inject them; ship a `Noop`/fake default so tests and headless builds stay green. *Time and randomness are dependencies, not ambient facts — `DateTime.now()`/`Random()` reached for inline is the DIP smell in disguise.*
- **A policy that will flip later** — feature availability, entitlements, remote config. Route every check through one interface, resolve it trivially now, swap the impl later.
- **A rule with more than one caller** — extract it into a single place (a pure helper or the owning service's method) and call it; never reimplement it. Two copies that *drift* — same rule, different behavior — are worse than duplication: they're a latent correctness bug.

When is a seam earned? When you can **name the second implementation** — a fake for tests, a paid tier, a second platform. One real use today plus a *named* future one justifies the interface; "might need it someday" does not — that's speculative structure (`flutter-mvp`), so build the concrete class and extract the seam when the second caller actually appears. Tests count as a named second caller.

Pure business math (weighting, thresholds, date rules) belongs in a **stateless helper**, not inlined in a service that also does I/O — one reason to change, and testable without a database.

**A fake is dumb state, not a second implementation.** A fake exists so a test can run without the real dependency — it must never re-derive the rules. *Smell:* a behavioral change touches both `<thing>_impl` and `fake_<thing>`, and a `fake_<thing>_test` mirrors the real suite. *Fix:* extract the rule into a pure core both call, or back the fake with the same derivation over an in-memory store. On pray-app a 261-line fake re-implemented the challenge rules on its own state model, so a single rule change had to be written twice and pinned twice — a tax charged on every future change, and two answers free to drift apart.

## Testing

- Every new function or feature ships a unit test in the same change — not a follow-up task.
- Test behavior, not implementation: name tests after what they verify (`returns empty list when no matches`), not the method they call.
- Cover the edge cases and error paths that would actually break in production, not a coverage percentage.
- Dart: `test/` mirrors `lib/` — `lib/features/prayer/prayer_controller.dart` → `test/features/prayer/prayer_controller_test.dart`.
- Can't unit-test a function without a real device/network/database? That's the Dependency Inversion smell above — fix the design, don't skip the test.

### Assert the effect, not the artifact

Every bug that reached a device on pray-app and *should* have been caught by an existing test was missed for one of these reasons. A test that asserts the artifact — a widget exists, a value was written, the happy path returned — proves nothing a user can feel.

- **Pin the user-visible outcome:** pixels actually painted, the read path's behavior changing, the forbidden call count staying at zero. *A celebration animation shipped invisible — it rendered beneath a dialog's barrier scrim — with green tests that only asserted the widget was in the tree.*
- **Every flag you write gets a test on its read path.** A written-never-read field is dead code with a switch attached: the setting "works" and changes nothing. *Two settings shipped purely decorative this way.*
- **Every `await` that gates startup or navigation gets a failure-path test** — error, timeout, and the fallback route. A screen whose only exit is a happy-path `await` is a hang waiting to happen.
- **Test past the boundary, not just up to it** — day N+1 of an N-day target, the second event on the same day, the re-fire. *Two latent bugs lived past day 21 because no test ever went there.*
- **Data-driven logic runs over the real shipped corpus**, not a synthetic sample. *Three of 122 real verses carried their own quotation marks; no handwritten fixture did.*
- **Mutation-verify a guarantee that must never break** (privacy, money, safety): delete the guarantee and prove the test goes red. Otherwise you have a test that passes for the wrong reason.

## Fixing a bug

A careless fix relocates a defect instead of closing it. On pray-app, *every* device-test round found bugs in the previous round's fixes — the single most expensive pattern in the project.

- **Reproduce, then root-cause, then fix.** No fix lands on an unreproduced defect. If it won't reproduce, close it with the evidence and a recipe for catching it next time — not a shrug.
- **One symptom can hide two questions.** Answer all of them before fixing any. *A P0 report was "why did the splash appear" AND "why did it hang"; only the second was a defect.*
- **Sweep the blast radius before calling it fixed.** What you found is one instance of its cause:
  - *Replaced a hardcoded constant?* Grep the feature for every other instance. Live arithmetic only — comments and content strings are not survivors, and one hit is usually a deliberate mention you would be wrong to "fix". *A fix corrected "Day 34 of 21" in the label and missed the same literal in the progress bar twenty lines below; the next round found it.*
  - *Fixed a shared widget for one screen?* Fix it **in the widget** so every call site heals. A per-call-site patch guarantees the next screen ships the same bug. *One shared glyph took four rounds this way.*
  - *Fixed one surface?* Check the sibling surface with the same shape before closing — the same dialog shape, the same affordance on another screen.
- **A subsystem that has cost a surprise fix twice earns a written map** — grepping the blast radius fresh every round is how the second-order hit gets missed a third time. → `blast-radius-map`.
- **The regression test ships in the same commit**, asserting the effect (above).
- **Update the comment, doc, or spec that described the old behavior in the same diff.**
- **One owner per defect.** Two open reports with one suspected cause are one fix — otherwise the same defect gets fixed twice and shipped once.
- **A fix is done when it survives the device, not when it merges** → `device-verification`.

## CI/CD

CI gates every merge to `main` (already required — see CLAUDE.md's "What NOT to Do"). CD stays manual until real users exist (`COMPANY.md`).

Minimal GitHub Actions workflow — lint + test, nothing else, until a real signal demands more:

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request, push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - run: flutter analyze
      - run: flutter test
```

Swap the two `flutter` steps for the stack's equivalent (`npm run lint` / `npm test`) on non-Flutter projects.

## Not covered here

Dart/Flutter style and widget rules → `flutter-mvp` skill. Commit/branch/PR mechanics → `git-workflow` skill. Proving a fix on real hardware, and running a device-test fix round → `device-verification` skill.
