---
name: play-release
description: Take a Belmia app release from "cut" to "live on Google Play". Runs every machine step itself (format, analyze, full test suite, CI, privacy/SDK gates, Version marker, signed AAB, tag, upload and promote through the Play Developer API). Walks the operator through each Play Console and Firebase step one at a time, and keeps a per-release tracker in the app repo (docs/releases/<version>.md). Resumable and idempotent. Trigger on "release <version>", "ship <version>", "upload to Play", "start the release", "resume the release", "where is the release", "promote to production", "send for review", "Play Console declarations", or any Play publishing work in a repo that has release.config.yaml.
---

# play-release

One command per release, `release <version>`, from a cut to live on Play. The machine does
everything it can; the operator does the console clicks, **one step at a time**. The tracker
is the single source of truth: **every status change is written there before anything is said
in chat**, so a release survives a crash, a new session, or a week's pause.

## Where things live

| Path | What | In git |
|---|---|---|
| `<this skill>/scripts/release.py` | the step runner | dotfiles (public: nothing app-specific, nothing secret) |
| `<this skill>/scripts/play_api.py` | Play Developer API v3 client (service-account JWT, edits) | dotfiles |
| `<this skill>/scripts/templates/` | tracker template, `release.local.example.yaml` | dotfiles |
| `<app>/release.config.yaml` | the app's values: package, Firebase project, policy URL and copies, tracks, gates, manual-step text | app repo |
| `<app>/release.local.yaml` | secrets: `reviewer_code_sha256`, the service-account key **path** | **gitignored** |
| `<app>/docs/releases/<version>.md` | the release's tracker | app repo (main line) |
| `<app>/docs/releases/play-console-state.md` | one-time Play Console declarations: current answer, status, last confirmed; the PRIV-1 field list | app repo (main line) |

`<this skill>` is the base directory shown when the skill loads (`~/.claude/skills/play-release`).
Run everything **from the app's main checkout**:
`python3 ~/.claude/skills/play-release/scripts/release.py <command> <version>`.

