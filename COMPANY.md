# GenX Labs

Solo-operated consumer apps studio. AI does the labor; the operator does the judgment.

> This file is the canonical strategic reference for the company. Keep it lean.
> Detail lives in the linked playbook files, not here.

---

## Identity

- **Name:** GenX Labs
- **Operator:** Jorge (CEO / CTO / sole human)
- **Form:** Solopreneur with AI leverage. Headcount: 1.
- **Legal entity:** `toiminimi` (Finland — sole trader). Revisit `osakeyhtiö` at higher revenue.

## Mission

Build a small portfolio of focused consumer apps that solve specific, recurring human pains — operated by one person with AI as the primary leverage.

## Vision

A self-sustaining studio of 3–5 profitable apps, each requiring strategic input rather than daily labor.

## Strategy

- One app at a time. Ship before starting the next.
- Free-to-start. Monetize only after retention is proven.
- AI does the labor; the operator does the judgment.
- Distribution discipline before feature expansion. Rule of 100 for content. ASO for store presence.
- Each app stands alone. No shared platform until data demands it.
- Mobile and web are separate products for separate purposes. Never ports.

## Operating principles

- Cash flow before scale.
- Quality over quantity, especially in content.
- Phased discipline: simple now, structured as users arrive.
- Manual before semi-automated. Semi-automated before autonomous.
- Human in the loop for anything reputational. Especially for faith/finance apps where a bad auto-reply is unrecoverable.

---

## Lanes of work (current — headcount 1)

The company runs in four lanes, not four departments. Each lane is a workflow on a cadence, not an org chart slot.

### Build
Operator + Claude Code. One app at a time. CI is on; CD waits for real users.
- Active: prayer app (Flutter, Android, MVP).
- Detail: `~/projects/prayer-app/CLAUDE.md`

### Distribute
Operator scripts and records the content. Claude chops, captions, and repurposes. ASO is part of this lane. Manual for the first 90 days, then evaluate what's worth automating.
- Detail: `~/genx-labs/distribute/PLAYBOOK.md` *(to be written)*

### Listen
One feedback inbox per app. Manual triage at this stage. Bug reports flow into GitHub Issues via Claude.
- Detail: `~/genx-labs/listen/INBOX.md` *(to be written)*

### Operate
Legal, accounting, taxes, banking. Set up once. Touch quarterly.
- Detail: `~/genx-labs/operate/SETUP.md` *(to be written)*

---

## Lanes that don't exist yet

Do not build these until the trigger condition is met. Premature structure is procrastination dressed as strategy.

- Marketing research / new-app discovery
- Automated customer support agents
- Financial forecasting / planning
- Multi-app shared infrastructure
- Paid acquisition

## Trigger conditions to add structure

- **~100 active users on an app** → template the most common support replies. Still manual send.
- **~1,000 active users** → semi-automate first-touch triage. Human reviews before send for sensitive topics.
- **App at break-even** → scope the next app. Until then, no R&D.
- **Recurring content patterns visible** → automate chop/repurpose, never scripting.
- **Revenue > €40k/yr** *(or local VAT threshold)* → revisit `toiminimi` → `Oy` switch.

---

## Project portfolio

### Active
- **Prayer app** — Christian, gospel-centered, 21-day challenge. Flutter Android. MVP launch is the immediate priority.

### Backlog (do not start)
- **Budgeting app** — PSD2/AISP via Tink, Plaid, or GoCardless. Resume only after prayer app MVP launches and stabilizes.
- **Web / SEO projects** (Next.js) — after the mobile portfolio is established.

---

## Decisions log

Append-only. Date + decision + reason. Short.

- **2026-05-08** — Adopted "lanes of work" instead of departments. Solopreneur with AI doesn't need org-chart vocabulary.
- **2026-05-08** — Deferred customer support automation until ~100 active users. Reputational risk of auto-replies on a faith app outweighs the efficiency gain at zero scale.
- **2026-05-08** — Froze marketing research mandate until prayer app ships. No R&D before first product launches.
- **2026-05-08** — Adopted lean `CLAUDE.md` routing pattern. Strategic detail lives in referenced files, not inlined.
- **2026-05-08** — Registered as `toiminimi` (Finnish sole trader). Simpler/cheaper to start; revisit `Oy` at higher revenue.
