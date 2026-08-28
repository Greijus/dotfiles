# Scoring rubric

Half-point granularity, 1–5. **Every score cites the evidence that set it** — a number from
`measurement-recipes.md`, a named file, or a finding id. A score with no citation is an opinion
and will not survive the re-score.

Carry three columns through the whole cycle: **was · predicted · measured after**.

## The default axes

**SOLID** — score the five sub-axes separately, then average into one headline number. Show the
sub-scores inline (`SRP 4 · OCP 4 · LSP 3 · ISP 5 · DIP 4`), because the average hides which one
moved. Smells and fixes per principle → `clean-code` § SOLID; do not re-derive them here.

| Axis | What sets it | Typical evidence |
|---|---|---|
| **Coupling & layering** | Do the layer rules hold, and is anything *checking* them? | Import-graph scan: cross-feature edges, widget→db imports, `Impl` types constructed outside DI |
| **Maintainability** | Can a stranger change this safely? Lint strictness, formatter state, file/function sizes | Analyzer config, formatter drift, files over the project's line rule |
| **Extensibility** | What does adding the next feature of the same kind cost? | Number of edits a new field/case/screen requires today |
| **Testing** | Ratio, and whether the tests assert effects | test:lib line ratio, suite count, coverage if measured, contract suites, presence of `clean-code` § Assert the effect failures |
| **Documentation** | Comments explaining *why*, specs that match code | Spot-read the densest module; comments that state behaviour must be backed by tests |
| **Failure handling** | Where does a throw go? What does the user see? | Bare vs typed catch census, top-level handlers, launch path guarded, reasons discarded |
| **Design-system fidelity** | Are tokens named and followed, or held in one head? | Raw literal census vs named constants, on-grid percentage, type-scale overrides |
| **Build & release hygiene** | Does CI prove what shipping needs? | CI steps vs the gates the project claims, build/artifact step, version stamping |

## Half points mean something

- **5** — holds *and is enforced*. Nothing can silently regress it.
- **4.5** — holds, enforced, with one named acceptable gap.
- **4** — holds by discipline; nothing checks it. This is the most common real score, and the
  enforcement gap is the finding.
- **3** — real defect present, contained and known.
- **≤2** — actively costing changes now.

## Ceiling notes are mandatory where they apply

An axis that **cannot structurally reach 5** says so, with the constraint that caps it:

> Failure handling caps at **4.5** — real crash reporting needs a backend, which the local-only
> rule forbids.

Without the note, the next audit reads 4.5 as an open task and someone re-litigates a settled
constraint.

## A priced trade is not a defect

Some things score below 5 **on purpose**. Dock the axis, keep the design, and say what was bought:

> DIP stays at **4** — 49 `sl<T>()` sites inside widgets are hidden dependencies, *and* they are
> why the widget tests are cheap (`GetIt.reset()` + one fake is the whole setup). A priced trade,
> documented in `service_locator.dart`'s own header.

Test: can you name what the trade buys, and where it is written down? If not, it is a finding.

## Adding and dropping axes

The list is a strong default, not a straitjacket.

- **Drop** an axis the project has no surface for (design-system fidelity on a CLI).
- **Add** one where a whole risk class lives that no axis would score: data migration, security &
  privacy, i18n, performance, accessibility, dependency health.
- **Say in the doc which you changed and why.** An audit that silently uses different axes than
  the last one cannot be compared to it — and comparability across re-audits is most of the value.

## Worked example — pray-app, 2026-08-21 → 2026-08-27

| Axis | Was | Predicted | Measured after | What moved it |
|---|---|---|---|---|
| SOLID (SRP 4→4.5 · OCP 4→5 · LSP 3→4.5 · ISP 5 · DIP 4) | 4.0 | 4.7 | **4.6** | findings 3, 4, 5 |
| Coupling & layering | 5.0 | 5.0 | **5.0** | now a gate, not discipline; frozen seam set can only shrink |
| Maintainability | 4.0 | 4.5 | **4.5** | analyzer hardened, formatter settled |
| Extensibility | 4.0 | 4.5 | **4.5** | new user state costs a narrow writer, not six edits and a race |
| Testing | 4.0 | 4.5 | **4.5** | +806 tests; still no coverage measurement |
| Documentation | 5.0 | 5.0 | **5.0** | — |
| Failure handling | 3.0 | 4.5 | **4.5** | device-verified; ceiling at 4.5 |
| Design-system fidelity | 3.5 | 4.5 | **4.5** | spacing named *and* gated |
| Build & release hygiene | 4.0 | 5.0 | **5.0** | CI gates format and proves an APK builds |
| **Overall** | **4.1** | **4.7** | **4.7** | |

**Where measured parted from predicted:** LSP reached 4.5, not 5. The rules now live once and a
shared contract suite runs against impl and fake — the actual defect — but the fakes got
*bigger*, because splitting one whole-row `save()` into six narrow writers correctly grew them.
The 150-line target was the wrong metric for the right goal. Recording that is the point of
re-scoring.
