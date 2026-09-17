---
name: device-verification
description: Use this skill whenever a build is proved (or disproved) on real hardware — running a device-test pass, triaging what the operator found on the phone or tablet, deciding whether a fix is actually done, planning or running a round of beta fixes, or driving a device over adb — and before any session runs the full test suite, a build, or anything on the device while other sessions may be doing the same. Covers the device-only list of things a test suite cannot prove, verifying the mechanism rather than the display, treating device state as evidence, the `testlock` mutex that stops concurrent sessions from colliding on the device or a checkout (test in a worktree or wait), writing forcing procedures that actually work, the round/finding-ID structure for fix cycles, and Android adb tribal knowledge. Trigger on "test on the device", "verify on the tablet/phone", "device pass", "beta round", "fix round", "does it work on the real device", "I found this on my phone", adb/screencap/logcat work, "run the full suite", "flutter test", "is the device free", or any claim that a fix is complete.
---

# device-verification

The discipline that closes the loop between "the suite is green" and "it works". Distilled from pray-app's six device-test fix rounds, where device-only defects were the largest bug class and several "verified" fixes had to be reopened.

## The core rule

**A fix is done when it survives the device, not when it merges.** Green tests prove the code does what you told it to; only hardware proves you told it the right thing. *A celebration animation passed its tests and rendered invisibly. A breathing glyph was device-verified, then reopened twice — too subtle to notice, then unreadable at 20 px.*

## The device-only list

Anything the build cannot prove goes on an explicit list, flagged **unverified** rather than assumed working. **Do not call it a "V-list" or give its entries a letter series** — it is part of the live round's doc and its items are numbered like everything else (`execution-planning` § Numbering). Never let "tests pass" stand in for these:

- OS share sheets, intents, browser hand-offs, tap-to-dial
- Notifications and scheduled reminders
- Fonts, text scaling, real densities
- Animations and anything z-ordered against a dialog or system surface
- Launcher icons and any asset the platform masks or rescales
- Permissions flows, battery/DND/vendor behavior
- Migrations against real upgraded data

Each V-item names the device, the steps, and the observable outcome. The operator runs it; you do not tick it for them.

## Verify the mechanism, not the display

A screen can be right for the wrong reason. Prove the thing underneath:

- Read the **database**, not the label (a backdated timestamp, the row that was actually written).
- Count the calls that must not happen (a client that throws if reached, asserted at zero).
- Inspect **decoded pixels** for anything visual — masks, corners, alpha, aliasing.
- For a hang or a crash, reproduce the *cause* (corrupt the DB, kill the network), not a lookalike.

*A challenge counter looked correct on screen while the field driving it had never moved — the day counter was derived from an event log, not from the field being backdated.*

## Device state is evidence

- **Do not replace the installed build while verifications are pending.** Reflashing destroys the evidence the operator was about to read. Ask before flashing anything.
- **Never uninstall when a migration is under test** — surviving real upgraded data is the whole point, and it is the one thing that cannot be un-shipped.
- **Run vendor defaults untouched first** (Samsung battery optimisation, DND). A failure there is a product finding, not a test artifact.
- **Order the checks against each other.** Fabricated state can destroy another item's evidence — verify the item that needs a natural history *before* the procedure that manufactures one.

## Sharing the device and the checkout — take the lock

Several sessions run at once, but there is one device and each checkout has one `build/` and `.dart_tool/`. Two sessions flashing the same device, or running `flutter test` / `flutter build` in the same checkout, corrupt each other's run and each other's evidence. Coordinate with `testlock` — no free-form "is anyone using it?", no guessing from `adb devices`:

```
~/.claude/skills/device-verification/scripts/testlock status
```

**This is enforced, not advisory:** the `require-testlock.py` hook (dotfiles `hooks/`) refuses a guarded command that is neither inside `testlock run` nor covered by a live lease this session holds, and its refusal says which lock to take. Read-only adb (screencap, dumpsys, logcat, pull) stays free. Do not route around a refusal with `bash -c` or a script — take the lock.

Two resources. The **device** lock is one per adb serial, machine-wide. The **checkout** lock is one per git working tree — a worktree is a different checkout with its own lock, and that is the escape hatch. `--owner` is always `<branch-or-lane>:<what>` (`rc/1.0b12:R12-3.2 device pass`), so `status` tells the other session who to wait for.

**Anything that builds or tests in a checkout runs under the checkout lock** — full suite, a single test file, `flutter build`, `flutter run`, `pub get`, `build_runner`. It is free when nobody else is there, and it releases itself when the command exits or dies:

```
testlock run checkout --owner "<branch>:full suite" -C <repo>/mobile -- flutter test
```

**A device pass holds a lease** across many tool calls — install, drive, screencap, read the DB — and releases when done. Renew it before `--ttl` (minutes, default 30) runs out, or it goes stale and anyone may break it:

