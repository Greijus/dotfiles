---
name: operator-surveys
description: How to ask the operator (Jorge) for input mid-task — as a survey with options, recommendation first, in plain language. Use WHENEVER a question, decision, confirmation, or product call needs the operator's input during any GenX Labs session — especially long orchestration runs monitored via remote control. Trigger before asking the operator anything, on "ask Jorge", "needs a decision", "open question", or any moment you would otherwise write a free-text question.
---

# operator-surveys

The operator usually monitors long runs from a phone via remote control. He does not have time to read context, open files, or type paragraphs. Every question must be answerable with **one tap**.

## The rules

1. **First, try not to ask.** Resolve it from the plan, the specs, the code, or sensible defaults. He would rather trust your call than be interrupted. Ask only for: irreversible/destructive actions, genuine scope changes, or product taste calls the docs don't answer.
2. **Ask with the AskUserQuestion tool** (options + tap-to-answer), never as free text in a message.
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
