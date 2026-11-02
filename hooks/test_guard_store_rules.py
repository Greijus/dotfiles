#!/usr/bin/env python3
"""Cases the store-rule guard must get right, in both directions.

Run: python3 hooks/test_guard_store_rules.py

Each case builds a throwaway repo, makes one change, and asks the hook about one command. The
allow cases matter as much as the deny ones: a gate that blocks a document or a removal gets
switched off.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "guard-store-rules.py"

# Assembled, so editing this file never trips the guard on the dotfiles repo itself.
PLAY_FIELD = "obfuscated" + "AccountId"
PLAY_SETTER = "setObfuscated" + "ProfileId"
FLUTTER_FIELD = "applicationUser" + "Name"
STOREKIT_FIELD = "appAccount" + "Token"
CLEARED = "Store rule cleared: a hashed account id, asked 2026-11-02"


def run(directory, *args):
    subprocess.run(["git", "-C", str(directory), *args], check=True, capture_output=True, text=True)


def seed(directory):
    run(directory, "init", "-q")
    run(directory, "config", "user.email", "t@example.com")
    run(directory, "config", "user.name", "t")
    (directory / "billing.dart").write_text("void buy() {\n  launch();\n}\n")
    (directory / "old.dart").write_text(f"final a = 1;\nfinal {FLUTTER_FIELD} = null;\nfinal b = 2;\n")
    run(directory, "add", ".")
    run(directory, "commit", "-q", "-m", "seed")


def write(directory, name, text, stage=True):
    (directory / name).write_text(text)
    if stage:
        run(directory, "add", name)


def add_field(directory, field=FLUTTER_FIELD, name="billing.dart", stage=True):
    write(directory, name, f"void buy() {{\n  launch({field}: plan);\n}}\n", stage)


def verdict(directory, command, cd=False):
    payload = {"tool_input": {"command": command}, "cwd": str(directory.parent if cd else directory)}
    result = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True, check=True
    )
    return "deny" if '"deny"' in result.stdout else "allow"


def case_flutter_field(d):
    add_field(d)
    return "deny", 'git commit -m "feat: tag the purchase"'


def case_play_field_in_kotlin(d):
    add_field(d, PLAY_FIELD, "Billing.kt")
    return "deny", 'git commit -m "feat: x"'


def case_play_setter(d):
    add_field(d, PLAY_SETTER, "Billing.java")
    return "deny", 'git commit -m "feat: x"'


def case_storekit_field(d):
    add_field(d, STOREKIT_FIELD, "Store.swift")
    return "deny", 'git commit -m "feat: x"'


def case_commit_all(d):
    add_field(d, stage=False)
    return "deny", 'git commit -am "feat: x"'


def case_pathspec(d):
    add_field(d, stage=False)
    return "deny", 'git commit -m "feat: x" -- billing.dart'


def case_amend(d):
    add_field(d)
    run(d, "commit", "-q", "-m", "first")
    return "deny", 'git commit --amend -m "second"'


def case_after_cd(d):
    add_field(d)
    return "deny", f'cd {d.name} && git commit -m "feat: x"', True


def case_ask_with_no_date(d):
    add_field(d)
    return "deny", 'git commit -m "feat: x" -m "Store rule cleared: a hashed id"'


def case_ask_with_nothing_named(d):
    add_field(d)
    return "deny", 'git commit -m "feat: x" -m "Store rule cleared: , asked 2026-11-02"'


def case_cleared(d):
    add_field(d)
    return "allow", f'git commit -m "feat: x" -m "{CLEARED}"'


def case_cleared_in_a_message_file(d):
    add_field(d)
    (d.parent / "message.txt").write_text(f"feat: x\n\n{CLEARED}\n")
    return "allow", f"git commit -F {d.parent / 'message.txt'}"


def case_unrelated_change(d):
    write(d, "billing.dart", "void buy() {\n  launchNow();\n}\n")
    return "allow", 'git commit -m "fix: x"'


def case_document(d):
    write(d, "notes.md", f"Play's {PLAY_FIELD} is a hashed user id.\n")
    return "allow", 'git commit -m "docs: x"'


def case_removed(d):
    write(d, "old.dart", "final a = 1;\nfinal b = 2;\n")
    return "allow", 'git commit -m "fix: drop the tag"'


def case_moved(d):
    write(d, "old.dart", f"final a = 1;\nfinal b = 2;\nfinal {FLUTTER_FIELD} = null;\n")
    return "allow", 'git commit -m "style: reorder"'


def case_named_only_in_the_message(d):
    write(d, "billing.dart", "void buy() {\n  launchNow();\n}\n")
    return "allow", f'git commit -m "fix: never use {PLAY_FIELD}"'


def case_not_a_commit(d):
    add_field(d)
    return "allow", "git status"


def case_quoted_mention(d):
    add_field(d)
    return "allow", "echo 'git commit -m x'"


CASES = [value for name, value in sorted(globals().items()) if name.startswith("case_")]


def main():
    failures = 0
    for case in CASES:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "repo"
            directory.mkdir()
            seed(directory)
            expected, command, *cd = case(directory)
            actual = verdict(directory, command, bool(cd))
            if actual != expected:
                failures += 1
                print(f"FAIL {case.__name__}: expected {expected}, got {actual}")
    print(f"{len(CASES) - failures}/{len(CASES)} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
