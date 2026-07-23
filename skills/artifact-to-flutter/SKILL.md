---
name: artifact-to-flutter
description: Use this skill when translating an HTML/CSS/JS Claude Artifact prototype into Flutter widgets, extracting design tokens from prototype CSS, or syncing a screen built as a Claude Artifact into the Flutter codebase. Trigger when asked to implement a screen from a Claude-designed prototype, pull colors/spacing/typography out of prototype CSS, or set up this workflow for a new app.
---

# artifact-to-flutter

Bridge between a Claude Artifact (HTML/CSS/JS) prototype and Flutter implementation — the same problem `figma-to-flutter` solves, with a different design source. Same target token pipeline; only the extraction step changes.

## Prototype is source of truth, but only once it's in git

A Claude Artifact lives on claude.ai, not in the repo — it can drift from what's described here or be lost. Before treating any prototype screen as a real spec:

1. Save its HTML/CSS/JS into the app repo, e.g. `design/prototype/<screen>.html`. Commit it.
2. Iterate on the prototype in Artifacts; re-export to that path whenever it changes meaningfully.

## Token extraction

1. In the prototype CSS, define tokens as custom properties (`:root { --color-primary: #...; --space-md: 16px; }`) rather than scattering literals through the markup.
2. Transcribe those properties into `design-tokens.json` in the Flutter project's `assets/` — same schema/location `figma-to-flutter` Path A uses, so the Flutter-side pipeline is identical regardless of design source.
3. Parse it in `lib/core/theme/tokens.dart` (or generate `tokens.g.dart`).
4. Every `ThemeData`, color, and text style references the generated tokens — never a raw value.

## Per screen

Hand Claude the committed prototype file (path, not a live Artifact link) plus the target feature directory, and ask for a widget tree built on theme tokens — layout and interaction states (hover/pressed/disabled in CSS) map to Flutter's equivalents, not to a pixel-matched re-implementation of the markup.

## Anti-patterns

- Hardcoding colors/sizes instead of routing through tokens (breaks all three app themes).
- Building a Flutter screen from a live Artifact link instead of a committed file — the source can change or disappear underneath you.
- Letting `design-tokens.json` go stale after the prototype changes — regenerate it in the same change, not later.
- Re-implementing CSS layout literally (flexbox quirks, web-only affordances) instead of the Flutter-idiomatic equivalent.

## Not covered here

Figma-sourced designs → `figma-to-flutter` skill. Dart/Flutter style and widget rules → `flutter-mvp` skill.
