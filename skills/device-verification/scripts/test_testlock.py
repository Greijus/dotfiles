#!/usr/bin/env python3
"""Cases testlock itself must get right.

Run: python3 skills/device-verification/scripts/test_testlock.py

2026-11-04: `testlock run checkout -C <a non-git dir>` named its lock "" and its cleanup ran
`rm -rf` on the lock root, deleting a live gate's checkout lock and slot. A run that cannot name
its lock must refuse, and must leave every other lock where it was.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTLOCK = Path(__file__).resolve().parent / "testlock"


def run(args, root, cwd=None):
    env = dict(os.environ, TESTLOCK_DIR=str(root), TESTLOCK_SLOTS="4", TESTLOCK_MAX_LOAD="999")
    return subprocess.run([str(TESTLOCK), *args], env=env, cwd=cwd, capture_output=True, text=True)


def test_non_git_dir_refuses_and_keeps_other_locks():
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as plain:
        other = Path(root) / "checkout_some_other_tree"
        other.mkdir()
        (other / "info").write_text(f"owner=gate\npid={os.getpid()}\n")

        result = run(["run", "checkout", "--owner", "t", "-C", plain, "--", "true"], root)

        assert result.returncode == 2, (result.returncode, result.stderr)
        assert "not in a git checkout" in result.stderr, result.stderr
        assert Path(root).is_dir(), "the lock root was deleted"
        assert (other / "info").is_file(), "another session's live lock was deleted"


def test_git_dir_still_runs():
    with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as repo:
        subprocess.run(["git", "init", "-q", repo], check=True)

        result = run(["run", "checkout", "--owner", "t", "-C", repo, "--", "true"], root)

        assert result.returncode == 0, (result.returncode, result.stderr)


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if failed else 0)
