---
name: device-verification
description: Use this skill whenever a build is proved (or disproved) on real hardware — running a device-test pass, triaging what the operator found on the phone or tablet, deciding whether a fix is actually done, planning or running a round of beta fixes, or driving a device over adb. Covers the V-list of things a test suite cannot prove, verifying the mechanism rather than the display, treating device state as evidence, writing forcing procedures that actually work, the round/finding-ID structure for fix cycles, and Android adb tribal knowledge. Trigger on "test on the device", "verify on the tablet/phone", "device pass", "beta round", "fix round", "does it work on the real device", "I found this on my phone", adb/screencap/logcat work, or any claim that a fix is complete.
---

# device-verification

The discipline that closes the loop between "the suite is green" and "it works". Distilled from pray-app's six device-test fix rounds, where device-only defects were the largest bug class and several "verified" fixes had to be reopened.

## The core rule

**A fix is done when it survives the device, not when it merges.** Green tests prove the code does what you told it to; only hardware proves you told it the right thing. *A celebration animation passed its tests and rendered invisibly. A breathing glyph was device-verified, then reopened twice — too subtle to notice, then unreadable at 20 px.*

## The V-list

Anything the build cannot prove goes on an explicit list, flagged **unverified** rather than assumed working. Never let "tests pass" stand in for these:

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

## Forcing procedures are code — run them before you record them

A written procedure rots faster than the docs around it. *One recorded forcing recipe was wrong in three ways and could not have produced the state it claimed: it named a package that is not debuggable, misstated how the ORM stores datetimes, and backdated a field that could not move a log-derived counter.*

Before a procedure is written down: execute it, confirm the state it claims to produce, and name the **debuggable** variant explicitly (a release build usually is not). Re-verify it whenever the build config changes.

## Running a fix round

- **One round file per device pass**, with a stable finding-ID scheme. Log the finding when it is reported, tick it when the fix lands.
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
