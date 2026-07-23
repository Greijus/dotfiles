---
name: figma-to-flutter
description: Use this skill when translating Figma designs into Flutter widgets, exporting design tokens, or syncing visual specs between Figma and a Flutter codebase. Covers two paths — manual token export via Tokens Studio (free-tier Figma) and Figma MCP server integration (Pro tier). Trigger when asked to implement a screen from a Figma frame, sync colors or typography from Figma, or set up the Figma-to-Flutter workflow for a new app.
---

# figma-to-flutter

Bridge between Figma source-of-truth and Flutter implementation. Pick one path per project at the start — switching mid-project means rewriting whatever theming code already exists.

> **Status:** Path A is the only one used today. Path B activates once Figma Pro is adopted — check `COMPANY.md`'s decisions log.

## Path A — Manual token export (free tier)

1. In Figma, define color/typography/spacing/radius tokens via the **Tokens Studio** plugin.
2. Export to `design-tokens.json` in the Flutter project's `assets/`. Commit the export.
3. Parse it in `lib/core/theme/tokens.dart` (or generate `tokens.g.dart`).
4. Every `ThemeData`, color, and text style references the generated tokens — never a raw value.
5. Per screen: screenshot the Figma frame, hand it to Claude with the feature directory, and ask for a widget tree built on theme tokens.

## Path B — Figma MCP server (Pro tier)

1. Confirm Figma Pro is active.
2. Configure the Figma MCP server per connector docs.
3. Confirm read access to the file.
4. Drop the manual screenshot step for any project on this path — tokens still flow through the generated Dart file; only the visual handoff changes.

## Anti-patterns

- Hardcoding colors/sizes instead of routing through tokens (breaks all three app themes).
- Hand-translating Figma spacing into raw pixels instead of the mapped `EdgeInsets` scale.
- Skipping the typography map — reference `TextTheme` roles (`bodyLarge`, `titleMedium`), never literal font sizes.
- Building a screen before its tokens exist.

## If no path is chosen yet

Ask which path applies before doing any work. Default to Path A if unclear — it's safer than committing to unfinished MCP setup.
