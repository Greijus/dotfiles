- **Scope** — did you change only what was asked? Unrelated edits belong in their own change.
- **Tests** — every new behaviour ships a test in the same change, asserting the effect a user
  can feel, not that the artifact exists.
- **Blast radius** — a fix swept its cause: grep the constant, heal the shared widget rather than
  the call site, check the sibling surface.
- **Trackers** — plan tables say what actually landed: `⊡` for started, never `☐` for half-built.
- **Docs** — the spec, comment or map describing the behaviour you changed moved in the same diff.
- **Delegation** — nothing was committed, pushed or merged that the operator did not ask for.

If an item here could be a lint, a CI step or a test, move it there and delete the line.
