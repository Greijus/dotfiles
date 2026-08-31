#!/usr/bin/env python3
"""Cases the blocker must get right, in both directions.

Run: python3 hooks/test_block_history_damage.py

The allow cases matter more than the deny ones. A gate that blocks legitimate work
gets switched off, and then it protects nothing — the first draft of this hook was
a regex, and it refused a heredoc that merely described the rules.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "block-history-damage.py"

TRAILER = "Co-Authored-By: Someone <someone@example.com>"


def cases(message_file_with_trailer, clean_message_file):
    return [
        # (name, command, expected)
        ("plain commit", 'git commit -m "feat: x"', "allow"),
        ("inline trailer", f'git commit -m "feat: x\n\n{TRAILER}"', "deny"),
        ("trailer in -F file", f"git commit -F {message_file_with_trailer}", "deny"),
        ("trailer in --file=", f"git commit --file={message_file_with_trailer}", "deny"),
        ("clean -F file", f"git commit -F {clean_message_file}", "allow"),
        ("squash", "git merge --squash feat/x", "deny"),
        ("squash after cd", "cd /repo && git merge --squash feat/x", "deny"),
        ("squash after semicolon", "echo hi; git merge --squash feat/x", "deny"),
        ("backgrounded squash", "git merge --squash x &", "deny"),
        ("subshell squash", "(cd /r && git merge --squash x)", "deny"),
        ("no-ff merge", "git merge --no-ff feat/x", "allow"),
        ("ff-only merge", "git merge --ff-only rc/1.0b11", "allow"),
        ("git -C commit, clean", 'git -C /r commit -m "fix: y"', "allow"),
        ("grep for the flag", 'grep -rn "merge --squash" skills/', "allow"),
        (
            "prose in a heredoc",
            "cat > R.md <<EOF\nRefuses a git commit carrying a "
            f"{TRAILER} trailer, and any git merge --squash.\nEOF",
            "allow",
        ),
        (
            "heredoc body starting with git",
            f'cat > R.md <<EOF\ngit commit -m "x\n\n{TRAILER}"\nEOF',
            "allow",
        ),
        ("quoted json argument", 'run \'{"command":"cd /r && git merge --squash x"}\'', "allow"),
        ("unbalanced quotes fail open", 'git commit -m "oops', "allow"),
        ("piped git", "git log --oneline | head -3", "allow"),
        ("not git at all", "echo git merge --squash", "allow"),
    ]


def decision_for(command):
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        return "allow"
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


def main():
    with tempfile.TemporaryDirectory() as directory:
        with_trailer = Path(directory) / "with-trailer.txt"
        with_trailer.write_text(f"feat: x\n\nbody\n\n{TRAILER}\n", encoding="utf-8")
        clean = Path(directory) / "clean.txt"
        clean.write_text("feat: x\n\nbody\n", encoding="utf-8")

        failures = 0
        for name, command, expected in cases(with_trailer, clean):
            actual = decision_for(command)
            passed = actual == expected
            failures += not passed
            print(f"{'PASS' if passed else 'FAIL'}  {name:32s} expected={expected:5s} got={actual}")

        total = len(cases(with_trailer, clean))
        print(f"\n{total - failures}/{total} passed")
        return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
