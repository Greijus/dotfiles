---
name: store-compliance
description: Use this skill whenever planning, building, reviewing or releasing anything that touches a store-regulated surface — billing, subscriptions, purchases, prices or trials; permissions, the manifest or background and foreground services; user data, accounts, deletion or the Data safety form; SDKs; notifications; AI-generated content; health, safety or crisis content; or the store listing. Asks what the store's official page says an API is for before anything is built, records it as a Store check in the plan, and as the compliance entry the release gate reads. Trigger on "is this allowed", "Play policy", "App Store rules", "will Play reject", "compliance", "workaround", "store rules", or any plan item, diff or feature on those surfaces, including a clever way around a platform limit. NOT a legal opinion, and NOT the release's privacy gates, which are `play-release`.
---

# store-compliance

The cheapest place to catch a store problem is before the code exists. So the question comes first, at planning, and it is one question: **what does the store say this is for?**

*Why this exists: pray-app `R26-1.1` (2026-11-02) wanted a plan's name to survive a reinstall, stored it in Play's obfuscated account ID, then base64-encoded it after the plugin's docs warned against clear text. Two code reviews improved the workaround. Nobody asked what the field was for. It is a hashed user ID read for fraud detection, on the only path that takes money, for a badge. The operator stopped it: "Let's not take risks".*

## The check

Run it on any plan item or diff that touches a surface below. Read the **live official page**, in this session. Memory goes stale and policies change. A plugin's docs, a blog or a Stack Overflow answer are leads, never the source.

1. **What is it for?** Quote the official page on the API, field or permission you plan to use. If your use is not what it says, stop: that is repurposing, even when it works and no rule names it.
2. **Is there a supported route?** Name it, with its cost. If there is none, the honest answer may be to accept the limit.
3. **What fails if the store objects?** Say it plainly: rejection, a blocked purchase, an unpublished app. On the path that takes money the bar is highest, and a cosmetic gain never clears it.
4. **Does the disclosure still hold?** Privacy policy, Data safety, permissions declarations, Sign in details.

**A workaround is named as one, to the operator, before it is built.** Two tells: you are encoding, hashing or renaming something so a rule's wording no longer applies, or you are using a field whose documented purpose you have not read. A rule that does not forbid something in so many words is not a yes.

**The check can stop a plan.** Reading the page and finding the idea does not fit is the check working. Offer the supported route or the limit, by survey (`operator-surveys`).

## The surfaces

Links are starting points, confirmed 2026-11-02; read the page, not this table.

| Surface | Watch for | Official page |
|---|---|---|
| Anything | The policy index | [Developer Policy Center](https://play.google/developer-content-policy/) |
| Billing, in-app purchase | Play billing for digital goods, purchase-flow identifiers | [Payments](https://support.google.com/googleplay/android-developer/answer/9858738) · [Fight fraud and abuse](https://developer.android.com/google/play/billing/security) |
| Subscriptions, trials | Offer terms before purchase, cancellation, misleading price | [Subscriptions](https://support.google.com/googleplay/android-developer/answer/9900533) |
| Permissions, sensitive APIs | Each permission's allowed use, and its declaration | [Permissions and sensitive APIs](https://support.google.com/googleplay/android-developer/answer/9888170) |
| Foreground services, full-screen intents | Declared type, justification, video | [Foreground service requirements](https://support.google.com/googleplay/android-developer/answer/13392821) |
| User data, accounts | Disclosure, consent, deletion | [User Data](https://support.google.com/googleplay/android-developer/answer/10144311) |
| Data safety form, SDKs | What every SDK sends | [Data safety](https://support.google.com/googleplay/android-developer/answer/10787469) |
| Generated content | Reporting and safety for AI output | [AI-Generated Content](https://support.google.com/googleplay/android-developer/answer/14094294) |
| Apple, if a project ships there | Everything above has its own rule | [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) |

A surface that bites and is missing here earns a row, with its official link.

## Where it is enforced

A skill only helps a session that loads it, so each stage has something that does not depend on that.

| Stage | Forced by |
|---|---|
| **Planning** | `execution-planning` § Task anatomy: an item on a surface carries a `Store check:` line, and the plan is not ready without it |
| **Code** | `hooks/guard-store-rules.py` refuses a commit adding a store user-identity field. Add a field there when a new one bites |
| **Review** | A delta review of these paths reads this skill and answers the four questions, not only "is the code correct" |
| **Release** | `play-release`'s compliance gate refuses the cut when a project's `gates.compliance.paths` changed since the last release with no entry that cites an official page |

```
Store check: <surface> — "<what the official page says it is for>" (<URL>, read <date>).
Supported route: <this one, or which>. If the store objects: <what fails>. Disclosures: <unchanged, or which>.
```

The release entry is the same content for the diff being cut:

```
release.py compliance <version> "v1.0..HEAD billing: <what changed>; <URL> read <date>: <what it says>; disclosures unchanged"
```

## What this does not do

It lowers the risk of a rejection; it does not promise an approval. The store's review has the final say, policy can change after a release, and none of this is legal advice. When a question turns on what a law requires, or a rule stays unclear after reading the page, say so and ask the operator rather than settling it here.

## Not covered here

The privacy-policy, PRIV-1, SDK and secrets gates, and the Play Console steps → `play-release`. Scoring a whole codebase → `code-audit`. Diff correctness → the built-in `/code-review`.
