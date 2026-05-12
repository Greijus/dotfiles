---
name: flutter-mvp
description: Use this skill whenever working on Flutter mobile apps under GenX Labs — scaffolding a new app, adding features, reviewing code, or making architectural decisions. Covers project layout, Effective Dart style, the MVP-discipline rules (no premature backend, no premature billing, no premature CI/CD), and the documentation and code-quality bar. Trigger for any task involving Dart files, pubspec.yaml, Flutter widgets, theming, or app architecture decisions.
---

# flutter-mvp

The Flutter house style for GenX Labs apps. The goal is to ship MVPs fast without accruing the kind of mess that becomes painful at user-scale. This skill encodes the rules that experience has shown pay off; everything else stays out.

## Stage-appropriate discipline

The single biggest mistake at MVP stage is adding enterprise structure before it's earned. Default to the simplest thing that works; let real users force structure on you.

- **No backend until the app needs server state.** Local SQLite, Hive, or Drift is fine.
- **No paid tier until retention is proven.** Free-to-start is the strategy. Stub the paywall, don't build it.
- **No CI/CD beyond GitHub Actions running `flutter analyze` and `flutter test`.** Fastlane and Vercel wait until there's a real release cadence to automate.
- **No state-management library until widget state can't carry the weight.** Start with `StatefulWidget` + `ValueNotifier`. Reach for Riverpod or Bloc when shared mutable state genuinely demands it.

The trigger to add structure is always a real signal — a user complaint, a recurring bug, a deploy that took too long — never a hypothetical.

## Project layout

One repo per app under `~/projects/<app-name>/`. Inside the repo:

```
<app-name>/
├── lib/
│   ├── main.dart
│   ├── app.dart                 # MaterialApp + theme + routing
│   ├── core/                    # cross-feature: theme, utils, constants
│   ├── data/                    # local persistence, API clients (later)
│   ├── features/<feature>/      # one folder per feature
│   │   ├── <feature>_screen.dart
│   │   ├── <feature>_controller.dart
│   │   └── widgets/
│   └── shared/                  # widgets used in 2+ features
├── test/
├── pubspec.yaml
├── CLAUDE.md                    # routes to ~/dotfiles/CLAUDE.md + this skill
└── README.md
```

Move a widget into `shared/` only when a *second* feature actually uses it. Premature shared abstractions outlive their usefulness — they're harder to delete than to re-extract later.

## Code quality bar

These are non-negotiable on every commit, because catching them early is free and catching them late is expensive.

- **Zero warnings from `flutter analyze`.** If a warning is a genuine false positive, suppress it with an inline comment explaining why — never globally in `analysis_options.yaml`.
- **Effective Dart** for naming, formatting, and idioms. `dart format` on save.
- **Max 3 levels of indentation in a function body.** Deeper than that means the function is doing too many things. Extract or use guard clauses.
- **Guard clauses over nested `if`s.** Exit early; reduce cognitive load.
- **DRY, but not prematurely.** Three repetitions before extracting an abstraction. Two is coincidence.
- **DartDoc on every public API.** Private methods get a one-line comment only when intent isn't obvious from the name.

## Widget rules of thumb

- **`const` everywhere it's valid.** It's free performance and the analyzer will flag missed spots.
- **Stateless first.** Convert to `StatefulWidget` only when state is owned by the widget itself.
- **No business logic in `build()`.** Controllers or notifiers own logic; widgets own layout.
- **Theme via `Theme.of(context)`**, never hardcoded colors. The prayer app's three themes (Dawn, Mist, Vespers) only work if every color goes through the theme.
- **Accessibility minimums**: every `IconButton` gets a `tooltip`; every meaningful `Image` gets a `semanticLabel`.

## When asked to scaffold a new app

Default order of operations:

1. Confirm the app name and create `~/projects/<app-name>/`.
2. `flutter create` with `--org com.genxlabs` and `--platforms android` (add ios/web later if explicitly scoped).
3. Set up the layout above with empty placeholder files — don't backfill with speculative code.
4. Add `analysis_options.yaml` extending `package:flutter_lints/flutter.yaml`.
5. Initialise git, commit the scaffold as `chore(init): scaffold flutter project` (see `git-workflow` skill).
6. Create `CLAUDE.md` at the repo root that routes to `~/dotfiles/CLAUDE.md` and lists project-specific context.

## What this skill explicitly doesn't cover

- Git workflow → see `~/dotfiles/skills/git-workflow/SKILL.md`
- Translating Figma designs → see `~/dotfiles/skills/figma-to-flutter/SKILL.md`
- Backend / Supabase setup → not yet a skill; revisit when the first app needs server state.
