#!/usr/bin/env bash
# Stop hook: one self-review pass against the checklist, before the turn ends.
#
# Scoped deliberately. It fires only when the working tree has CHANGED since the
# last review in this session — not on every turn — because a checklist that
# interrupts conversational turns gets ignored like any other prose.
#
# It holds judgement calls only. Anything a lint, a CI step or a test can catch
# belongs there instead; delete the item here the day that lands.

set -uo pipefail

payload=$(cat)

# The re-prompted turn must be allowed to finish, or the session loops forever.
[[ $(jq -r '.stop_hook_active // false' <<<"$payload") == "true" ]] && exit 0

project_directory=${CLAUDE_PROJECT_DIR:-$PWD}
git -C "$project_directory" rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

tree_state=$(
  git -C "$project_directory" status --porcelain
  git -C "$project_directory" rev-parse HEAD 2>/dev/null
)
# A clean tree with nothing new to review is not worth a round-trip.
[[ -n $(git -C "$project_directory" status --porcelain) ]] || exit 0

state_directory="${TMPDIR:-/tmp}/claude-stop-review"
mkdir -p "$state_directory"
session_id=$(jq -r '.session_id // "unknown"' <<<"$payload")
state_file="$state_directory/${session_id//[^A-Za-z0-9_-]/_}"
current_state=$(printf '%s' "$tree_state" | cksum)

[[ -f $state_file && $(cat "$state_file") == "$current_state" ]] && exit 0
printf '%s' "$current_state" > "$state_file"

checklist_file="$(dirname "$(readlink -f "$0")")/checklist.md"
[[ -r $checklist_file ]] || exit 0

jq -n --arg checklist "$(cat "$checklist_file")" '{
  decision: "block",
  reason: ("Before finishing, review the work you just left in the tree against these:\n\n" + $checklist)
}'
