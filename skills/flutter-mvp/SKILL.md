---
name: flutter-mvp
description: Use this skill whenever working on Flutter mobile apps under GenX Labs — scaffolding a new app, adding features, reviewing code, or making architectural decisions. Covers project layout, Effective Dart style, the MVP-discipline rules (no premature backend, no premature billing, no premature CI/CD), and the documentation and code-quality bar. Trigger for any task involving Dart files, pubspec.yaml, Flutter widgets, theming, or app architecture decisions.
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
├── CLAUDE.md                  # routes to ~/Projects/dotfiles/CLAUDE.md
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

## Scaffolding a new app

1. Create `~/Projects/<app-name>/`.
2. `flutter create --org com.genxlabs --platforms android` (add ios/web only when explicitly scoped).
3. Lay out the structure above with empty placeholders — no speculative code.
4. Add `analysis_options.yaml` extending `package:flutter_lints/flutter.yaml`.
5. `git init` and stage the scaffold; hand off to the operator to commit as `chore(init): scaffold flutter project` (see `git-workflow` skill).
6. Add a `CLAUDE.md` that routes to `~/Projects/dotfiles/CLAUDE.md` plus project-specific context.

## Not covered here

Git workflow → `git-workflow` skill. Figma translation → `figma-to-flutter` skill. Backend/Supabase → not yet a skill.
