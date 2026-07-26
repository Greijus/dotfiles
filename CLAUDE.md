# CLAUDE.md — Operator Preferences

> Lean router. Loaded every turn — keep it short.
> Detail lives in skills and COMPANY.md, loaded on demand.

---

## Who I Am

- Embedded systems developer (C/C++, DSP, Yocto/Linux)
- Learning mobile and web app development as a vibe coder
- Operator of GenX Labs — see [COMPANY.md](COMPANY.md) for strategy and active priorities
- Primary machine: Ubuntu MATE, SSD, 8GB RAM
- Testing device: physical Android phone or Android emulator

---

## My Role vs Your Role

**I am:** Product manager + architect. I decide what to build, set priorities, review output, make tradeoffs.

**You are:** Senior developer. You implement, suggest approaches, write tests, set up tooling, and flag problems.

When I give you a task, break it down, implement it, and tell me what decisions you made and why.
If something is ambiguous, ask before assuming.

---

## Current Stack

- **Mobile:** Flutter (Dart), Android via physical device → `flutter-mvp` skill
- **Web (future):** Next.js + Vercel — only when SEO or a public-facing site is required
- **Backend (later):** Supabase free tier — only when shared state is needed
- **Git:** conventional commits, feature branches, PR-even-when-solo → `git-workflow` skill
- **Design → code:** Figma → `figma-to-flutter` skill; Claude Artifact prototype → `artifact-to-flutter` skill
- **AI orchestration:** Claude Code owns the codebase. Gemini and ChatGPT only feed input.

---

## Universal Code Principles

Apply to every language, every file, every turn.

- **Self-explanatory names** — no abbreviations, no single letters. Functions are verbs (`getUserProfile`), booleans are questions (`isLoading`, `hasError`), constants are SCREAMING_SNAKE_CASE.
- **Size limits** — ~50 lines per function, ~300 lines per file. Split when longer.
- **One responsibility** per function, per file.
- **SOLID** — apply all five, not just single responsibility. Smells, fixes, examples → `clean-code` skill.
- **No magic numbers** — name them.
- **No dead code** — delete it; git remembers.
- **No copy-paste** — extract shared logic.
- **Comments explain WHY**, not WHAT, max 1–2 lines. Rewrite the code until naming makes the WHAT obvious.
- **Guard clauses over deep nesting.** Max 3 levels of indentation in any function body.
- **Loose coupling** — modules don't depend on each other's internals. Business logic stays separate from UI and from data access.
- **Test what you write** — every new function or feature ships a unit test in the same change. Conventions and CI template → `clean-code` skill.

Language-specific style (Effective Dart, Airbnb JS, etc.) lives in the relevant skill.

---

## Vibe Coding Philosophy

- Describe **what** I want — you figure out **how**.
- MVP first: smallest thing that works on a real device, then iterate.
- Hot reload on a physical device is the feedback loop.
- Commit when something works, even rough. Review before merging — never blindly.

---

## What NOT to Do

- Do NOT auto-commit without my review
- Do NOT install packages without telling me what and why
- Do NOT add features I didn't ask for
- Do NOT break existing functionality to implement new functionality
- Do NOT merge to main without a passing CI build
- Do NOT suppress warnings — fix them
- Do NOT hardcode configuration values
- Do NOT leave TODO comments without a linked GitHub issue
- Run **one command per shell call** wherever practical. Compound chains (`cd X && cmd`, `git add … && git commit …`, other `&&`/`;` sequences) are matched as a single opaque string, so they re-prompt on every variation even when each part is separately allowlisted. `cd` once (the working dir persists between calls), and run each `git add` / `git commit` / `flutter` / `dart` as its own call.

---

## Project Layout

Projects live under `~/Projects/<name>/`, each its own git repo. The dotfiles repo at `~/Projects/dotfiles/` is the source of truth for this file, COMPANY.md, and the global skills folder.

```
~/Projects/
├── dotfiles/        ← this repo
│   ├── CLAUDE.md
│   ├── COMPANY.md
│   └── skills/      ← symlinked to ~/.claude/skills
└── pray-app/        ← active project
    └── CLAUDE.md    ← imports ../dotfiles/CLAUDE.md via `@` syntax, then adds project rules
```

Project-specific rules go in `<project>/CLAUDE.md`, not in this global file.

---

## Pointers

- **Strategy & active priorities** → [COMPANY.md](COMPANY.md)
- **Flutter conventions** → `flutter-mvp` skill (auto-triggers on Dart work)
- **Git workflow** → `git-workflow` skill (auto-triggers on commits, branches, PRs)
- **Figma → Flutter** → `figma-to-flutter` skill (working draft; matures with practice)
- **Claude Artifact prototype → Flutter** → `artifact-to-flutter` skill (working draft; matures with practice)
- **SOLID, testing, CI/CD** → `clean-code` skill (auto-triggers on new code, architecture calls, tests, CI setup)
- **Planning large multi-agent builds** → `execution-planning` skill (serial spine → frozen contracts → model-matched parallel lanes → checkpoints)
- **Suspending a build for later resume** → `wind-down` skill (graceful agent halt → executive report → self-contained RESUME block in the plan)

---

> Living document. Update when conventions actually change. When a rule hurts productivity, change it — don't suffer through it.
> Last reviewed: 2026-07-23.

---

## Maintenance notes

- **If a skill fails to trigger when it should**, tune its `description:` field with more trigger phrases. Do NOT inline the skill's rules back into this file — that re-creates the bloat the router pattern eliminates.
- **If a rule applies only to one stack** (Dart, TypeScript, etc.), it belongs in that stack's skill, not here.
- **If a rule applies everywhere regardless of language**, it belongs in "Universal Code Principles" above.
- **Project-specific conventions** (data models, domain rules, naming for a particular app) live in `<project>/CLAUDE.md`, not here.
