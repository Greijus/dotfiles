---
name: flutter-mvp
description: Use this skill whenever working on Flutter mobile apps under GenX Labs — scaffolding a new app, adding features, reviewing code, fixing UI defects, or making architectural decisions. Covers project layout, Effective Dart style, the hardened `analysis_options.yaml` baseline (and the lint rules deliberately left off), the MVP-discipline rules (no premature backend, no premature billing, no premature CI/CD), the before-calling-UI-done device checklist (font scale, themes, contrast, animations), binary-asset and launcher-icon rules, the localization-ready-from-day-one checklist (one shipped-locale list, locale-keyed content, per-locale rules for any prose check, a test-only pseudo-locale), and the documentation and code-quality bar. Trigger for any task involving Dart files, pubspec.yaml, Flutter widgets, theming, layout or text-scale problems, app icons and image assets, or app architecture decisions.
---

# flutter-mvp

GenX Labs' Flutter house style: ship MVPs fast without accruing structure that isn't earned yet.

## Stage-appropriate discipline

Default to the simplest thing that works. Add structure only when a real signal — a user complaint, a recurring bug, a slow deploy — demands it, never speculatively.

- No backend until the app needs server state (local SQLite/Hive/Drift is fine).
- No paid tier until retention is proven — stub the paywall, don't build it.
- No CI/CD beyond GitHub Actions running `flutter analyze` + `flutter test`.
- No state-management library until `StatefulWidget` + `ValueNotifier` can't carry the weight; then Riverpod or Bloc.

## Project layout

```
<app-name>/
├── lib/
│   ├── main.dart
│   ├── app.dart              # MaterialApp + theme + routing
│   ├── core/                 # cross-feature: theme, utils, constants
│   ├── data/                 # local persistence, API clients (later)
│   ├── features/<feature>/   # one folder per feature
│   │   ├── <feature>_screen.dart
│   │   ├── <feature>_controller.dart
│   │   └── widgets/
│   └── shared/                # widgets used in 2+ features
├── test/
├── pubspec.yaml
├── CLAUDE.md                  # routes to the dotfiles CLAUDE.md via `@` import
└── README.md
```

Move a widget into `shared/` only when a second feature actually needs it.

## Code quality bar

- Zero warnings from `flutter analyze`. Suppress a false positive inline with a reason — never globally in `analysis_options.yaml`.
- Effective Dart naming/formatting/idioms; `dart format` on save.
- Max 3 levels of indentation per function body — guard clauses over nested `if`s.
- DRY after 3 repetitions, not 2.
- DartDoc on every public API.

### The analyzer baseline

`flutter create` writes a stock `analysis_options.yaml` with every example commented out and **no
`analyzer:` section at all** — strict casts, inference and raw types off. Ship this instead, from
day one; retrofitting it onto a grown app was a whole audit phase on pray:

```yaml
include: package:flutter_lints/flutter.yaml

analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true

linter:
  rules:
    unawaited_futures: true
    avoid_dynamic_calls: true
    prefer_final_locals: true
    always_declare_return_types: true
```

**Deliberately left off:** `cascade_invocations` and `directives_ordering` — on pray they were
118 of 148 hits and bought nothing. `use_build_context_synchronously` is already on via
`flutter_lints`; re-adding it is noise. Turning this on late is ~25 real fixes on a 30k-line app,
mostly untyped `MaterialPageRoute`s and genuinely unawaited futures — **read those three or four
unawaited navigation calls rather than reflexively wrapping them in `unawaited()`.**

## Widget rules of thumb

