# Measurement recipes

Every number in an audit is a command's output, **with the command shown in the doc** so the next
reader can re-run it. Flutter/Dart first because it is the live stack; the method above each
recipe is stack-agnostic.

Run them from the project root of a **committed tree or a clean export**:

```bash
git rev-parse --short HEAD                    # the sha the audit is pinned to
git log -1 --date=short --format='%h %ad'     # sha + date for the header
git status --short                            # MUST be empty, or export instead:
git archive HEAD | tar -x -C /tmp/audit-$(git rev-parse --short HEAD)
```

## Size and shape — exclude generated files or every number lies

Generated code (`*.g.dart`, `*.freezed.dart`, `l10n/`, `build/`, vendored deps) inflates counts
and is not code anyone maintains. State the exclusion set in the doc.

```bash
find lib -name '*.dart' ! -name '*.g.dart' ! -path 'lib/l10n/*' | wc -l          # files
find lib -name '*.dart' ! -name '*.g.dart' ! -path 'lib/l10n/*' -print0 \
  | xargs -0 cat | wc -l                                                        # lines
find test -name '*.dart' | wc -l                                                # test files
```

The **test:source line ratio** is the one worth quoting (pray: ~1.26:1). Raw test counts move for
reasons unrelated to quality.

## The gates as they stand today

```bash
flutter analyze                                     # baseline: is it clean right now?
flutter test                                        # "N passed, M skipped" — quote both
dart format --output=none --set-exit-if-changed .   # exit 1 == drift exists
dart format --output=none . | grep -c '^Changed'    # HOW MANY files drift
```

Formatter drift as a **fraction** (`154 of 344`) is the number that means something — an absolute
count grows with the repo and hides a stable percentage.

## Sizing a stricter lint config before proposing it

Never propose a lint config without measuring the work it creates. Copy the candidate config in,
run the analyzer, and **classify the hits** — substantive vs pure style, `lib/` vs `test/`:

```bash
cp analysis_options.yaml /tmp/analysis_options.bak
# edit in the candidate analyzer: strict-casts, strict-inference, strict-raw-types, ...
flutter analyze > /tmp/strict.txt; grep -c '•' /tmp/strict.txt
awk -F' • ' '{print $NF}' /tmp/strict.txt | sort | uniq -c | sort -rn   # by rule
cp /tmp/analysis_options.bak analysis_options.yaml
```

Then say in the finding **which rules you are deliberately leaving off and why** — in pray, two
noisy rules accounted for 118 of 148 hits and bought nothing, so the real number was ~23.

## Layering and coupling

The shell version is for *sizing*; the deliverable is an executable test (SKILL.md § 3).

**Match the import style the project actually uses.** A `package:` grep on a codebase that
imports relatively returns a confident zero. Both naive forms below were re-run on pray while
writing this file and **both gave the wrong answer**:

```bash
# WRONG on a relative-import codebase — returns 0 with 20 real edges present
grep -rn "^import 'package:<app>/features/" lib/features
# WRONG — 17 hits, all constructor declarations in the Impl's own file
grep -rEn "\b[A-Z][A-Za-z]*Impl\(" lib --include='*.dart' | grep -v service_locator
```

```bash
# cross-feature edges, relative imports (a sibling ../<feature>/ is the edge)
grep -rn "^import '\.\./" lib/features --include='*.dart' \
  | grep -vE "\.\./\.\./(core|data|services|shared|l10n)/"
# widget -> db
grep -rn "data/db/" lib/features --include='*.dart'
# Impl constructed outside DI, excluding each Impl's own declaration
grep -rEn "\b[A-Z][A-Za-z]*Impl\(" lib --include='*.dart' \
  | grep -v service_locator | grep -v '_impl.dart:'
```

**Do not report the count as "zero" until a test has run it** — the pray audit reported zero
cross-feature edges by eye and a later test found 17. Count first, then freeze the acceptable set
in an allowlist the suite checks in both directions. `test/architecture/layering_test.dart` is the
shape: a `_frozenCrossFeatureSeams` set of 17 `a.dart -> b.dart` strings, a new edge fails, a
stale entry fails, and its sibling literal allowlist is **empty on purpose** with a comment saying
why it should stay that way.

## God classes and long methods

A file over the line limit is not automatically a fat class — fifteen small widget classes in one
file is a full *file*. Classify before reporting.

```bash
find lib -name '*.dart' ! -name '*.g.dart' -print0 | xargs -0 wc -l | sort -rn | head -25
grep -c 'class ' <the-long-file>        # many classes => full file, not a god class
```

For method bodies, the honest signal is **non-`build()` bodies over ~100 lines** — find them with
an editor/LSP outline rather than a regex, and name them individually.

## Design-system fidelity

Count raw literals *and* how many already conform — a scale being followed by hand scores very
differently from no scale at all.

```bash
grep -rhoE 'SizedBox\((width|height): [0-9]+' lib | grep -oE '[0-9]+$' \
  | sort -n | uniq -c | sort -rn                     # the histogram IS the scale
```

If most values land on one grid, the finding is *"the scale has no name"*, not *"there is no
scale"* — and the remediation is transcription, not design.

## Failure handling

```bash
grep -rn 'catch (_)' lib --include='*.dart' | wc -l          # bare
grep -rnE 'on [A-Z][A-Za-z]*Exception' lib | wc -l           # typed
grep -rn 'FlutterError.onError\|PlatformDispatcher.instance.onError' lib
grep -n 'await setup\|runApp' lib/main.dart                  # is launch guarded?
```

A raw bare-catch count is misleading on its own: read each one. In pray all seven were genuine
best-effort cleanup with a comment saying so, and the real finding was **above** them — nothing
installed at the top level, and an unguarded `await` in `main()` that produced a black screen.

## Dependency injection and contracts

```bash
grep -rn 'sl<' lib/features --include='*.dart' | wc -l       # locator sites in UI
ls lib/services/contracts/*.dart | wc -l                     # contracts
grep -rn 'schemaVersion' lib/data/db/*.dart                  # schema version vs tested migrations
```

## Other stacks

Same method, different commands: `eslint --max-warnings=0` / `prettier --check .` / `tsc --noEmit`
/ `npm test`; `ruff check` / `black --check` / `pytest -q`; `clang-tidy` / `clang-format --dry-run
-Werror`. The rule is identical — **quote the command, quote its output, exclude generated code,
and prefer a check that can run in CI over a count you did by hand**.
