# hooks

Rules the harness **enforces**, rather than rules a session is asked to remember.

A skill is read-time advice: it shapes what gets written when it happens to load, and has no
purchase on a session that skipped it. A hook runs whether or not anything read anything. So the
split is the one `clean-code` § Enforce it, don't document it names — anything mechanically
checkable moves here, and prose keeps the judgement calls.

| Hook | Event | What it does |
|---|---|---|
| `block-history-damage.py` | `PreToolUse` · Bash | **Refuses** the two operations that damage history irreversibly: a commit carrying the forbidden co-author trailer (inline `-m`, or hidden in a `-F` message file), and a squash merge. Both are absolute in CLAUDE.md, and both are a two-token check. |
| `review-before-stop.sh` | `Stop` | One self-review pass against `checklist.md` before the turn ends. |

## Tokenize, don't grep

`block-history-damage.py` parses the command with `shlex` and acts only on a `git` token in
**command position**. The first draft grepped the command string and produced two false positives
within a minute: it refused a heredoc that merely *described* these rules, then refused its own
test harness, whose JSON payload contained the forbidden text inside quotes. A regex cannot tell
shell syntax from quoted data.

`python3 hooks/test_block_history_damage.py` covers both directions — 20 cases, and the **allow**
cases are the ones that matter. A gate that blocks legitimate work gets switched off, and then it
protects nothing.

## The Stop hook is deliberately scoped

It fires only when the **working tree changed since the last review in this session** — keyed on
`git status --porcelain` plus HEAD, per session id, under `$TMPDIR/claude-stop-review/`. So it
stays silent on conversational turns and on a clean tree, and costs one extra round-trip per batch
of real edits rather than one per turn. It honours `stop_hook_active`, so the re-prompted turn
always completes.

## checklist.md holds judgement calls only

An item earns its place only while no tool can catch it. **The day a lint, a CI step or a test can
check something on that list, move it there and delete the line** — otherwise this becomes another
document nobody's tooling reads, which is the exact failure it exists to prevent.

## Per-machine setup

Run once from the dotfiles repo, alongside the skills symlink:

```bash
ln -s "$PWD/hooks" ~/.claude/hooks
```

Then wire them in `~/.claude/settings.json`. That file is per-machine and **not** in this repo, so
the second machine needs this block added by hand:

```json
"hooks": {
  "PreToolUse": [
    { "matcher": "Bash",
      "hooks": [{ "type": "command", "command": "\"$HOME\"/.claude/hooks/block-history-damage.py" }] }
  ],
  "Stop": [
    { "hooks": [{ "type": "command", "command": "\"$HOME\"/.claude/hooks/review-before-stop.sh",
                  "statusMessage": "Reviewing against the checklist" }] }
  ]
}
```

No `if:` filter on the `PreToolUse` entry, on purpose: an `if` of `Bash(git *)` would miss a
compound command that reaches git after a `cd`, and the script already exits immediately on
anything that is not a commit or a merge. A blocker that silently fails to fire is worse than the
cost of running it.

Verify with `/hooks`, or by attempting a squash merge on a throwaway branch — it should be refused
before git runs.
