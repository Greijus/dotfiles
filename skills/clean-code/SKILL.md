---
name: clean-code
description: Use this skill whenever writing a new function, class, or feature, FIXING A BUG, making an architecture or "should I split this" call, or writing/reviewing unit tests and CI setup in any GenX Labs project. Covers SOLID principles with smell→fix guidance, the minimal-comment rule, the blast-radius discipline for bug fixes, the test-the-effect rule, the enforce-it-don't-document-it disposition that moves any checkable rule into a lint/CI step/test, and the GitHub Actions CI template that gates merges. Trigger for any new code being written, any bug fix or defect investigation ("fix this", "it's broken", "this doesn't work", a device-test finding, a fix round), architecture review, test writing, or CI pipeline changes.
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

## Enforce it, don't document it

A rule that lives only in prose is a rule nothing checks. **This file's own fake-duplication
example is the proof:** it cited a 261-line fake as the worked case, and the file grew to 362
lines anyway, with the rule written down the whole time.

So the default disposition of any rule you are tempted to write down:

- **Expressible as a lint, a CI step, or a test? Move it there.** Layering invariants become an
  import test; a naming or ordering rule becomes an analyzer rule; a token scale becomes a test
  that fails on a raw literal; a lookup table becomes a coverage assertion against its corpus.
- **Freeze the violations you are accepting in an allowlist that fails on new *and* stale
  entries** — a list that can only shrink. An allowlist that merely rejects additions is
  permanent debt with a comment on it.
- **A deferral needs a tripwire.** A hook that returns the only value there is — a locale
  helper that always answers `en`, a feature flag with one state — is not infrastructure; it is
  a stub that *looks* finished, and nothing can ever exercise the path it stands for. Ship it
  with the test that fails the day something bypasses it (a pseudo-locale, a second fake
  tenant, a flag flipped in CI), or the code grows past the recipe and nobody notices.
  *pray-app: the content-locale hook was a one-line constant for ten weeks; three prose checks
  written in that time were English-only, each noting it in a code comment nobody re-read.*
- **A priced trade gets a ratchet.** When a review or audit keeps a trade — a long class, a
  locator call in widgets, a bare catch — freeze its measure in a shrink-only test that reads the
  number from the tree. Raising the frozen number is a commit whose body says why, never a
  silent edit. *pray-app `1.0b11` → `1.0b19`: the rules the first audit made tests drifted by
  zero; the trades it priced in prose (the locator, the god classes, silent catches) all grew,
  and the score fell 4.7 → 4.0.*
- **Prose keeps only the judgement calls** — when to split, what a seam is worth, which trade to
  price. Those cannot be executed, which is exactly why they earn the words.
- Adding a paragraph to a skill that was already ignored repeats the failure. If a rule was
  broken while written down, the fix is a gate, not a rewrite.

Auditing a whole codebase for where this has already happened → `code-audit`.

## Testing

- Every new function or feature ships a unit test in the same change — not a follow-up task.
- Test behavior, not implementation: name tests after what they verify (`returns empty list when no matches`), not the method they call.
- Cover the edge cases and error paths that would actually break in production, not a coverage percentage.
- Dart: `test/` mirrors `lib/` — `lib/features/prayer/prayer_controller.dart` → `test/features/prayer/prayer_controller_test.dart`.
- Can't unit-test a function without a real device/network/database? That's the Dependency Inversion smell above — fix the design, don't skip the test.
- Other sessions may share the checkout: run the suite under the checkout lock, and move to a worktree when it is busy → `device-verification` § Sharing the device and the checkout.

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
- **The commit that exposed a defect is not always the commit that caused it.** A latent fault waits on a *condition* — a content mix, a data volume, a screen size, a setting nobody had on — and the change that finally satisfies it is innocent. So when "it worked in the last build" is true, **bisect to a commit only after a cheap truth table says the fault is in the code and not in the state**: vary one condition at a time across both builds and read the grid. A grid that comes out non-monotonic (old-build-both-ways fine, new build fine one way and broken the other) has already told you the trigger is a condition, and a bisect would have handed you a commit and no cause. *A scroll defect A/B'd as a clean regression between two release candidates; the two builds' difference turned out to be which sections the page contained, and the actual fault had been latent for months.*
- **A subsystem that has cost a surprise fix twice earns a written map** — grepping the blast radius fresh every round is how the second-order hit gets missed a third time. → `blast-radius-map`.
- **The regression test ships in the same commit**, asserting the effect (above).
- **Update the comment, doc, or spec that described the old behavior in the same diff.**
- **One owner per defect.** Two open reports with one suspected cause are one fix — otherwise the same defect gets fixed twice and shipped once.
- **A fix is done when it survives the device, not when it merges** → `device-verification`.

