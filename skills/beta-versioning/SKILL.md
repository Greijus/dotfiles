---
name: beta-versioning
description: GenX Labs beta versioning — a VERSION file at the repo root plus "Version X.YbN" marker commits that stamp exactly which build a device-test round exercised. Use whenever a build is handed to (or returns from) device/beta testing, when the operator reports tested-build findings and fixes are about to start, when cutting the next beta, or on any mention of "version file", "1.0b2", "beta version", "mark this version", or a "Version …" changelog commit. Complements git-workflow (marker commits are the one sanctioned exception to conventional-commit format).
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

## When to make one

1. **Before starting fixes on a tested build's findings** — stamp the code state that was actually tested (if it wasn't stamped when handed over). Its changelog describes what that beta contains.
2. **When handing the next beta to testing** — bump `VERSION` (e.g. `1.0b1` → `1.0b2`) and marker-commit; the changelog lists the fixes/changes since the previous marker.

Between markers, all work stays ordinary conventional commits. Finding-fix rounds get a fix plan with a tracker (see `execution-planning`); the tracker is ticked per fix, and the next marker's changelog is read straight off it.

## Rules

- One marker per tested build — never reuse or amend a version number that reached a device.
- The marker commit contains **only** the VERSION bump; fixes never ride in it.
- Don't tag releases with this; store/app-release versioning (pubspec `version:`, build numbers) is a separate concern the marker commit does not touch.