```
testlock acquire device --owner "<branch>:R12-3.2 device pass" --ttl 30
testlock renew   device --owner "<branch>:R12-3.2 device pass" --ttl 30
testlock release device --owner "<branch>:R12-3.2 device pass"
```

Build the APK under the checkout lock, then install and drive under the device lock. When the build is handed to the **operator** to verify, keep the device lease for that handover with a long `--ttl` naming it (`--owner "rc/1.0b12:operator verifying R12-3"`) — pending verifications are evidence (§ Device state is evidence), and a lease that runs out would let another session flash over them.

**When the lock is busy (exit 75), do not queue on it idly — pick by resource:**

- **Checkout busy → test in a worktree.** If your change is committed (or you are already a lane), run the suite in your own worktree (`git worktree add`, then `pub get` there) instead of waiting. The first run there is slower, but it rarely loses to a long suite plus a device pass. Uncommitted edits in the shared checkout cannot move — wait with `--wait`.
- **Device busy → wait for it, and work on something else meanwhile.** There is no second device. Retry with `--wait <sec>` (keep it under ~540 so the Bash call does not time out), or run the wait in the background and carry on with work that does not need hardware: tests in a worktree, docs, the next finding's root cause.
- **Never break a lock that is not stale**, and never `release --force` one someone else holds unless the operator says so. `status` marks a stale lock (lease expired, or the `run` process died); the next `acquire`/`run` breaks those itself.
- **Hand the constraint to every agent you spawn.** A subagent that runs tests or touches the device gets the `testlock` lines in its brief (`orchestrator` § Fresh context per agent); a lane in a worktree still takes the device lock.

## Forcing procedures are code — run them before you record them

A written procedure rots faster than the docs around it. *One recorded forcing recipe was wrong in three ways and could not have produced the state it claimed: it named a package that is not debuggable, misstated how the ORM stores datetimes, and backdated a field that could not move a log-derived counter.*

Before a procedure is written down: execute it, confirm the state it claims to produce, and name the **debuggable** variant explicitly (a release build usually is not). Re-verify it whenever the build config changes.

## Running a fix round

- **The live round gets its OWN doc**, one file per round, and it is the working document for as long as that round is open. A consolidated `beta-rounds`-style file is a **summary of CLOSED rounds** — history, not a work list — and an open-items list is a candidate pool, not a round. Running a live round out of either is the drift this rule exists to stop: findings end up in three places, and none of them is authoritative.
- **The round doc opens with its tracker table, directly under the H1**, nothing above it (`execution-planning` § Numbering and the phase table). Log the finding when it is reported, tick it when the fix lands.
- **Number findings `R<round>-<phase>.<item>` and cite them round-qualified** — `R3-1.1`, never a bare `1.1`. **`R` is the only letter in the scheme.** Do not open a new letter series for a round, a checklist, or a backlog, however many old ones you see in the neighbouring docs — see `execution-planning` § Numbering. Legacy letters stamped into commit messages are quoted verbatim when citing that commit and extended never.
- **Reproduce first.** No lane, no fix, no estimate on an unreproduced defect.
- **One owner per defect** — two reports with one suspected cause are one fix, or the same defect gets fixed twice and shipped once.
- **Never open a lane on an undecided point.** An ambiguous spec is a product call, not an implementation detail; guessing wastes the lane either way. *One round lost a full rebuild to a spec whose two sections contradicted each other.*
- **State machines get specced for the user who already has history** — mid-run adoption, past-the-target, dead/expired state, migration. Blank-slate specs are how the same mechanic gets re-specced three rounds running.
- **Root-cause notes are the durable artifact**, not the trackers. Keep closed rounds for what they explain; git holds the rest. Mark spent handoff prompts HISTORICAL so no one runs them again.

## Android adb notes

- `adb shell monkey` fails against a lock screen — launch explicitly: `am start -n <package>/<activity>`.
- A permission prompt can steal focus on each launch; dismiss with `KEYCODE_BACK`.
- Flutter exposes nothing to `uiautomator`, so `adb exec-out screencap -p` is the only way to read the UI. A black screenshot almost always means the device is locked.
- Only the debug variant is debuggable — all DB and `run-as` work goes to the `.dev` package (`flutter-mvp` § Scaffolding).
- Watch for freeform/multi-window: screen coordinates, not app coordinates.

## Not covered here

Fix discipline and blast-radius sweeps → `clean-code` § Fixing a bug. The UI checklist itself (font scale, themes, contrast) → `flutter-mvp` § Before calling UI done. Which build a device is running → `beta-versioning`. Lane structure and handoff prompts → `execution-planning`. Landing the batch → `git-workflow` § Release-candidate branches.