## CI/CD

CI gates every merge to `main` (already required — see CLAUDE.md's "What NOT to Do"). CD stays manual until real users exist (`COMPANY.md`).

Minimal GitHub Actions workflow — lint + test, nothing else, until a real signal demands more. Its few extra lines are the cheap defaults below; each one was paid for in runner minutes on pray-app:

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    # Only what CI checks. Keep docs/plans, trackers and READMEs out — but keep any doc a test reads.
    paths: ['lib/**', 'test/**', 'assets/**', 'android/**', 'pubspec.*', 'analysis_options.yaml', '.github/workflows/**']
  workflow_dispatch:            # "Run workflow": everything, on demand
concurrency:                    # a newer push supersedes the run still going
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30         # ~2× a green run; a dead runner otherwise holds the job for hours
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - run: flutter analyze
      - run: flutter test -j "$(nproc)"   # the default is half the cores: one file at a time on a 2-core runner
```

Swap the two `flutter` steps for the stack's equivalent on non-Flutter projects (`npm run lint` / `npm test`, `ruff` / `pytest`), and set the same concurrency there: Jest `--maxWorkers="$(nproc)"`, pytest-xdist `-n auto`, Gradle `maxParallelForks = Runtime.getRuntime().availableProcessors()`.

**The defaults, and why** (pray-app, October 2026 — 52 push runs, ~830 runner-minutes over two weeks):

- **Run for changes CI checks, not for every push.** 29 of the 52 runs (51% of the minutes) were pushes that changed only plans and release trackers, and with `cancel-in-progress` each one cancelled the code run before it. `on.push.paths` stops both. List what CI reads: the source, the tests, the build files, the workflow, *and any doc a test opens*. Then **enforce the list with a test**: a lint test reads `on.push.paths` from the workflow and fails on any read outside it (pray-app `mobile/test/lint/ci_paths_test.dart`), so the list cannot go stale silently. Caveat: if branch protection *requires* this check, a path-skipped push leaves it pending forever. Either don't require it or add a trivial always-run job with the same name.
- **One trigger per commit.** `on: [pull_request, push]` runs every PR commit twice. A solo repo with no PRs needs `push` only. A PR repo uses `pull_request` plus `push: branches: [main]`.
- **Anything that gates on "CI green at commit X" must accept a skipped commit.** A docs-only commit gets no run, and a push of several commits runs only at its tip. The check takes the newest run on X's first-parent history, provided nothing under `paths` changed since (play-release `ci_run_for`).
- **Concurrency is the suite's lever, not test selection.** On pray-app no file took more than 11 s of an 8-minute suite. Running files on every core cut it to 5–7 min. Running only "the tests near the change" is not offered: there is no reliable impact analysis, and shared code breaks far from the edit.

**When the job grows a heavy build step** (an Android APK/AAB, a Docker image, a web bundle):

- **Run it only when its own inputs changed.** Analyze and the tests already compile the code. An APK adds proof only for Gradle, the manifest, native plugins and — built `--release`, one ABI, debug-signed, with a throwaway value for any secret the build checks — the R8/minified path, so build it when `android/`, `pubspec.*`, the version file or the workflow changed. Gate a code-generator freshness check (regenerate, `git diff --exit-code`) the same way, on the generator's inputs: it costs minutes on every push otherwise. Also build it when the push base can't be diffed (a new branch, a force-push) or on a manual run. Diff `github.event.before..github.sha` after `checkout` with `fetch-depth: 0`. The release build proves the full build anyway before anything ships.
- **Android on hosted runners: free the disk first.** The NDK and CMake install on every run, on a disk the test run has nearly filled. pray-app's last green build ended with **38 MB** free, and every build after it killed its runner. A runner that dies leaves **no log** and holds the job until something cancels it (2 h 18 min once). Before the build:
  `sudo rm -rf /usr/share/dotnet /usr/local/.ghcup /opt/ghc /usr/share/swift /usr/local/share/boost /opt/hostedtoolcache/CodeQL` (took 9.4 → 24 GB free). Print `df -h /` before and after, so the next squeeze shows in the log.
- **Gate it to the branches that ship** (`main`, `rc/*`); lane branches gate on the suite.

A full worked example of all of the above: pray-app `.github/workflows/ci.yml` (round 19).

## Not covered here

Dart/Flutter style and widget rules → `flutter-mvp` skill. Commit/branch/PR mechanics → `git-workflow` skill. Proving a fix on real hardware, and running a device-test fix round → `device-verification` skill.
