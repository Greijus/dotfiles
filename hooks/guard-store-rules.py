#!/usr/bin/env python3
"""PreToolUse(Bash) gate: a commit that adds a store's user-identity field records the ask.

Google Play and the App Store each give a purchase one field for a hashed ID of the user, read
for fraud detection. It is not storage. Any new use of one needs the operator's yes, whichever
way it is written, because a mistake here lands on the path that takes money. The body says so:

    Store rule cleared: <what it is for>, asked <YYYY-MM-DD>

Only added lines of source count, and not one that also moved out of the same diff. Documents
may name the fields freely. This guards the fields, not the principle: repurposing or disguising
anything else stays a judgement call (CLAUDE.md § What NOT to Do, checklist.md).

Why: pray-app `R26-1.1` (2026-11-02) stored the plan in Play's obfuscated account ID to show a
badge after a reinstall, then encoded it after the plugin docs warned against clear text. The
operator caught it before the upload: "Let's not take risks".

Reuses guard-operator-rulings.py for the command and the diff the commit will make. Fails open on
anything it cannot read — no repo, no HEAD, a git error.
"""

import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "guard_operator_rulings", Path(__file__).resolve().parent / "guard-operator-rulings.py"
)
rulings = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rulings)

# Spelled as patterns, so committing this file never trips the guard on the dotfiles repo itself.
FIELD = re.compile(
    r"\b(?:set)?obfuscated(?:Account|Profile)Id\b"  # Play Billing, in every binding
    r"|\bapplication_?user_?name\b"  # in_app_purchase (Flutter), SKPayment (StoreKit 1)
    r"|\bapp(?:Account)Token\b",  # StoreKit 2
    re.IGNORECASE,
)
DOCUMENT = re.compile(r"\.(?:md|markdown|txt|rst|adoc)$", re.IGNORECASE)
CLEARED = re.compile(r"^Store rule cleared:\s*\S.*,\s*asked\s+\d{4}-\d{2}-\d{2}\s*$", re.IGNORECASE | re.MULTILINE)


def added_fields(diff):
    """{field: file} for each store field on an added source line not also removed by the diff."""
    added, removed, path, in_hunk = [], set(), "?", False
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            in_hunk = False
        elif not in_hunk and line.startswith("+++ "):
            path = line[4:].removeprefix("b/")
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            added.append((line[1:].strip(), path))
        elif in_hunk and line.startswith("-"):
            removed.add(line[1:].strip())
    return {
        match.group(0): path
        for text, path in added
        if text not in removed and not DOCUMENT.search(path)
        for match in FIELD.finditer(text)
    }


def reason(fields):
    touched = ", ".join(f"{field} ({path})" for field, path in sorted(fields.items()))
    return (
        f"Blocked: this commit adds a store user-identity field — {touched}. That field is a hashed "
        "user ID read for fraud detection, on the path that takes money. Never use it to store "
        "anything else, and never encode a value to get past its rules. If a store limit blocks a "
        "feature, take the supported route or accept the limit. A new use is the operator's call: "
        "survey first (operator-surveys). Once they say yes, put this in the commit body: "
        "Store rule cleared: <what it is for>, asked <YYYY-MM-DD>"
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

    for directory, arguments in rulings.commits(tokens, cwd):
        try:
            fields = added_fields(rulings.staged_diff(directory, arguments))
        except (RuntimeError, OSError, subprocess.SubprocessError):
            continue
        if fields and not any(CLEARED.search(body) for body in rulings.messages(directory, arguments)):
            rulings.history.deny(reason(fields))


if __name__ == "__main__":
    main()
