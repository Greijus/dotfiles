#!/usr/bin/env python3
"""Cases the ruling guard must get right, in both directions.

Run: python3 hooks/test_guard_operator_rulings.py

Each case builds a throwaway repo whose HEAD holds a test pinned to an operator ruling, makes
one change, and asks the hook about one command. The allow cases matter as much as the deny
ones: a gate that blocks a re-indent or a new ruling gets switched off.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "guard-operator-rulings.py"

# Assembled, so editing this file never trips the guard on the dotfiles repo itself.
TAG = "operator " + "ruling"
RULING_LINE = f"    expect(daypart(at13), afternoon, reason: '{TAG} R9-4 2026-08-21: \"pure wall-clock\"');"
OTHER_LINE = "    expect(greeting(), isNotEmpty);"
ASK = "Operator ruling changed: R9-4, asked 2026-10-27"


def run(directory, *args):
    subprocess.run(["git", "-C", str(directory), *args], check=True, capture_output=True, text=True)


def seed(directory):
    run(directory, "init", "-q")
    run(directory, "config", "user.email", "t@example.com")
    run(directory, "config", "user.name", "t")
    (directory / "daypart_test.dart").write_text(f"void main() {{\n{RULING_LINE}\n{OTHER_LINE}\n}}\n")
    (directory / "notes.md").write_text(f"A prose mention of an {TAG} with no id.\n")
    run(directory, "add", ".")
    run(directory, "commit", "-q", "-m", "seed")


def edit(directory, old, new, stage=True):
    path = directory / "daypart_test.dart"
    path.write_text(path.read_text().replace(old, new))
    if stage:
        run(directory, "add", "daypart_test.dart")


def changed(directory, stage=True):
    edit(directory, "afternoon", "evening", stage)


def deleted(directory, stage=True):
    edit(directory, RULING_LINE + "\n", "", stage)


def moved(directory):
    edit(directory, f"{RULING_LINE}\n{OTHER_LINE}", f"{OTHER_LINE}\n{RULING_LINE}")


def added(directory):
    edit(directory, OTHER_LINE, f"{OTHER_LINE}\n{RULING_LINE.replace('R9-4', 'R22-1.1')}")


def unrelated(directory):
    edit(directory, "isNotEmpty", "isNot(isEmpty)")


def prose(directory):
    (directory / "notes.md").write_text("Rewritten.\n")
    run(directory, "add", "notes.md")


def amended_without_ask(directory):
    changed(directory)
    run(directory, "commit", "-q", "-m", "fix: the slot decides")


def amended_with_ask(directory):
    changed(directory)
    run(directory, "commit", "-q", "-m", f"fix: the clock decides\n\n{ASK}")


def cases(message_file_with_ask):
    return [
        # (name, change, command template, expected) — {repo} is the throwaway repo
        ("ruling changed, no ask", changed, 'git commit -m "fix: x"', "deny"),
        ("ruling deleted, no ask", deleted, 'git commit -m "fix: x"', "deny"),
        ("ruling changed, ask inline", changed, f'git commit -m "fix: x\n\n{ASK}"', "allow"),
        ("ruling changed, ask in -F", changed, f"git commit -F {message_file_with_ask}", "allow"),
        ("ask names another id", changed, f'git commit -m "fix: x\n\n{ASK.replace("R9-4", "R9-5")}"', "deny"),
        ("ask without a date", changed, 'git commit -m "fix: x\n\nOperator ruling changed: R9-4"', "deny"),
        ("ask in a heredoc message", changed,
         f"git commit -m \"$(cat <<'EOF'\nfix: x\n\n{ASK}\nEOF\n)\"", "allow"),
        ("new ruling added", added, 'git commit -m "test: pin R22-1.1"', "allow"),
        ("ruling line moved unchanged", moved, 'git commit -m "refactor: order"', "allow"),
        ("unrelated line in the same file", unrelated, 'git commit -m "test: x"', "allow"),
        ("prose mention without id removed", prose, 'git commit -m "docs: x"', "allow"),
        ("git -C from elsewhere", changed, 'git -C {repo} commit -m "fix: x"', "deny"),
        ("cd then commit", changed, 'cd {repo} && git commit -m "fix: x"', "deny"),
        ("-am commits the unstaged edit", lambda d: changed(d, stage=False), 'git commit -am "fix: x"', "deny"),
        ("pathspec commits the unstaged edit", lambda d: changed(d, stage=False),
         'git commit -m "fix: x" daypart_test.dart', "deny"),
        ("unstaged edit, plain commit", lambda d: changed(d, stage=False), 'git commit -m "docs: x"', "allow"),
        ("amend --no-edit, no ask", amended_without_ask, "git commit --amend --no-edit", "deny"),
        ("amend --no-edit, ask in HEAD", amended_with_ask, "git commit --amend --no-edit", "allow"),
        ("not a commit", changed, "git status --short", "allow"),
        ("commit mentioned in prose", changed, "echo git commit -m x", "allow"),
    ]


def decision_for(command, cwd):
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)}),
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        return "allow"
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


def main():
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        message_file = scratch / "message.txt"
        message_file.write_text(f"fix: x\n\n{ASK}\n", encoding="utf-8")
        elsewhere = scratch / "elsewhere"
        elsewhere.mkdir()

        failures = 0
        all_cases = cases(message_file)
        for number, (name, change, template, expected) in enumerate(all_cases):
            repo = scratch / f"repo{number}"
            repo.mkdir()
            seed(repo)
            change(repo)
            command = template.replace("{repo}", str(repo))
            cwd = elsewhere if "{repo}" in template else repo
            actual = decision_for(command, cwd)
            passed = actual == expected
            failures += not passed
            print(f"{'PASS' if passed else 'FAIL'}  {name:36s} expected={expected:5s} got={actual}")

        print(f"\n{'PASS' if decision_for('git commit -m x', elsewhere) == 'allow' else 'FAIL'}  not a repo fails open")
        failures += decision_for("git commit -m x", elsewhere) != "allow"
        total = len(all_cases) + 1
        print(f"\n{total - failures}/{total} passed")
        return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
