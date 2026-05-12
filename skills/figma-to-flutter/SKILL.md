---
name: figma-to-flutter
description: Use this skill when translating Figma designs into Flutter widgets, exporting design tokens, or syncing visual specs between Figma and a Flutter codebase. Covers two paths — manual token export via Tokens Studio (free-tier Figma) and Figma MCP server integration (Pro tier). Trigger when asked to implement a screen from a Figma frame, sync colors or typography from Figma, or set up the Figma-to-Flutter workflow for a new app.
---

# figma-to-flutter

The bridge between Figma source-of-truth and Flutter implementation. Two paths exist depending on Figma tier; pick once per project and stick with it.

> **Status: working draft.** Path A is the only one tested in practice today. Path B activates once the Figma Pro decision is made — see `~/dotfiles/COMPANY.md` decisions log for current status.

## Path A — Manual token export (Figma free tier)

The path available without a paid Figma plan. Slower per-screen, but zero external dependencies and no MCP setup overhead.

**Workflow:**

1. In Figma, install the **Tokens Studio** plugin. Define color, typography, spacing, and radius tokens as Figma variables or via the plugin's JSON sync.
2. Export tokens to `design-tokens.json` in the Flutter project's `assets/` directory. Commit the export.
3. In Flutter, write `lib/core/theme/tokens.dart` that parses the JSON at startup (or commit a generated `tokens.g.dart` if regeneration is rare).
4. Every `ThemeData`, color, and text style references the generated tokens — never a hardcoded value.
5. For per-screen translation, screenshot the Figma frame and hand it to Claude alongside the relevant feature directory. Ask for a widget tree that uses theme tokens, not Figma's raw values.

## Path B — Figma MCP server (Figma Pro tier)

The path that becomes available once the Pro upgrade is committed. Claude Code reads Figma frames directly via the MCP server, eliminating the manual screenshot-and-describe step.

**Setup (when activated):**

1. Verify Figma Pro is active on the account.
2. Configure the Figma MCP server in Claude Code per the connector documentation.
3. Confirm read access to the relevant Figma file.
4. Discard the manual screenshot pipeline for any project that adopts this path.

The MCP path doesn't replace the Tokens Studio export — tokens still flow through a generated Dart file. It replaces only the per-screen visual handoff.

## Choosing a path per project

Decide at project start. Switching paths mid-project means rewriting whichever theming code was already in place, which is wasted effort. The prayer app currently sits on Path A by default; revisit if Figma Pro is adopted before the prayer app's MVP ships.

## Anti-patterns

- **Hardcoding colors or sizes in widget code.** Always route through theme tokens. The prayer app's three themes (Dawn, Mist, Vespers) only work if every visual property is theme-driven.
- **Hand-translating spacing in pixels.** The Figma spacing scale maps to Flutter `EdgeInsets`; preserve the scale, don't reinvent it screen-by-screen.
- **Skipping the typography map.** Figma text styles map 1:1 to `TextTheme` entries. Define them once in `tokens.dart` and reference by role (`bodyLarge`, `titleMedium`, etc.) — never by literal font-size.
- **Implementing a screen before the tokens are in place.** Token-first or you'll be doing find-and-replace through every widget when the design changes.

## When this skill is invoked but path isn't chosen yet

Ask which path applies to the current project before doing any work. If unclear, default to Path A — it's safer than committing to MCP setup that may not happen.
