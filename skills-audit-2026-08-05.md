# Skills audit — what the Pray beta rounds should teach the GenX skills

**Date:** 2026-08-05 · **Auditor:** Claude (auditing-architect session) · **Basis:** `master` @ `97d73b1` (Version 1.0b5), 248 commits, fix rounds 1–6 (≈45 defect IDs F/S/T/L/U/W/X), `docs/plans/beta-fixes.md` + round files + verification.md + the three spent orchestrator prompts, and the operator's session transcripts.

**Purpose:** feed the lessons this project paid for back into the dotfiles skills (`clean-code`, `flutter-mvp`, `git-workflow`, `execution-planning`, `beta-versioning`) so the next round — and the next project — doesn't pay for them again. Recommendations only; nothing has been edited.

---

## 1. Headline numbers

- Of 248 commits: **101 (41%) are docs**, 65 feat, 36 fix/perf, 12 test. `docs(plan*)` bookkeeping alone is 69 commits ≈ **1.9 bookkeeping commits per fix commit**.
- Of the 36 fix commits, **~30 correct the project's own shipped work**; only ~5 have external causes.
- **Every device round found bugs in the previous round's fixes**: `ba69786`→`01bd235` (same hardcoded 21, 20 lines apart), `fd770e7`→`f13c1c8`→`17756b4`→`8feb050` (streak flame, four iterations), `592eaeb`→`7b06d22` (Mist panel overshoot), `666ca85`→`2e9db59` (decorative Focus-Mode settings), `1b47ec0`→`c6a79b3` (icon pipeline discarded on sight).
- The launcher icon took **9 commits and 3 generations**; challenge mechanics were **re-specced three times** (L5 → W1 → X1).
- Tests were written **after** bugs shipped in every traced case; no device-round bug was caught by an existing test. W1 had to be implemented and pinned **twice** because a 261-line fake re-implements the challenge rules.

