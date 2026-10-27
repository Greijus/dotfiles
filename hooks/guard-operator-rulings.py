#!/usr/bin/env python3
"""PreToolUse(Bash) gate: a commit that changes an operator ruling's line records the ask.

`clean-code` § A ruling becomes a test that names it: an operator ruling is pinned by an
assertion whose `reason:` (or a comment on it) carries `operator ruling <id> <YYYY-MM-DD>:
"<quote>"`. Removing or rewriting that line reverses or narrows a decision that is the
operator's, so the commit body must say the operator was asked, one line per ruling id:

    Operator ruling changed: <id>, asked <YYYY-MM-DD>

Added lines pass freely, and so does a tagged line moved or re-indented unchanged.

Why: pray-app `3cb6230d` (2026-08-25) reversed the R9-4 ruling "the daypart stays a pure
wall-clock read" without asking and pinned the reversal in a test. It shipped from 1.0b10 on.

Tokenized like block-history-damage.py (its helpers are reused): only a `git` in command
position counts. Fails open on anything it cannot read — no repo, no HEAD, a git error.
"""

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "block_history_damage", Path(__file__).resolve().parent / "block-history-damage.py"
)
history = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(history)

RULING = re.compile(r"operator ruling\s+([^\s:]+)\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
ASKED = re.compile(
    r"^Operator ruling changed:\s*([^\s,]+),\s*asked\s+\d{4}-\d{2}-\d{2}\s*$", re.IGNORECASE | re.MULTILINE
)
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
COMMIT_OPTIONS_TAKING_A_VALUE = {
    "-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c", "--reedit-message",
    "-t", "--template", "--author", "--date", "--cleanup", "--fixup", "--squash", "--trailer",
    "--pathspec-from-file",
}
REUSED_MESSAGE_FLAGS = {"-C", "--reuse-message", "-c", "--reedit-message"}


def git(directory, *args):
    result = subprocess.run(
        ["git", "-C", directory, *args], capture_output=True, text=True, timeout=10, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def commits(tokens, cwd):
    """Yield (directory, commit arguments) for every `git commit`, following `cd` and `git -C`."""
    directory, at_command_position, index = cwd, True, 0
    while index < len(tokens):
        token = tokens[index]
        if token in history.SEPARATORS:
            at_command_position = True
        elif at_command_position and token == "cd" and index + 1 < len(tokens):
            directory = str(Path(directory, os.path.expanduser(tokens[index + 1])))
            index += 1
            at_command_position = False
        elif at_command_position and token == "git":
            end = index + 1
            while end < len(tokens) and tokens[end] not in history.SEPARATORS:
                end += 1
            arguments, target = tokens[index + 1 : end], directory
            while len(arguments) >= 2 and arguments[0] == "-C":
                target, arguments = str(Path(target, arguments[1])), arguments[2:]
            verb, rest = history.subcommand_of(arguments)
            if verb == "commit":
                yield target, rest
            index, at_command_position = end, False
            continue
        else:
            at_command_position = False
        index += 1


def commit_shape(arguments):
    """(commits every tracked change, amends, pathspecs, reused-message commits)."""
    everything = amend = False
    pathspecs, reused = [], []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            pathspecs += arguments[index + 1 :]
            break
        if argument in COMMIT_OPTIONS_TAKING_A_VALUE:
            if argument in REUSED_MESSAGE_FLAGS and index + 1 < len(arguments):
                reused.append(arguments[index + 1])
            index += 2
            continue
        if argument == "--all":
            everything = True
        elif argument == "--amend":
            amend = True
        elif re.fullmatch(r"-[A-Za-z]+", argument):
            cluster = re.match(r"-[^mFCct]*", argument).group(0)
            everything = everything or "a" in cluster
            if len(cluster) == len(argument) - 1:  # `-am msg`: the last flag takes the next word
                if argument[-1] in "Cc" and index + 1 < len(arguments):
                    reused.append(arguments[index + 1])
                index += 1
        elif not argument.startswith("-"):
            pathspecs.append(argument)
        index += 1
    return everything, amend, pathspecs, reused


def staged_diff(directory, arguments):
    everything, amend, pathspecs, _ = commit_shape(arguments)
    base = "HEAD"
    if amend:
        try:
            git(directory, "rev-parse", "--verify", "-q", "HEAD^")
            base = "HEAD^"
        except RuntimeError:
            base = EMPTY_TREE
    options = ["diff", "-U0", "--no-color", "--no-ext-diff", "-M"]
    if everything or pathspecs:
        return git(directory, *options, base, "--", *pathspecs)
    return git(directory, *options, "--cached", base)


def changed_rulings(diff):
    """{ruling id: file} for every tagged line the diff removes and does not re-add verbatim."""
    removed, added, path, in_hunk = [], set(), "?", False
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            in_hunk = False
        elif not in_hunk and line.startswith("--- "):
            path = line[4:].removeprefix("a/")
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("-"):
            removed.append((line[1:].strip(), path))
        elif in_hunk and line.startswith("+"):
            added.add(line[1:].strip())
    return {
        match.group(1): path
        for text, path in removed
        if text not in added
        for match in RULING.finditer(text)
    }


def messages(directory, arguments):
    yield from history.message_bodies(arguments)
    _, amend, _, reused = commit_shape(arguments)
    for commit in reused + (["HEAD"] if amend else []):
        try:
            yield git(directory, "log", "-1", "--format=%B", commit)
        except RuntimeError:
            pass


def reason(unasked):
    touched = ", ".join(f"{ruling} ({path})" for ruling, path in sorted(unasked.items()))
    asks = " / ".join(f"Operator ruling changed: {ruling}, asked <YYYY-MM-DD>" for ruling in sorted(unasked))
    return (
        f"Blocked: this commit removes or rewrites an operator ruling's line — {touched}. Reversing "
        "or narrowing a recorded ruling is the operator's call: survey first (operator-surveys). "
        f"Once asked, put this in the commit body: {asks}. "
        "See clean-code § A ruling becomes a test that names it."
    )


def main():
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
        cwd = payload.get("cwd") or "."
    except (json.JSONDecodeError, AttributeError):
        return

    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return

    for directory, arguments in commits(tokens, cwd):
        try:
            rulings = changed_rulings(staged_diff(directory, arguments))
        except (RuntimeError, OSError, subprocess.SubprocessError):
            continue
        if not rulings:
            continue
        asked = {match.group(1) for body in messages(directory, arguments) for match in ASKED.finditer(body)}
        unasked = {ruling: path for ruling, path in rulings.items() if ruling not in asked}
        if unasked:
            history.deny(reason(unasked))


if __name__ == "__main__":
    main()
