#!/usr/bin/env python3
"""Cases the testlock gate must get right, in both directions.

Run: python3 hooks/test_require_testlock.py

As with the history blocker, the allow cases matter most: a gate that refuses a grep or
a screenshot gets switched off, and then it protects nothing.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "require-testlock.py"
SESSION = "session-me"
SERIAL = "T1"


def write_lock(root, name, session, expires_in=600, pid=""):
    lock = root / name
    lock.mkdir(parents=True, exist_ok=True)
    (lock / "info").write_text(
        f"owner=someone\nsince={int(time.time())}\nexpires={int(time.time()) + expires_in}\n"
        f"pid={pid}\nsession={session}\nwhat=lease\n",
        encoding="utf-8",
    )


def decision_for(command, cwd, lock_root):
    env = dict(os.environ, TESTLOCK_DIR=str(lock_root), ANDROID_SERIAL=SERIAL)
    env.pop("TESTLOCK_ENFORCE", None)
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"session_id": SESSION, "cwd": str(cwd), "tool_input": {"command": command}}),
        capture_output=True, text=True, check=False, env=env,
    )
    if not result.stdout.strip():
        return "allow"
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


def checkout_name(repo):
    top = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return "checkout" + "".join(c if c.isalnum() or c in "._-" else "_" for c in top)


def main():
    failures = total = 0
    with tempfile.TemporaryDirectory() as scratch:
        repo = Path(scratch) / "repo"
        (repo / "mobile").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        device = f"device-{SERIAL}"
        checkout = checkout_name(repo)

        # (name, command, locks to set up [(name, session, expires_in, pid)], expected)
        cases = [
            ("git status", "git status", [], "allow"),
            ("flutter --version", "flutter --version", [], "allow"),
            ("flutter doctor", "flutter doctor", [], "allow"),
            ("grep for the command", 'grep -rn "flutter test" skills/', [], "allow"),
            ("echo mentions it", "echo flutter test", [], "allow"),
            ("heredoc prose", "cat > R.md <<EOF\nflutter test and adb install\nEOF", [], "allow"),
            ("dart format", "dart format lib", [], "allow"),
            ("wrapped suite", "testlock run checkout --owner a -C mobile -- flutter test", [], "allow"),
            ("wrapped by full path", "~/.claude/skills/device-verification/scripts/testlock run checkout --owner 'rc/x:suite' -- flutter test", [], "allow"),
            ("cd then wrapped", "cd mobile && testlock run checkout --owner a -- flutter analyze", [], "allow"),
            ("adb devices", "adb devices", [], "allow"),
            ("screencap", "adb exec-out screencap -p > shot.png", [], "allow"),
            ("dumpsys", "adb shell dumpsys battery", [], "allow"),
            ("quoted read-only pipe", 'adb shell "dumpsys activity | grep mResumed"', [], "allow"),
            ("logcat with serial", "adb -s T1 logcat -d", [], "allow"),
            ("pm list", "adb shell pm list packages", [], "allow"),
            ("pull", "adb pull /sdcard/x.png", [], "allow"),
            ("own device lease: install", "adb install app.apk", [(device, SESSION, 600, "")], "allow"),
            ("own device lease: tap", "adb shell input tap 10 20", [(device, SESSION, 600, "")], "allow"),
            ("own checkout lease: suite", "cd mobile && flutter test", [(checkout, SESSION, 600, "")], "allow"),
            ("lease + wrapped install", "testlock run checkout --owner a -- flutter install", [(device, SESSION, 600, "")], "allow"),
            ("wrapped device command", "testlock run device --owner a -- adb install app.apk", [], "allow"),
            ("unbalanced quotes fail open", 'flutter test "oops', [], "allow"),

            ("bare suite", "flutter test", [], "deny"),
            ("cd then suite", "cd mobile && flutter test", [], "deny"),
            ("single test file", "flutter test test/foo_test.dart", [], "deny"),
            ("full-path flutter build", "/home/jorge/flutter/bin/flutter build apk --debug", [], "deny"),
            ("timeout prefix", "timeout 600 flutter test", [], "deny"),
            ("env assignment prefix", "FOO=1 flutter analyze", [], "deny"),
            ("pub get", "flutter pub get", [], "deny"),
            ("build_runner", "dart run build_runner build", [], "deny"),
            ("after semicolon", "echo go; flutter test", [], "deny"),
            ("subshell", "(cd mobile && flutter test)", [], "deny"),
            ("adb install", "adb install app.apk", [], "deny"),
            ("adb tap", "adb shell input tap 10 20", [], "deny"),
            ("adb am start", "adb shell am start -n a/b", [], "deny"),
            ("quoted keyevent", 'adb shell "input keyevent 4"', [], "deny"),
            ("adb uninstall with serial", "adb -s T1 uninstall com.x", [], "deny"),
            ("wrapped install without device lease", "testlock run checkout --owner a -- flutter install", [], "deny"),
            ("other session's device lease", "adb install app.apk", [(device, "session-other", 600, "")], "deny"),
            ("own lease expired", "adb install app.apk", [(device, SESSION, -5, "")], "deny"),
            ("own run-held checkout", "cd mobile && flutter test", [(checkout, SESSION, 0, "12345")], "deny"),
            ("other session's checkout lease", "cd mobile && flutter test", [(checkout, "session-other", 600, "")], "deny"),
        ]

        for name, command, locks, expected in cases:
            lock_root = Path(scratch) / f"locks-{total}"
            lock_root.mkdir()
            for lock_name, session, expires_in, pid in locks:
                write_lock(lock_root, lock_name, session, expires_in, pid)
            actual = decision_for(command, repo, lock_root)
            passed = actual == expected
            failures += not passed
            total += 1
            print(f"{'PASS' if passed else 'FAIL'}  {name:40s} expected={expected:5s} got={actual}")

    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
