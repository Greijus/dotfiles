---
name: operator-surveys
description: How to ask the operator (Jorge) for input — ALWAYS as a tap-to-answer survey with options, recommendation first, in plain language, never as a free-text question. Use WHENEVER a question, decision, confirmation, product call, or "which way do you want this?" needs the operator's input in any GenX Labs session — mid-task, at a commit boundary, or in the last paragraph of a turn. Trigger before asking the operator anything at all, on "ask Jorge", "needs a decision", "open question", "shall I", "do you want", "let me know", or any moment you would otherwise end a message with a question mark.
---

# operator-surveys

The operator usually monitors long runs from a phone via remote control. He does not have time to read context, open files, or type paragraphs. Every question must be answerable with **one tap**.

## The rules

1. **First, try not to ask.** Resolve it from the plan, the specs, the code, or sensible defaults. He would rather trust your call than be interrupted. Ask only for: irreversible/destructive actions, genuine scope changes, or product taste calls the docs don't answer.
2. **Ask with the AskUserQuestion tool** (options + tap-to-answer), never as free text in a message. **This holds everywhere, including the end of a turn.** A question in your closing paragraph — "want me to push?", "shall I continue with X?", "let me know if you'd rather…" — is the same interruption wearing different clothes, and it is *worse* there: it cannot be tapped, so it costs him a typed reply. If you are about to end a message with a question mark, that question is a survey.
3. **Your recommendation goes first**, labeled `(Recommended)`. If you have no recommendation, you probably haven't thought about it enough to interrupt him.
4. **Explain super simply.** One or two short sentences of context, no jargon, no file paths, no IDs he'd have to look up. Write it so it makes sense with zero surrounding context — he may see only the question, not the conversation.
5. **Each option's description says what happens if he taps it** — the consequence, not the implementation.
6. **Batch questions.** If several decisions are pending, ask them in one survey (up to 4 questions), not a drip of interruptions.
7. **Don't block on nice-to-knows.** If the answer only affects polish, pick the recommended option yourself, proceed, and report what you chose so he can override later.

## Shape of a good question

> **Header:** Streak flame · **Question:** "The small flame on Home is hard to see on the gold card. How should we fix it?"
> 1. **White glyph with warm glow (Recommended)** — reads clearly on all themes; matches the design render.
> 2. **Bigger flame** — more visible but crowds the card.
> 3. **Leave as is** — ships unchanged.

Bad: "Should `_flameRamp` in streak_flame.dart gate on `size < 32` or use `LayoutBuilder` constraints?" — he cannot evaluate that from a phone; that call is yours.

## Don't stop when you could ask and keep going

A survey is not a stopping point. It is how you *stay* moving when one fork needs him.

- **Never end a turn to wait for an answer you did not ask for.** Reaching a commit boundary is not a reason to stop; work continues until the task is done or a survey is genuinely blocking.
- **Ask, then keep working on whatever the answer does not block.** Most decisions gate one branch of the work, not all of it.
- **Approvals already given stay given.** "Commit as you go", "resume the plan", "keep going" cover the whole run, not the next step. Re-asking is an interruption you were told you didn't need.
- **Two things always go in a survey rather than a closing sentence**, because they are the ones most often smuggled into prose: *pushing / anything outward-facing*, and *"which of these should I do next?"*.
