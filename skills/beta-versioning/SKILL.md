---
name: beta-versioning
description: GenX Labs beta versioning — a VERSION file at the repo root plus "Version X.YbN" marker commits that stamp exactly which build a device-test round exercised. Use whenever a build is handed to (or returns from) device/beta testing, when the operator reports tested-build findings and fixes are about to start, when cutting the next beta, or on any mention of "version file", "1.0b2", "beta version", "mark this version", or a "Version …" changelog commit. Also covers wiring the build to read VERSION — reach for it on `versionName`/`versionCode`, pubspec `version:`, or "which build is on the device". Complements git-workflow (marker commits are the one sanctioned exception to conventional-commit format).
---

# beta-versioning

Identify every tested build exactly, with one file and one marker commit — so "the bug was in 1.0b1" always resolves to a sha.

## The scheme

- **Beta builds:** `<major>.<minor>b<N>` — `1.0b1`, `1.0b2`, … one per build handed to device testing.
- **Releases:** `<major>.<minor>` — `1.0`, `1.1`, …

## The VERSION file

A `VERSION` file at the repo root; its **first line is the current version**. The rest of the file documents this scheme so the repo is self-describing. Bumping this file is what a marker commit contains — nothing else rides along.

## The marker commit

The **only commit allowed to break the conventional-commit format** (deliberate — it must stand out in `git log` as a version boundary):

```
Version <version>

- Brief description of the beta

Changelog:
- change a
- change b
```

No type prefix, no co-author line. Commit it via a message file (`git commit -F <msgfile>`, per git-workflow's permission-friendly rules) when agent commits are authorized; otherwise draft it for the operator.

## When to make one — ONLY when the operator asks

**A marker commit is never created on the agent's own initiative.** Not when a fix round finishes, not when the suite goes green, not when a build "looks ready to hand over" — the operator decides when a build becomes a numbered beta, because only they know what they are about to test. Creating one unasked mislabels history with a version that may never reach a device.

So: finish the work, report that the build is ready, and **state the marker is not made** — draft the `Version X.YbN` message and the changelog if useful, and stop there. Wait for an explicit request ("cut 1.0b2", "mark this version", "make the version commit").

Typical operator-requested moments: stamping the code state a device test actually exercised, or cutting the next beta before handing it over.

**A beta gets a marker, not a tag** (operator, 2026-11-02). Tags name real releases only (`v1.0`, `v1.1`); the marker commit and the sha in `versionName` already identify a beta, and a beta tag cost a second CI run on every cut. So land a marker on the main line: one left only on a dead branch has nothing holding it.

**An operator's "cut" is not a pass on the gates.** The marker still waits for the privacy gate (below) and the audit gate (play-release § Gates): a delta review of the code since the last marker, and a scored re-audit once the code has churned past the configured limits. It waits for the compliance gate too, when a store-regulated file changed (`store-compliance`).

Between markers, all work stays ordinary conventional commits — those need no special permission beyond the project's normal commit policy. Finding-fix rounds get a fix plan with a tracker (see `execution-planning`); the tracker is ticked per fix, and the next marker's changelog is read straight off it when the operator calls for it.

## Privacy-policy gate — before every cut (beta or release)

Once an app's privacy policy and store listing (Play Data safety form, etc.) are set up, **the policy is frozen against the store**: a change to it that is not mirrored in the store is a compliance break. So before drafting or cutting any `Version …` marker:

1. **Diff the policy since the last marker.** Find the previous `Version …` commit (`git log --grep='^Version ' -1`) and run `git diff <that-sha>..HEAD -- <every policy copy>`. Policy copies are project-specific — in pray-app: `mobile/assets/content/en/privacy-policy.md` (in-app) and the site copy in the `belmia-studio` repo (`src/pages/pray/privacy.md`); check the project's CLAUDE.md / open-items for the list.
2. **Also check what the policy describes**, not just its text: a changed AI provider, a new SDK that transmits data, or new typed input in the prompt changes what the policy and Data safety form must say even when the policy file itself is untouched.
3. **No change → say so** in the ready-to-cut report ("privacy policy unchanged since `<sha>`").
4. **Any change → report it prominently and do not cut until it is handled.** List the diff and the data-flow trigger, then state what is owed: the same edit in every policy copy, the hosted public URL redeployed, and the Play Data safety form (and any consent text) updated to match. The operator does the Play Console side; the marker waits until they confirm the store and the hosted policy match.

## Rules

- **Operator-requested only** (above) — the one rule that overrides convenience.
- **Run the privacy-policy gate (above) on every cut** — beta or release; a policy change blocks the marker until the store and hosted policy match.
- **The marker waits for the audit gate exactly as it waits for the privacy gate** → play-release § Gates (*Audit*). A version stamps reviewed code, not just tested code: pray-app went 643 commits from `1.0b11` to `1.0b19` without one, and its audit score fell 4.7 → 4.0.
- One marker per tested build — never reuse or amend a version number that reached a device.
- The marker commit contains **only** the VERSION bump; fixes never ride in it.
- **Wire the build to read VERSION** (below) so the string a marker stamps is the one a device reports. Until a project does, its app version is a separate concern the marker commit doesn't touch — but that leaves builds unidentifiable on-device, which defeats the point of stamping them.

## Wiring VERSION into the build

A marker commit only pays off if you can tell which build a device is running. Have the build
**read VERSION directly** rather than copying the number into a manifest or `pubspec.yaml`:
duplication drifts, and a second place to bump is a second place to forget.

Flutter/Android reference — pray-app, `mobile/android/app/build.gradle.kts` — parses the first
line, derives both Android fields, and fails the build loudly on anything malformed:

```
1.0b4  ->  versionName "1.0b4",  versionCode 10004
1.0    ->  versionName "1.0",    versionCode 10099
```

`versionCode` is `major*10000 + minor*100 + (beta, or 99 for a final release)`, so it only ever
increases and a release outranks every beta of its minor. Betas cap at 98.

**Stamp the build, not just the beta.** VERSION doesn't move between markers, so every sideloaded
build carrying newer fixes reports the same string as the marker it started at — indistinguishable
on-device (learned on pray-app, 2026-08-10). Fix this by having `versionName` self-identify in
three states: **VERSION names the beta; the short commit sha names the build.**

```
Clean build, HEAD == marker commit   → 1.0b5              (it IS the named beta — no stamp)
Clean build, commits past the marker  → 1.0b5+9af4e20     (drifted — sha appended)
Uncommitted tracked changes           → 1.0b5+9af4e20.dirty
```

A build is "at the marker" when the tree is clean **and** `HEAD` equals the sha of the last commit
that touched VERSION; only then does it report the bare version. `.dirty` flags a build that
matches no commit at all. `versionCode` stays derived from VERSION alone — the sha is display-only,
so store-ordering never breaks. Reference: pray-app `mobile/android/app/build.gradle.kts`.

Once wired, `pubspec.yaml`'s `version:` is inert — say so in a comment beside it and never bump
it. The marker commit still contains **only** the VERSION bump; that it now moves the app's
reported version is the whole point, not a violation of the rule above.

**Show the version inside the app** — a Settings or About footer reading the build's own
`versionName`. The chain only closes when the operator can read `1.0b5` on the device screen and
map it to a marker commit without a terminal. *Until this shipped, the app said "version 1.0
beta" and device findings could not be pinned to a build: "I don't know what beta is installed."*
