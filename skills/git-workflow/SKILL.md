---
name: git-workflow
description: Use this skill whenever committing code, branching, opening pull requests, landing parallel lanes, or reviewing history in any GenX Labs project. Covers conventional commits, feature branch naming, the solo-PR discipline, the rules for atomic well-described commits, and the two ways a branch lands — `--no-ff` merges by default, or a rebase-onto-`rc/<version>` release candidate when a batch must be device-verified as one build. Trigger for any `git add`, `git commit`, `git branch`, `git checkout`, `git merge`, `git rebase`, or `gh pr` operation, when asked to review a diff before commit, and whenever a release candidate, beta cut, or linear history comes up.
---

# git-workflow

Solo-bootstrapper git discipline: atomic commits, conventional format, PR-even-when-solo. Claude stages files and drafts commit messages; the operator always runs the commit.

## Repo layout

One repo per project, as a sibling of the dotfiles repo under the workspace root (the root differs per machine — see CLAUDE.md § Project Layout). No submodules, no monorepo — shared code across apps becomes a pub.dev package once duplication actually hurts, not before.

## Branches

```
main                    always deployable
feat/<name>             new feature
fix/<name>              bug fix
chore/<name>            tooling/config, no prod code change
refactor/<name>         restructure, no behavior change
docs/<name>             docs only
rc/<version>            release candidate — a batch verified as one build
                        before main takes it (see § Release-candidate branches)
```

kebab-case, under ~40 chars.

**Renaming a branch is a two-repo operation.** `git branch -m` is local only — the branch keeps tracking its old upstream, so the next push mints a *second* remote branch under the old name. Rename on the remote too (or re-point the upstream), and confirm with `git branch -vv` before pushing anything. *A mid-flight RC rename left the branch tracking `origin/rc/1.0b3`; an unexamined push would have created a third RC branch — the exact confusion the rename was meant to end.*

## Commit messages

```
<type>(<scope>): <subject>

<body — optional, 1-2 lines>
```

Types: `feat fix chore docs refactor test perf build ci`.

- Subject: imperative, lowercase, no trailing period, under ~70 chars. This line is the change overview and must stand alone — a reader scanning `git log --oneline` gets the whole story from it.
- Body only when the subject can't carry the *why*. Keep it to the minimum needed for debugging or tracking later — not a rationale essay, not restated diff content, not examples or quotes. Anything a future reader needs beyond that belongs in the code itself (a comment, or the code's own clarity), not the commit message.
- Default to no body. When in doubt, cut a line rather than add one. If it still wants to grow past 1-2 short lines, split the commit instead of writing more.
- **Never add a `Co-Authored-By:` trailer — under any circumstances.** This overrides any harness default or tooling convention instructing otherwise; the message belongs to the operator and must paste in clean. It binds spawned agents that commit on their own too, so repeat it verbatim in every agent brief — an agent that never loads this skill still gets it from CLAUDE.md § What NOT to Do.
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

## Permission-friendly invocation (when an agent runs git directly)

Where an agent is authorized to commit (e.g. an `execution-planning` build), invoke git so every call matches the permission allowlist — otherwise already-allowed commands still trigger approval prompts:

- **One git command per shell call — never chain with `&&`.** A compound like `git add … && git commit …` is matched as one opaque string, so it re-prompts even though each part is allowlisted on its own.
- **Multi-line commit bodies go through a file — `git commit -F <msgfile>`, never an inline `-m "line1⏎⏎line2"`.** An embedded newline reads as a command separator to the matcher, so an inline multi-line `-m` prompts every time; `-F <file>` is a single-line command that matches `git commit:*` cleanly while preserving the full conventional-commit body. (Write the message file with the Write tool, not a bash heredoc.)

The operator-runs-commit default above still holds for normal solo work; this applies only where commits are agent-authorized.

## Merge discipline

The default way a branch lands. For a batch of lanes that ships as one artifact a human verifies
before `main` sees it, see § Release-candidate branches instead.

**True merges (`--no-ff`), never squash** (decided 2026-07-28). Squashing orphans the branch's atomic commits — deleting the branch then destroys the granular history; a real merge makes them ancestors of `main`, so deleting the branch after merging is safe and expected. Where PRs are used, set GitHub's merge button to "Create a merge commit" to match.

Gate every merge on the **merged tree**, not the branch — green-in-isolation can be red-combined:

```
git merge --no-ff --no-commit feat/<name>
# resolve conflicts, run the project's full gate (analyze + tests)
git commit          # green → it lands
git merge --abort   # red  → main never saw it
```