- `const` everywhere valid.
- Stateless first; `StatefulWidget` only when the widget owns its own state.
- No business logic in `build()` — controllers/notifiers own logic.
- Theme via `Theme.of(context)`, never hardcoded colors (all three app themes depend on this).
- Every `IconButton` gets a `tooltip`; every meaningful `Image` gets a `semanticLabel`.
- **Shared brand widgets style themselves** — no caller-supplied color or tint parameter. A tint a caller can pass is a tint a caller can get wrong.
- **A widget that must hold a shape re-asserts its own constraints.** A stretching parent hands down tight constraints that silently override yours — that is how a circle ships as an oval.
- **A bounded page lays itself out; only a feed is lazy.** `ListView(children: [...])` builds a `SliverList`, which lays out only what is near the viewport and **extrapolates `maxScrollExtent` from the average height of the children it happens to have laid out**. Where children are uneven — spacers beside a tall card beside a section that renders to nothing — that estimate is wrong, and at the *bottom* of the page it collapses: `pixels` is left past the new extent, Flutter corrects the offset down, and a slow drag gains ten pixels and loses seventy. A fling outruns the collapse, so it reaches you as *"it only scrolls if I flick"* and looks like a gesture bug, which is the wrong thing to go looking for. Use **`SingleChildScrollView` + `Column`** for any page with a fixed, countable set of sections — settings, forms, onboarding, detail screens — and keep `ListView`/`.builder` for lists that are genuinely unbounded or uniform. Swapping it, mind that `ListView` stretches children to the viewport width and a `Column` centres them: `crossAxisAlignment: stretch`. *This shipped. It was latent for months and surfaced only when one section was removed and a zero-height one added, which moved the average — so the commit that exposed it was not the commit that caused it, and bisecting found a commit but not a cause.*
- **Every startup- or navigation-gating `await` gets a catch, a timeout, and a fallback route.** A catch alone is not enough: a wedged database isolate returns a future that neither resolves nor throws. And check that error *reporting* cannot break the recovery it exists to explain — `FlutterError.reportError` asserts on async-gap stacks.

## Before calling UI done

Device-only defects were the largest bug class on pray-app, and widget tests see none of it. Run this list before you claim a screen is finished.

- **Font scale 1.5 and 2.0** on every new or changed screen and dialog. Layouts that pass at 1.0 often work only by incidental whitespace — a gapless `Row` looks deliberate until the label grows into its neighbour. Dialogs must scroll, not clip. *Truncated navigation labels shipped in a public beta simply because nothing had ever been looked at above the default scale.*
- **Every theme**, not the one you developed against.
- **The smallest size the widget actually renders at** — a three-stop gradient cannot resolve in 20 px.
- **Contrast fixes carry numbers.** Name the target ratio, measure the candidates, and pin every text/background pair in a contrast test. An unmeasured "make it lighter" overshoots — one panel went dark → white → finally right over three rounds. A pair that passes numerically can still *read* wrong, so look at it on the device too.
- **Animations are bounded and reduced-motion-static.** An unbounded `repeat()` blocks every `pumpAndSettle`. Overlay content goes last in the `Stack`, never under a `showDialog` barrier. "The controller is running" is not evidence that anything is visible.
- **Scroll every page to its bottom and drag back up slowly.** The boundaries are where scrolling breaks, and a flick hides it — a page can be perfect in open water and unusable at the end. Do it at the content the *user* has, not the default: an expanded section or an extra row changes the child heights the extent is computed from. Watch the page, not just the offset. A widget test will not see any of this, and neither will a fast synthetic swipe (`device-verification` § Verify the mechanism).

## Binary assets

Assets have physics no widget test touches. Verify properties mechanically before wiring one in — never trust the file.

- **Check real alpha** by compositing over dark: a grey-and-white checkerboard baked into opaque pixels looks transparent in a light viewer. Check dimensions and corner pixels per density while you are there.
- **Android adaptive icons reserve the outer ~33%** for the launcher mask. Watch for stacked insets — a generator's default inset applied on top of a master that already frames its own safe zone crops the artwork twice.
- **Never hand-edit a generated set.** Fix the master or the generator config and regenerate.
- **A master downscaled more than ~3× in a single decode step aliases** — ship dpr variants instead. When an image looks wrong at size, suspect the master, not the widget.
- **A README records which master feeds which surface**, or the next regeneration starts from the wrong file.
- **Art direction settles on sight, and only the operator's.** Get their eyes on a cheap preview *before* building any derivation pipeline. *One pipeline was built, gated green against 570 tests, and deleted the next day because the result looked bad — aesthetic acceptance cannot be delegated to a test suite.*

