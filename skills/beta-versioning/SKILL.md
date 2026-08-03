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

Between markers, all work stays ordinary conventional commits — those need no special permission beyond the project's normal commit policy. Finding-fix rounds get a fix plan with a tracker (see `execution-planning`); the tracker is ticked per fix, and the next marker's changelog is read straight off it when the operator calls for it.

## Rules

- **Operator-requested only** (above) — the one rule that overrides convenience.
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

Once wired, `pubspec.yaml`'s `version:` is inert — say so in a comment beside it and never bump
it. The marker commit still contains **only** the VERSION bump; that it now moves the app's
reported version is the whole point, not a violation of the rule above.