Root-cause distribution (per the round docs): device-only visual/UX is the **largest class** (F1, F10, S5–S7, T2, U5, W2, X10, X11 …), then spec/product-call gaps (mostly "behavior for the non-blank-slate user was never decided"), then wiring bugs (data plumbed but never consumed: S1, X2/X3, X5, X6), then unit-testable logic bugs that existing tests missed (S1, U1, U6, X9b, X12, L5's latent pair), then platform gotchas, then process/docs failures (seven dead SHAs, the wrong V5 forcing procedure, stale U2 research, the unasked 1.0b2 marker).

## 2. What the skills already got right — validated, keep

- `git-workflow` § Release-candidate branches is a faithful distillation of the round-3 trial (tick-after-ff, foreground gates, generated-file rule, ARB markers). The failures it encodes did **not** recur in rounds 4–6.
- `beta-versioning`'s "operator-requested only" rule (bought by the unasked `fc2497b` 1.0b2 marker) held from round 4 on.
- `clean-code` § Design seams: `FeatureGate`, the one-door LLM boundary, and L1's `calls == 0` mutation-verified privacy proof are the payoff — the consent-gate work (L1, U4, W5) shipped cleanly three times because the seam existed.
- `execution-planning`'s frozen contracts + disjoint lanes: rounds 4–5 landed 4–5 lanes each with ~one trivial conflict.

The gaps are elsewhere: **bug-fix discipline, effect-level testing, device-reality checks, and asset handling** — the places where this project actually bled.

---

## 3. `clean-code` — the biggest gaps

### 3.1 Add a new section: **Fixing a bug** (the skill currently covers only writing new code)

Half this project's life was fix rounds, and the skill has nothing to say about fixing. Every lesson below was paid for at least twice.

Proposed text:

> ## Fixing a bug
>
> - **Reproduce, then root-cause, then fix.** A fix without a root cause relocates the bug (X4, L12). If it does not reproduce, close it with evidence and a recurrence recipe, not a shrug (X9a's logcat recipe).
> - **A symptom can hide two questions — answer both before fixing either.** X9 was "why did the splash appear" AND "why did it hang"; only one was a defect.
> - **Sweep the blast radius before calling it fixed.** The bug you found is one instance of its cause:
>   - fixed a hardcoded constant → `grep` the feature for every other instance (`ba69786` fixed "Day 34 of 21" in the label and missed the same `21` in the bar 20 lines below → U6). Live arithmetic only — prose and comments are not survivors (the 21-day-myth grep trap).
>   - fixed a shared widget on one screen → fix it **in the widget** so every call site heals; a per-call-site patch means the next screen ships the same bug (the flame: Home fixed, Progress missed, four iterations total).
>   - fixed one surface → check the sibling surface with the same shape (X10's dialog fix applies verbatim to its two sibling dialogs; X8 = F7 on a different screen).
> - **The regression test pins the fix in the same commit** — and asserts the *effect*, not the artifact (§ Testing).
> - **Update the comment/spec that described the old behavior in the same change** — a stale contract comment is how the next writer diverges (`8433a90`: a vague "the first" let two writers of one field drift; three separate doc-unstaling sweeps were needed after W1/W5).
> - **One owner per defect.** Two open items with one suspected cause belong to one fix (X5 owns L12) — "that is how the same defect gets fixed twice and shipped once."

### 3.2 Strengthen § Testing: test the **effect**, not the artifact

Every traced test failure was a test asserting existence, a write, or the happy path:

- F6: celebration tests "asserted the widget existed, not that anything was visible" — it rendered under `showDialog`'s barrier scrim. Cure was a **pixel-count test**.
- S1: `feelingCheckInPaused` was **written but never read** — the switch "worked" and changed nothing.
- X9b: the splash `await` had no catch, no timeout, no fallback route — no failure-path test existed.
- L5: the day-21 moment re-fired forever because no test covered days **past** the target.
- X12: five quote-wrap sites double-quoted 3 of 122 verses — never tested against the real corpus.

Proposed additions:

> - **Assert the effect, not the artifact.** "Widget exists" / "value was written" prove nothing. Prove the user-visible outcome: pixels rendered (F6's pixel-count), behavior changed on the read path, the forbidden call count is zero (L1).
> - **Every flag you write gets a test on its read path.** A written-never-read field is dead code with a UI switch attached (S1). If a setting ships, its wired behavior ships and is tested end-to-end — otherwise the setting is decoration (Focus Mode shipped two decorative pickers, `2e9db59`).
> - **Every `await` that gates navigation or startup gets a failure-path test** — error, timeout, and the fallback route (X9b: "a splash whose only exit is a happy-path await is a hang waiting to happen").
> - **Test past the boundary, not just up to it** — day N+1 of an N-day target, the second same-day event, the re-fire (both L5 latent bugs lived past day 21).
> - **Data-driven logic runs over the real shipped corpus in tests**, not synthetic samples (X12: 3 of 122 real verses carried their own quotes).
> - **Mutation-verify a guarantee that must never break** (privacy, money, theology): prove the test fails when the guarantee is removed — the L1 `calls == 0` model.

### 3.3 Extend § Design seams: **fakes must be dumb**

`FakeChallengeService` is 261 lines re-implementing streak rules on its own state model ("streak + lastActiveAt approximation"). Result: W1 was implemented twice (`96b3d24` touches both) and pinned twice (`5e3c965` + a mirror suite). Every behavioral change pays 2× and risks fake/real divergence — the exact "two copies that drift" the skill already warns about, produced by the skill's own fakes pattern.

Proposed addition:

> A fake is **dumb state, not a second implementation**. If a fake needs its own rules engine, the rules are in the wrong place — extract them into a pure core (stateless helper) that the real impl and the fake both call, or back the fake with the same derivation over an in-memory store. The smell: a behavioral change that touches `*_impl.dart` **and** `fake_*.dart`, and a `fake_*_test.dart` mirroring the real suite — that's the 2× tax, paid on every rule change forever.

### 3.4 Extend § Comments: **a comment that promises behavior is a contract**

- X5: the lifecycle comment already said "*or a new day begun*" — "the case was understood and only half-wired." The comment promised behavior no code implemented.
- U5: a highlight "commented as 'the canvas's blurred white disc'" was painted 30% **black** — comment and code contradicted, and reading them side-by-side was the diagnosis.

Proposed addition:

> A comment that states behavior is a contract: either code + a test back it, or it lies. When a fix changes behavior, the comment describing the old behavior is part of the diff. A comment contradicting its code is a bug report — read them against each other when diagnosing.

---

## 4. `flutter-mvp` — device reality and assets

### 4.1 Add: **Device-reality checklist** (the largest defect class had no rule)

Nothing was tested above default text scale until 2026-08-05 — X11 shipped truncated bottom-nav labels to a public beta "simply never looked at above the default text scale". F1, X10, X11 are all large-font failures; W2 is a 20px-size failure; F10/S6/T2 a three-round contrast hunt.

Proposed section:

> ## Before calling UI done
>
> - **Font scale 1.5 and 2.0** on every new/changed screen and dialog — layouts that pass at 1.0 often work only by incidental whitespace (X10's gapless `Row`). Dialogs must scroll, not clip (F1's failure mode).
> - **All themes, not the one you developed on** (the flame died on gold; Mist ate three rounds).
> - **The smallest size the widget actually renders at** — a 3-stop gradient cannot resolve in 20 px (W2).
> - **Contrast fixes carry numbers.** Name the target ratio, measure the candidates, pin every text/background pair in a contrast test (`prayer_surface_contrast_test.dart` after S7). An unmeasured "lighter" overshoots to white (S6→T2) — and a ratio that passes numerically can still *look* wrong, so eyeball it on the device too (`7b06d22`).
> - **Animations are bounded and reduced-motion-static** — an unbounded `repeat()` blocks every `pumpAndSettle`; and an animation "verified" as working can still be invisible in context (S3 shipped too subtle to notice; F6 rendered under a dialog's barrier scrim — overlay content goes **last in the Stack**, and never under `showDialog`'s barrier).

### 4.2 Extend § Widget rules of thumb

> - **Brand-critical shared widgets style themselves** — no caller-supplied tint/color parameter: "a tint a caller can pass is a tint a caller can get wrong" (U5; the flame's color param was removed, and the rule defended in W2 and round-5's prompt).
> - **A widget that must keep a shape re-asserts its own constraints** — parents hand out tight constraints that silently override yours (F2's oval medallion).
> - **Every startup/gating `await` has a catch, a timeout, and a fallback route.** A `catch` alone is not enough — a wedged DB isolate returns a future that neither resolves nor throws (X9b); and don't let error *reporting* break the recovery path (`FlutterError.reportError` asserts on async-gap stacks).

### 4.3 Add: **Assets have physics** (nine commits of icon tuition)

> ## Binary assets
>
> - **Verify properties mechanically before wiring an asset in**: real alpha (composite over dark — a checkerboard baked into opaque pixels *looks* transparent in a light viewer), dimensions, corner pixels per density. "Verified before placing rather than trusted" (`1b59c9d`) — the rule that ended the icon saga.
> - **Android adaptive icons: the outer ~33% is mask-reserved.** Watch stacked insets (generator default **plus** the master's own framing = double inset, `5f32c41`). Never hand-edit generated icon sets — fix the master or the generator config and regenerate (W3).
> - **A master downscaled >~3× in one decode step aliases** — ship dpr variants (1x/2x/3x) instead (W4). "The master is what is wrong for the job, not the widget."
> - **A README records which master feeds which surface** — otherwise the next regeneration starts from the wrong file.
> - **Art direction only settles on sight.** Get the operator's eyes on a cheap preview **before** building a derivation pipeline — a full pipeline was built, gated green on 570 tests, and discarded next day because the result "looked bad on sight" (`1b47ec0`→`c6a79b3`). Aesthetic acceptance cannot be delegated to a gate.

### 4.4 Extend § Scaffolding: **dogfood install identity from day one**

The operator's real prayer history was destroyed because a dev `flutter run` replaced the dogfood install ("The update deleted my history in the device…"). Fixed only in beta 4 (`25c36c4`).

> When the operator dogfoods on a personal device, set up per-variant `applicationId`s (`.dev` suffix) and keep signing config out of git **at scaffold time** — so `flutter run` can never uninstall the dogfood app and take its data with it. Verify schema migrations on a real upgraded install, never via uninstall/reinstall (V4's "the one item that could not have been un-shipped").

---

## 5. `git-workflow` — one small addition

The RC section already encodes its lessons and they held. One trap remains undocumented:

> **Renaming a branch is a two-repo operation.** The round-4 RC rename was local-only — the branch still tracked `origin/rc/1.0b3`, and a naive push would have minted a third RC branch. After any rename: rename on origin too (or re-point upstream) and verify with `git branch -vv` before anything is pushed.

---

## 6. `execution-planning` — five additions

1. **No lane on an undecided point.** Round 3 "lost a full rebuild by treating an ambiguous spec as settled" (L4's spec sections contradicted each other). Round 6 codified it project-locally: "Do not spawn a lane off an item whose open point is unanswered." Promote it into Task anatomy: a task whose Spec contains a contradiction or an open product call is not spawnable — ask the operator first; guessing wastes a lane either way.
2. **Audit the handoff prompt against the live repo before spawning.** The round-4 handoff audit (`edec109`) found **five** instructions that "would have cost a lane each": a local-only branch rename, a non-disjoint lane seam, a search task whose answer already existed, a grep that would have "fixed" deliberate prose, and a stale test-count baseline. Before spawning: verify branch/tracking state, baseline test count (run it), lane file-disjointness against `git grep` reality, and that each search task hasn't already been answered.
3. **Spec state-machine features for the non-blank-slate user.** Challenge mechanics were re-specced three times (L5 → W1 → X1) because each spec covered the new user and real history kept arriving as "new" product questions. Task anatomy addition: a Spec touching counters/streaks/history states the behavior for **existing** data — mid-run adoption, past-the-target, dead/expired state, migration — or it is not frozen.
4. **Trackers record only what git can't derive.** The status table duplicated facts git already knew (which version master is at, where rounds live) and drifted twice (`23128f0` is a commit solely to refresh it; `d891f9a` reconciles it again). Plus: **a written procedure is code — run it before recording it.** The V5 forcing procedure "was wrong in three ways and could not have produced day 21", written without being executed.
5. **Research findings carry a date and get re-verified before they kill a feature.** Device-wide grayscale was written off on 2026-07-23 research; Android 15's `ZenDeviceEffects` had already made it buildable (`7df1785` → `03b3c04`). A blocking "impossible" older than one OS release is re-checked before it's acted on.

Also worth an honest look, not a rule yet: the tracker discipline costs ~1.9 docs commits per fix commit (69 `docs(plan*)` commits). The per-fix tick is load-bearing (dead-SHA lesson), but consider letting the orchestrator batch ticks **per landing** (one docs commit per lane fast-forwarded, covering all its fixes) — same drift-safety, roughly half the bookkeeping commits.

---

## 7. `beta-versioning` — one addition

The wiring section exists because the operator couldn't tell which beta was on the device ("right now only shows version 1.0 beta, so I don't know what beta is installed"). The last mile is still undocumented:

> **Surface the version in the app itself** (Settings/About footer reading the build's `versionName`, `f6c494a`) — the chain is only closed when the operator can read `1.0b5` on the device screen and map it to the marker commit, without a terminal.

---

## 8. NEW skill: `device-verification` (working name)

The single largest body of hard-won, reusable knowledge currently lives only in one project's plan docs and three **spent** orchestrator prompts — the next project would rediscover all of it. The operator is already re-transmitting it by hand in session-handoff prompts (the round-6 kickoff prompt re-explains adb quirks, verification ordering, and evidence rules from scratch).

Charter (distilled from `beta-fixes.md` § Process, `verification.md`, and the prompts):

- **A fix is not done when it merges — it is done when it survives the device.** Anything the build can't prove (share sheets, fonts, animations, reminders, notifications) goes on an explicit **V-list**, flagged unverified rather than assumed working. Born from F6 (green tests, invisible feature) and S3 (device-verified, then reopened).
- **Verify the mechanism, not the display**: read the DB (`W1`'s backdated `challenge_started_at`), count the forbidden calls (L1), decode the pixels (W4) — the display can be right for the wrong reason.
- **Device state is evidence.** Don't replace the installed build while verifications are pending ("if you replace what is on the tablet before he has run them, that evidence is gone"); never uninstall when a migration is under test; run reminder tests with vendor battery defaults untouched first — a failure there is a product finding.
- **Forcing procedures are executed before they're recorded** (the V5 lesson), and ordered against each other — fabricated state can destroy another item's evidence (W1 before U6).
- **The device-check matrix**: font scale 1.5/2.0, all themes, smallest rendered size, a real day-rollover.
- **Round mechanics**: one round file per device pass with a stable ID scheme; root-cause notes are the durable artifact ("closed rounds are kept for their root-cause notes, not their trackers"); reproduce-then-fix; one owner per defect; spent prompts get a HISTORICAL banner.
- **ADB tribal knowledge** (Android): `monkey` fails against a lock screen — use `am start -n`; permission prompts steal focus on launch; Flutter exposes nothing to uiautomator, so `screencap` is the only way to read the UI; a black screenshot means the device is locked.

This also gives `beta-versioning`'s V-list-shaped content a home and keeps `git-workflow` purely about git.

---

## 9. Router `CLAUDE.md` — one line

Universal Code Principles covers writing code; the project's dominant failure mode was *re-fixing*. One line, router-lean:

> - **A fix sweeps its blast radius** — root-cause first, then grep the constant, heal the shared widget (not the call site), and check the sibling surface, before calling it done.

Plus a Pointers entry for `device-verification` once it exists.

---

## 10. Priority order (by observed cost prevented)

1. **`clean-code` § Fixing a bug** (3.1) — would have prevented U6, the flame's 3 re-fixes, X8, and the round-over-round "fixes generating fixes" pattern. Highest leverage.
2. **`clean-code` § Testing effects** (3.2) — F6, S1, X9b, L5, X12 were all unit-testable and all missed for the same reason.
3. **`flutter-mvp` device-reality checklist** (4.1) — the largest defect class; two font-scale bugs shipped to a public beta.
4. **New `device-verification` skill** (8) — biggest knowledge-preservation win for the *next* project.
5. **`clean-code` fakes rule** (3.3) — stops a 2× tax that compounds with every behavioral change.
6. Everything else (4.2–4.4, 5, 6, 7, 9) — cheap, one paragraph each.

---

*Sources: git history mining and round-doc mining performed on `master` @ `97d73b1`; operator feedback from the four session transcripts under `~/.claude/projects/-home-stresstech-Documents-JORGE-sw-pray/`. All SHAs and defect IDs cited are verifiable in `git log master` and `docs/plans/beta-fixes/`.*
