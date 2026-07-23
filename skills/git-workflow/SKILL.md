---
name: git-workflow
description: Use this skill whenever committing code, branching, opening pull requests, or reviewing history in any GenX Labs project. Covers conventional commits, feature branch naming, the solo-PR discipline, and the rules for atomic, well-described commits. Trigger for any `git add`, `git commit`, `git branch`, `git checkout`, `git merge`, or `gh pr` operation, and when asked to review a diff before commit.
---

# git-workflow

Solo-bootstrapper git discipline: atomic commits, conventional format, PR-even-when-solo. Claude stages files and drafts commit messages; the operator always runs the commit.

## Repo layout

One repo per project under `~/Projects/<name>/`. No submodules, no monorepo — shared code across apps becomes a pub.dev package once duplication actually hurts, not before.

## Branches

```
main                    always deployable
feat/<name>             new feature
fix/<name>              bug fix
chore/<name>            tooling/config, no prod code change
refactor/<name>         restructure, no behavior change
docs/<name>             docs only
```

kebab-case, under ~40 chars.

## Commit messages

```
<type>(<scope>): <subject>

<body — optional, 1-2 lines>
```

Types: `feat fix chore docs refactor test perf build ci`.

- Subject: imperative, lowercase, no trailing period, under ~70 chars.
- Body only when the subject can't carry the *why*. If it wants to grow past 2 lines, split the commit instead of writing more.
- Never add a co-author line — the message belongs to the operator, ready to paste as-is into `git commit -m`.
- Always present the final message in its own fenced code block so it can be copied straight into the terminal.

## Atomic commits, atomic staging

One story per commit, one story per `git add`. If the subject needs "and," or the diff bundles two unrelated changes, split the staging along with the message.

Two files may share a commit only when mechanically coupled (one is invalid without the other). "Both touch the same feature" is not enough.

## Staging vs. committing

Claude may run `git add` — staging is reversible (`git restore --staged <path>` undoes it). Claude never runs `git commit`, under any circumstances; the operator makes the final call.

Claude stages proactively only when:
- the operator says "stage X" → stage exactly X, or
- the operator prompts the bare word `git` → see below.

### The `git` shortcut

1. `git status` + `git diff` (staged and unstaged).
2. Detect stories — a story is one coherent, one-subject-line change. Unrelated files, or one file mixing unrelated hunks, means multiple stories.
3. **Single story:** stage everything, propose the commit message, stop.
4. **Multiple stories:** announce the split (1..N), stage only story 1 — whole files via `git add <path>`, partial files via a hunk-only patch and `git apply --cached` — propose story 1's message, stop. The next `git` prompt handles story 2.

## PR discipline

Every feature branch gets a PR, even solo one-commit ones. Title mirrors the commit subject; description covers What / Why / How tested. Squash-merge to `main`; delete the branch after.

## Reviewing a diff

Check, in order: scope (one conventional-commit type?) → accidental debug/commented-out code → test coverage for changed logic → naming consistency → would the subject read clearly to a stranger in six months?

## Don't delete now-empty config files

If a `.gitignore`, `.editorconfig`, or `.gitattributes` becomes empty after a change, edit it to empty rather than deleting it — its presence signals the project manages that concern.