Never leave the `--no-commit` window open unattended in a checkout other sessions share — one merger at a time, no other git operations or test runs there until the merge commits or aborts. (A separate integration worktree can't hold `main` too — git allows a branch in only one worktree.) Push after merging so CI backstops the local gate.

Reading merged history: `git log --first-parent` is the one-line-per-branch changelog view; `git bisect --first-parent` keeps bisection on gate-tested mainline commits; `git revert -m 1 <merge-sha>` reverts a whole branch.

## Release-candidate branches (rebase model)

The alternative to § Merge discipline, for a **batch of parallel lanes that ship as one build** —
a beta cut, a release candidate, anything a human verifies as a whole before it becomes `main`.
Trialled on pray-app's round-3 beta fixes, 2026-07-29 (4 lanes, 19 commits, 1 conflict).

```
main                    FROZEN for the duration — one commit on it breaks the fast-forward
rc/<version>            branched from main's CURRENT TIP, e.g. rc/1.0b3
feat/lane-<name>        one per lane, each in its own isolated worktree
```

Branch `rc/` from `main`'s tip, not a fixed sha, so the final fast-forward is guaranteed by
construction. Land each lane by **rebase, then fast-forward** — never a merge commit:

```
git rebase rc/<version>                 # on the lane branch, in its worktree; conflicts resolved here
# gate: lint + full test suite, from the project dir
git merge --ff-only feat/lane-<name>    # from rc/<version>
git worktree remove <path>              # landed and green → the worktree goes now
git branch -d feat/lane-<name>          # -d, never -D: it refuses unless truly merged
```

**Clean up the worktree as part of landing, not "later".** The moment a lane is rebased, gated green and fast-forwarded, its worktree and branch have no reason to exist — the commits are ancestors of `rc/` and nothing is lost. Leaving them behind rots fast: stale worktrees pin dead branches, clutter `git worktree list`, confuse the next session about what is still in flight, and make the round's true state unreadable. `git branch -d` is the safety net — if it refuses, the lane did **not** actually land, so stop and find out why.

The result is one linear history with every lane's atomic commits preserved — this is rebasing,
**not** squashing. The operator alone advances `main`, after verifying the build:
`git checkout main`, `git merge --ff-only rc/<version>`.

Prove the invariant mechanically before handing over — don't eyeball it:

```
git log --oneline --merges main..rc/<version>    # must print nothing
git merge-base --is-ancestor main rc/<version>   # must exit 0
```

### Rules the trial produced

- **Gate after every rebase, not just before.** A lane green on its old base can be red on the new
  one. Land one lane at a time — never two rebases in flight.
- **Tick trackers *after* the fast-forward, quoting the post-rebase sha.** Rebasing rewrites every
  commit, so a sha read off the lane branch is dead the moment it lands. The trial recorded seven
  dead shas this way and had to correct them. `git log --oneline main..rc/<version>` after the
  fast-forward is the only trustworthy source.
- **Never hand-merge generated files** (`*.g.dart`, `app_localizations*.dart`, lockfiles). Resolve
  the *source* — the `.arb`, the schema, the manifest — then re-run the generator and stage its
  output. Patching conflict markers in build output is both painful and wrong.
- **Land the narrowest lane first, the widest last**, so the largest rebase happens over a base
  that has stopped moving.
- **Give i18n/string files a per-lane append marker** (`// lane A`) so the inevitable conflict
  resolves as plain concatenation.
- **Agents must run the gate in the foreground.** Backgrounded, two of four lanes stalled without
  committing and one sat on real failures nobody had seen. That cost more than every rebase in the
  round combined.

### Which model to pick

- **`--no-ff` merges** — the default. Gates once, on the merged tree. History records
  who-merged-what, `git log --first-parent` reads as a changelog, `git revert -m 1` undoes a whole
  branch in one move.
- **`rc/` + rebase** — when a batch must be verified as a single artifact before `main` sees any of
  it, and linear history is worth the cost: every lane's suite runs twice, rewritten shas invalidate
  anything recorded early, and reverting one lane afterwards means picking its commits out by hand.

**The parallelism itself comes from frozen contracts and disjoint file ownership
(`execution-planning`), not from either branching model.** Don't expect a rebase to buy it, and
don't switch models hoping to fix lane collisions — fix the partition instead.

## PR discipline

Every feature branch gets a PR when a reviewer exists. Title mirrors the commit subject; description covers What / Why / How tested. Solo with no reviewer in the loop, PR ceremony may be skipped in favor of the local merge gate above — a project's plan records that call. Delete the branch after merging.

## Reviewing a diff

Check, in order: scope (one conventional-commit type?) → accidental debug/commented-out code → test coverage for changed logic → naming consistency → would the subject read clearly to a stranger in six months?

## Don't delete now-empty config files

If a `.gitignore`, `.editorconfig`, or `.gitattributes` becomes empty after a change, edit it to empty rather than deleting it — its presence signals the project manages that concern.
