---
name: git-workflow
description: Use this skill whenever committing code, branching, opening pull requests, or reviewing history in any GenX Labs project. Covers conventional commits, feature branch naming, the solo-PR discipline, and the rules for atomic, well-described commits. Trigger for any `git add`, `git commit`, `git branch`, `git checkout`, `git merge`, or `gh pr` operation, and when asked to review a diff before commit.
---

# git-workflow

The git habits that keep a solo bootstrapper sane as projects accumulate. The bet is that a 10-second discipline now saves a 30-minute archaeology dig in six months. Every rule below has paid for itself at least once.

## Layout

One repo per project under `~/Projects/<project-name>/`. Each repo is independent — no submodules, no monorepo, no shared infrastructure across apps. When two projects genuinely share code, extract a pub.dev package; until then, copy-paste is cheaper than premature coupling.

## Branch naming

```
main                  → always deployable
feat/<short-name>     → new feature
fix/<short-name>      → bug fix
chore/<short-name>    → tooling, config, no production code change
refactor/<short-name> → restructure without behavior change
docs/<short-name>     → documentation only
```

Branch names use kebab-case and stay under ~40 chars. `feat/streak-tracker` not `feat/implement_the_streak_tracker_for_users`.

## Conventional commits

Every commit follows the conventional commits spec:

```
<type>(<scope>): <subject>

<body — optional>
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`.

Subject is imperative, lowercase, no trailing period, under ~70 chars.

For atomic commits, **the body is usually unnecessary** — a clear subject says everything the diff doesn't. Only add a body when there's a *why* the subject can't carry: a non-obvious motivation, a hidden constraint, a referenced incident. When you do, keep it to **1–2 short lines**. If the body wants to grow into paragraphs, the change wants to split into multiple commits — not a longer message.

**Examples:**

- `feat(prayer): add 21-day streak counter to home screen`
- `fix(theme): correct contrast ratio on Vespers dark mode`
- `chore(deps): bump flutter_riverpod to 2.5.1`
- `refactor(home): extract prayer card into shared widget`

## The solo-PR discipline

Open a PR even when working alone. The five minutes it takes to title and describe a PR are the cheapest design review in software — half the issues that get caught in the diff would have shipped to production without the pause.

- Every feature branch ends in a PR, even one-commit ones.
- PR title mirrors the conventional-commit subject.
- PR description has three short sections: **What** (1–2 sentences), **Why** (the user-facing motivation), **How tested** (manual steps or test coverage).
- Squash-merge to `main`. Intermediate commits on a feature branch don't earn their place in history.
- After merge, delete the remote branch. Stale branches are noise.

## Atomic commits

A commit either makes sense alone or it doesn't belong on its own. If a single commit message would need an "and" in the middle ("add streak counter and fix nav bug"), split it.

**Atomicity applies to both the file set AND the message.** If you can't describe the change in one subject line plus at most 1–2 short body lines, the commit is doing too much. The fix is to split the diff, not to write a longer message.

Indicators a commit is too big:

- The subject would need to be longer than 70 chars to be accurate.
- The body wants to become paragraphs to cover everything in the diff.
- The diff tells two stories — a reviewer would naturally describe it with "this commit does X *and also* Y."
- You'd review it in two passes.

Two files can ship in the same commit if they're **mechanically coupled** (one requires the other to be valid — e.g., removing a `.gitignore` line that hides a file you're adding in the same change). Conceptual relatedness ("both are docs", "both touch the new feature area") is not enough.

## Reviewing a diff before commit

When asked to review a staged or unstaged diff, check in this order:

1. **Scope** — does this match one conventional-commit type? If not, suggest a split.
2. **Accidents** — debugger statements, commented-out code, `print()` calls, test-only changes left in. Flag every one.
3. **Tests** — does the change touch logic that has or should have tests? Suggest the minimum coverage that would catch a regression.
4. **Naming** — variable, function, and file names match the rest of the project? Inconsistency now becomes friction later.
5. **Message** — would the subject line make sense to a stranger six months from now? Rewrite if not.

## When something feels wrong

If a workflow rule feels expensive in a specific moment, it usually means the situation is unusual (a hotfix, a one-off script, a personal experiment), not that the rule is wrong. The rules earn their keep over months, not minutes. Override deliberately, not silently — leave a note in the commit body when you do.
