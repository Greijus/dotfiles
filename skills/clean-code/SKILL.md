---
name: clean-code
description: Use this skill whenever writing a new function, class, or feature, making an architecture or "should I split this" call, or writing/reviewing unit tests and CI setup in any GenX Labs project. Covers SOLID principles with smell→fix guidance, the minimal-comment rule, the test-per-function discipline, and the GitHub Actions CI template that gates merges. Trigger for any new code being written, architecture review, test writing, or CI pipeline changes.
---

# clean-code

Cross-language discipline for maintainable, testable code. Applies to every stack; language-specific style still lives in `flutter-mvp` (or a future web skill).

## Comments

Self-explanatory names and small functions eliminate most comments. When one is genuinely needed:
- Explain WHY (a constraint, a workaround, a non-obvious tradeoff) — never WHAT.
- Max 1–2 lines. If it needs more, the code is the problem — refactor instead of documenting around it.
- No commented-out code, no restating the function name in prose.

## SOLID

Five smells to catch during implementation or review — not a checklist to prove upfront.

- **Single Responsibility** — one reason to change. *Smell:* the name has "and" in it, or a change for reason A also touches code reason B depends on. *Fix:* split along the reasons for change.
- **Open/Closed** — extend with new code, don't edit already-tested paths. *Smell:* a `switch`/`if-else` chain that grows every time a case is added. *Fix:* polymorphism or a strategy map keyed by the varying case.
- **Liskov Substitution** — a subtype must be swappable for its base type with no surprises. *Smell:* an override that throws, no-ops, or narrows what the base type promised. *Fix:* the contract was wrong — split the interface instead of special-casing the subtype.
- **Interface Segregation** — small, focused interfaces over one fat one. *Smell:* an implementer stubs out methods it never uses. *Fix:* split the interface along actual usage.
- **Dependency Inversion** — depend on abstractions; inject dependencies instead of reaching for a global/singleton or constructing a concrete dependency inline. *Smell:* a class can't be unit-tested without a real database/network/widget tree. *Fix:* pass the dependency in and let the caller wire the concrete type.

## Testing

- Every new function or feature ships a unit test in the same change — not a follow-up task.
- Test behavior, not implementation: name tests after what they verify (`returns empty list when no matches`), not the method they call.
- Cover the edge cases and error paths that would actually break in production, not a coverage percentage.
- Dart: `test/` mirrors `lib/` — `lib/features/prayer/prayer_controller.dart` → `test/features/prayer/prayer_controller_test.dart`.
- Can't unit-test a function without a real device/network/database? That's the Dependency Inversion smell above — fix the design, don't skip the test.

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

Dart/Flutter style and widget rules → `flutter-mvp` skill. Commit/branch/PR mechanics → `git-workflow` skill.
