---
name: flutter-mvp
description: Use this skill whenever working on Flutter mobile apps under GenX Labs — scaffolding a new app, adding features, reviewing code, fixing UI defects, or making architectural decisions. Covers project layout, Effective Dart style, the MVP-discipline rules (no premature backend, no premature billing, no premature CI/CD), the before-calling-UI-done device checklist (font scale, themes, contrast, animations), binary-asset and launcher-icon rules, and the documentation and code-quality bar. Trigger for any task involving Dart files, pubspec.yaml, Flutter widgets, theming, layout or text-scale problems, app icons and image assets, or app architecture decisions.
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

## Widget rules of thumb

- `const` everywhere valid.
- Stateless first; `StatefulWidget` only when the widget owns its own state.
- No business logic in `build()` — controllers/notifiers own logic.
- Theme via `Theme.of(context)`, never hardcoded colors (all three app themes depend on this).
- Every `IconButton` gets a `tooltip`; every meaningful `Image` gets a `semanticLabel`.
- **Shared brand widgets style themselves** — no caller-supplied color or tint parameter. A tint a caller can pass is a tint a caller can get wrong.
- **A widget that must hold a shape re-asserts its own constraints.** A stretching parent hands down tight constraints that silently override yours — that is how a circle ships as an oval.
- **Every startup- or navigation-gating `await` gets a catch, a timeout, and a fallback route.** A catch alone is not enough: a wedged database isolate returns a future that neither resolves nor throws. And check that error *reporting* cannot break the recovery it exists to explain — `FlutterError.reportError` asserts on async-gap stacks.

## Before calling UI done

Device-only defects were the largest bug class on pray-app, and widget tests see none of it. Run this list before you claim a screen is finished.

- **Font scale 1.5 and 2.0** on every new or changed screen and dialog. Layouts that pass at 1.0 often work only by incidental whitespace — a gapless `Row` looks deliberate until the label grows into its neighbour. Dialogs must scroll, not clip. *Truncated navigation labels shipped in a public beta simply because nothing had ever been looked at above the default scale.*
- **Every theme**, not the one you developed against.
- **The smallest size the widget actually renders at** — a three-stop gradient cannot resolve in 20 px.
- **Contrast fixes carry numbers.** Name the target ratio, measure the candidates, and pin every text/background pair in a contrast test. An unmeasured "make it lighter" overshoots — one panel went dark → white → finally right over three rounds. A pair that passes numerically can still *read* wrong, so look at it on the device too.
- **Animations are bounded and reduced-motion-static.** An unbounded `repeat()` blocks every `pumpAndSettle`. Overlay content goes last in the `Stack`, never under a `showDialog` barrier. "The controller is running" is not evidence that anything is visible.

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
4. Add `analysis_options.yaml` extending `package:flutter_lints/flutter.yaml`.
5. `git init` and stage the scaffold; hand off to the operator to commit as `chore(init): scaffold flutter project` (see `git-workflow` skill).
6. Add a `CLAUDE.md` that routes to the dotfiles `CLAUDE.md` plus project-specific context.
7. **Give each build variant its own `applicationId`** (a `.dev` suffix on debug) and gitignore the signing config — do this at scaffold time, not at beta 4. The operator dogfoods on a personal device; without separate install identities a routine `flutter run` uninstalls the dogfood app and takes its real data with it. *That is not hypothetical — it cost a real prayer history.* Verify schema migrations on a genuinely upgraded install, never by uninstall/reinstall.

## Not covered here

Git workflow → `git-workflow` skill. Figma translation → `figma-to-flutter` skill. SOLID, testing, bug-fix discipline → `clean-code` skill. Proving it on hardware → `device-verification` skill. Backend/Supabase → not yet a skill.