## Scaffolding a new app

1. Create `<app-name>/` as a sibling of the dotfiles repo under the workspace root (the root differs per machine — see CLAUDE.md § Project Layout).
2. `flutter create --org com.genxlabs --platforms android` (add ios/web only when explicitly scoped).
3. Lay out the structure above with empty placeholders — no speculative code.
4. Add `analysis_options.yaml` — the hardened baseline in § Code quality bar, not the stock one.
5. `git init` and stage the scaffold; hand off to the operator to commit as `chore(init): scaffold flutter project` (see `git-workflow` skill).
6. Add a `CLAUDE.md` that routes to the dotfiles `CLAUDE.md` plus project-specific context.
7. **Give each build variant its own `applicationId`** (a `.dev` suffix on debug) and gitignore the signing config — do this at scaffold time, not at beta 4. The operator dogfoods on a personal device; without separate install identities a routine `flutter run` uninstalls the dogfood app and takes its real data with it. *That is not hypothetical — it cost a real prayer history.* Verify schema migrations on a genuinely upgraded install, never by uninstall/reinstall.

## Localization-ready from day one

Ship one language; build so the second is a content job. "i18n-ready" means `gen_l10n` **and**
all of this — the UI half is enforced by the compiler, the content half only by what you set
up here. *pray-app learned it the slow way (`docs/plans/localization-infrastructure.md`):
`gen_l10n` from Phase 0 and a content path helper that always returned `en`; ten weeks later
four prose checks, the app-written opening, the reference display and 83 tests were English-only.*

- **One `shippedLocales` list, one resolver.** Stored preference → device locale → default,
  resolved in one function that the UI, the content loader, notifications and any model prompt
  all read. `supportedLocales` derives from the list, never from which ARBs happen to exist.
- **Content under `assets/content/<locale>/`, all-or-nothing.** A locale ships complete or not
  at all; a completeness test says exactly what is missing. No per-asset fallback. Asset paths
  are resolved per call — a `static final _path = …` caches the first locale for the process.
- **Prose is content, never a Dart literal.** Anything a user reads comes from an ARB or a
  content file; a lint over `lib/` for `Text('…')`, `label:`, `title:`, `hintText:` with a
  shrink-only allowlist of dev screens.
- **Any code that matches prose reads a per-locale rules table.** Regexes for an address, a
  closing phrase, a forbidden register, a word tokenizer, a word-count target — data keyed by
  locale, English's entry moved in verbatim, a test that every shipped locale has one. Unicode
  classes (`\p{L}`, `unicode: true`), never `[a-z]`.
- **Canonical keys with a display map.** Ids, tags and lookup keys (a Bible book name, a theme
  tag) stay in one canonical form in every locale; what the user sees goes through a per-locale
  label file. A key that is also displayed cannot be translated in place.
- **A test-only pseudo-locale, from day one.** Generate `xa` from English — every display
  string accented and padded 40 %, every key untouched — into `test/`, never into assets, and
  run every content, resolver, display and prose-check test against it. It fails the day
  someone hardcodes `en`, caches a path, adds an English regex to a check, or prints a key.
  `gen_l10n`'s `untranslated-messages-file` gated in CI covers the ARB half.
- **Word counts are per language.** A Finnish prayer says the same thing in ≈70 % of the words;
  any length floor or target carries a per-locale factor.

## Not covered here

Git workflow → `git-workflow` skill. Figma translation → `figma-to-flutter` skill. SOLID, testing, bug-fix discipline → `clean-code` skill. Proving it on hardware → `device-verification` skill. Backend/Supabase → not yet a skill.
