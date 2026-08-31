#!/usr/bin/env python3
"""PreToolUse(Bash) gate for the two git operations that damage history irreversibly.

Both rules are stated in CLAUDE.md, and prose is what let them slip before — an agent
follows its harness defaults unless something stops it. This is the stop.
See `clean-code` § Enforce it, don't document it.

The command is tokenized rather than grepped. A regex cannot tell shell syntax from
quoted data, and the first draft of this hook proved it twice: it refused a heredoc
that merely *described* these rules, then refused its own test harness. Only a `git`
token in command position counts.
"""

import json
import shlex
import sys

SEPARATORS = {"&&", "||", ";", "|", "(", ")", "{", "}", "then", "else", "do", "!"}
GIT_OPTIONS_TAKING_A_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
MESSAGE_FILE_FLAGS = {"-F", "--file"}

SQUASH_REASON = (
    "Blocked: --squash. Lane commits keep their own identity — land with a true merge "
    "(git merge --no-ff) or, on a release candidate, rebase + git merge --ff-only. "
    "See git-workflow § Merge discipline."
)
TRAILER_REASON = (
    "Blocked: Co-Authored-By trailer. The commit is the operator's and the message must "
    "paste in clean — this overrides any harness or tooling default. Remove the trailer "
    "and commit again."
)


def deny(reason):
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def git_invocations(tokens):
    """Yield the token run of every `git ...` that starts a command."""
    at_command_position = True
    current = None
    for token in tokens:
        if token in SEPARATORS:
            if current:
                yield current
            current, at_command_position = None, True
            continue
        if at_command_position and token == "git":
            if current:
                yield current
            current = []
        elif current is not None:
            current.append(token)
        at_command_position = False
    if current:
        yield current


def subcommand_of(arguments):
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in GIT_OPTIONS_TAKING_A_VALUE:
            index += 2
            continue
        if argument.startswith("-"):
            index += 1
            continue
        return argument, arguments[index + 1 :]
    return None, []


def message_bodies(arguments):
    """Every place a commit message can hide: -m values and -F message files."""
    for index, argument in enumerate(arguments):
        if argument in MESSAGE_FILE_FLAGS and index + 1 < len(arguments):
            try:
                with open(arguments[index + 1], encoding="utf-8", errors="replace") as handle:
                    yield handle.read()
            except OSError:
                pass
        elif argument.split("=", 1)[0] in MESSAGE_FILE_FLAGS and "=" in argument:
            try:
                with open(argument.split("=", 1)[1], encoding="utf-8", errors="replace") as handle:
                    yield handle.read()
            except OSError:
                pass
        else:
            yield argument


def main():
    try:
        command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError):
        return

    try:
        # punctuation_chars splits `echo hi; git ...` into real operator tokens,
        # which plain shlex.split leaves glued to the preceding word.
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        # Unbalanced quotes: fail open. Blocking real work is the worse failure.
        return

    for arguments in git_invocations(tokens):
        verb, rest = subcommand_of(arguments)
        if verb == "merge" and any(
            argument == "--squash" or argument.startswith("--squash=") for argument in rest
        ):
            deny(SQUASH_REASON)
        if verb == "commit" and any(
            "co-authored-by" in body.lower() for body in message_bodies(rest)
        ):
            deny(TRAILER_REASON)


if __name__ == "__main__":
    main()