A new app needs a `release.config.yaml` (copy PRAY's and change the values), a
`release.local.yaml` (from the template) and a seeded `play-console-state.md`.

## Commands

| Command | Does |
|---|---|
| `status <v>` | creates the tracker if missing; prints the table |
| `run <v>` | runs from the first open step until a manual step, a go, or a failure |
| `done <v> <step> "<evidence>"` | records a **manual** step; evidence is a date, count, sha or path, never "done" |
| `cut <v> --go` | makes the `Version <v>` marker (VERSION only), after gates 9–11 are ✅ and the audit gate passes |
| `cherry-pick <v> <sha>…` | brings a fix into the release; reopens every code step after it |
| `ack <v> <package> "<why>"` | accepts a new direct dependency for the SDK gate |
| `review <v> "<evidence>"` | records the delta review of the code at HEAD in § Delta review, for the audit gate. Evidence is what the review did and what came of it: `/code-review high v1.0b19..HEAD: 6 findings, 5 fixed (<shas>), 1 recorded in open-items` |
| `promote <v> --to <track> --fraction <0–1> --go` | moves the uploaded build between tracks |
| `gate <v> policy\|priv1\|sdk\|audit [--worktree DIR]` | runs one gate without touching the tracker |
| `readout <v>` | reads tracks, app details, store listing + image counts, and subscriptions from Play (read-only: the edit is deleted) into `play-console-state.md` § Play readout, with what the listing still lacks |

**Source column.** Every tracker row and every state row says where its evidence came from:
`api`, `gh`, `repo`, `repo + site`, `gcloud`, or `manual (<operator>, <date>)`. **Never mark ✅
what was not verified that way.** A fact the operator reported but no tool confirmed is
◐ "reported", with the check that would verify it.

**Long steps** (the tests take ~20 min, the build ~7) run inside `run`. Start it with the Bash
tool's `run_in_background`, wait for the completion notice, then show the result. Never poll.

## How a session runs it

1. `run <v>`. Show the operator **only** what it printed: the current step and the table.
2. **Manual step** (◐, Who = me): relay the printed guide as it is. Wait for the operator. Then
   `done <v> <n> "<evidence they gave>"` and `run` again.
3. **Needs a go** (cut, promote, publish): ask in one tap (`operator-surveys`). Run the command
   with `--go` only after the operator said go **in this conversation, for this action and
   this version**.
4. **⛔**: relay what failed, why, and the fix, exactly as printed. **Stop.** Do not try a
   workaround, and do not mark anything ✅ by hand.
5. After step 13, **rewrite § Play release notes** in plain words for users: what changed for
   them, no ids, within the limit. Delete the DRAFT line. The upload refuses a draft.
6. When the operator changes a declaration's answer, edit that row of `play-console-state.md`
   (answer, status). `done` stamps the date.

## The steps (rendered into every tracker)

1–4 setup: preflight · Play API service account (once per app; auto-✅ once it works) ·
release worktree · fixes to cherry-pick. 5–8 verify: `dart format` + l10n regenerated
with no diff · `flutter analyze` · full `flutter test` · CI green at that commit — or, when the
workflow filters `on.push.paths`, at the newest earlier commit with nothing under those paths
changed since (a docs-only commit gets no run of its own). 9–11 privacy gates. 12 the cut,
**on go**, refused until the audit gate passes. 13 changelog + release notes. 14 secrets gate.
15 signed AAB, verified. 16 tag and push. 17 upload to the internal track. 18–21 operator
checks: the phone on the Play-installed build · Firebase · declarations flagged for re-check ·
Sign in details. 22 promote, **on go**. 23 send for review / publish, **on go**. 24 close.

## Gates (each blocks with what failed, why, and the fix)

- **Policy parity:**
  - the site repo copy equals the in-app copy, from `policy.body_starts_at` down;
  - the deployed page equals the site repo.
  Both are compared as normalised word streams, so Markdown versus HTML and curly versus straight quotes don't count as differences.
- **PRIV-1:** the `request.*` fields the prompt builder reads must equal the `priv1` block in `play-console-state.md`, and every phrase must appear in the policy. A new field stops the release: update both policy copies and Data safety, and do the consent re-ask.
- **Audit** (`gates.audit`; skipped as "not configured" without it), checked at step 12 before VERSION is written:
  - *cadence:* commits and lines changed (insertions + deletions) under `paths` since `last_audit_sha`, on the RC's history. Past `max_commits` or `max_lines_changed`, the cut stops until a scored re-audit (`code-audit`) lands its remediation and `last_audit_sha` moves to the re-measured commit;
  - *delta review:* § Delta review must name HEAD, or a commit with nothing under `paths` changed since. Review `<last release>..HEAD` (built-in `/code-review` at high effort, or a fresh agent against the `clean-code` rubric), fix or record every finding, then `review`.
  *Why:* pray-app went 643 commits from `1.0b11` to `1.0b19` with no audit between. Every rule the first audit had made a test held; every rule left as prose decayed, and the score fell 4.7 → 4.0.
- **CI waiver** (step 8): `gates.ci_waiver: {until, reason}` accepts step 7's local full suite in place of CI, but only for a run GitHub never started (billing, spending limit) and only before `until`. A run that started and failed still stops. Set it only on the operator's call, with a date; the evidence names the refused run. *Why:* pray-app 1.0b21 (2026-10-27) hit the spent Actions allowance at the cut.
- **SDK:** no package matching `gates.sdk.deny` anywhere in `pubspec.lock`. Every new direct dependency since the last release needs an `ack`.
- **Secrets:** the reviewer hash comes from `release.local.yaml`, is never printed, and must agree with `cross_check_files`. The Gradle debug-token guard must be present, and no debug token may be in the environment.
- **AAB:**
  - signed with `upload_cert_sha256`;
  - the store package id, with no `.rc` / `.dev` suffix;
  - versionName is the bare version at the marker, else `<v>+<sha>`, and never `.dirty`;
  - the reviewer hash is in every `libapp.so`.

## Parallel work

- **The release worktree:** `.claude/worktrees/release-<v>`. If `rc/<v>` is free it is checked out there. If your folder has `rc/<v>` open, the worktree is a **detached copy of its tip** and your folder stays where it is. Move it to the next `rc/` **only if you are developing** during the release (operator, 2026-10-21).
- ⚠️ **Detached mode is broken (found 2026-10-23, pray-app 1.0b19):** the runner's tracker commits go onto `rc/<v>` in your folder, while the cut and the build go onto the detached copy. The two lines diverge at the cut, and the branch-moved guard counts the tracker's own docs commits. **Until it is redesigned, before `run`: move your folder to the next `rc/` branch, so the worktree checks out `rc/<v>` itself.** That is the arrangement that shipped 1.0b18. Afterwards, rebase the next `rc/` branch onto the `Version <v>` marker.
- **The branch must not move under the release.** Before the cut, the build and the push, the runner stops if `rc/<v>` gained commits the release does not have. Picked commits count as had. The push is fast-forward only. In detached mode, step 16 ends by telling you to `git merge --ff-only origin/rc/<v>` in your folder; it never moves your branch itself.
- **Fixes:** they reach the release only through `cherry-pick`. It never merges or rebases. Each pick is recorded in § Cherry-picks, and every code step after it reopens.
- **A dirty worktree stops the step**, listing every dirty file.
- **Gitignored build files** (`build.local_files`, e.g. `key.properties`) are symlinked from the main checkout, never copied.
- **Tracker commits:** only the tracker and the state file, as `docs(release): …` in the main checkout. There is **one commit per command** (`run`, `done`, `cut`, …), not one per step, although the file itself is written at every status change. They are never pushed by the runner.

## Rules

- **No secrets anywhere** but `release.local.yaml` and the key file: not the repo, the tracker, logs, command lines shown, or chat. That covers the reviewer code, its hash, the service-account JSON, keystore passwords and debug tokens. Evidence names a path or a check result.
- **Never send for review, publish, or promote** without the operator's explicit go, given in this conversation for that action and that version.
- **On failure:** say what failed, why, and the fix, then stop. Never guess and continue.
- **Chat stays short:** the current step plus the table. Details go in the tracker.
- One command per Bash call. Flutter and dart runs go through `testlock` (the runner does this itself).
- The `Version` marker follows `beta-versioning`: VERSION only, and only on go. The runner's privacy gates are that skill's privacy gate; its audit gate is that skill's audit gate.
- **Never edit § Delta review by hand, and never move `last_audit_sha` without the re-audit.** Each is the only proof its half of the audit gate has.
