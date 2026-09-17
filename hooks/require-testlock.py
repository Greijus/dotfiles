#!/usr/bin/env python3
"""PreToolUse(Bash) gate: device and checkout work runs only under `testlock`.

Parallel sessions share one test device and, per checkout, one build/ and .dart_tool/.
`device-verification` § Sharing the device and the checkout says to take the lock; this
makes it true for a session that never loaded the skill.

A guarded command is allowed when either
  - it runs inside `testlock run <resource> ... -- <command>` (that resource is covered), or
  - this session holds a live lease on the resource (`testlock acquire`, stamped with
    the session id), and no other resource the command needs is missing.

Guarded:
  checkout  flutter test|build|run|install|drive|attach|pub|analyze|gen-l10n|clean,
            dart test|run|pub|analyze, gradlew
  device    flutter run|install|drive|attach, and every adb command that is not read-only

Tokenized like block-history-damage.py: only a command-position word counts, so prose,
heredocs and grep patterns that mention `flutter test` pass. Parse failures fail open.
Operator escape hatch: TESTLOCK_ENFORCE=0 in the environment Claude Code runs in.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

LOCK_ROOT = Path(os.environ.get("TESTLOCK_DIR", "/tmp/genx-testlocks"))
TESTLOCK_HELP = "~/.claude/skills/device-verification/scripts/testlock"

SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")", "{", "}", "then", "else", "do", "!", "\n"}
PREFIX_COMMANDS = {"time", "nohup", "nice", "stdbuf", "command", "exec"}

FLUTTER_CHECKOUT = {"test", "build", "run", "install", "drive", "attach", "pub", "analyze", "gen-l10n", "clean"}
FLUTTER_DEVICE = {"run", "install", "drive", "attach"}
DART_CHECKOUT = {"test", "run", "pub", "analyze"}

ADB_OPTIONS_TAKING_A_VALUE = {"-s", "-t", "-H", "-P", "-L"}
ADB_READ_ONLY = {
    "devices", "get-serialno", "get-state", "get-devpath", "version", "logcat",
    "pull", "wait-for-device", "help", "start-server", "bugreport",
}
SHELL_READ_ONLY = {
    "screencap", "screenrecord", "getprop", "dumpsys", "logcat", "ls", "cat", "ps", "id",
    "whoami", "df", "uptime", "echo", "grep", "head", "tail", "wc", "stat", "find", "top",
}
SHELL_READ_ONLY_PAIRS = {("pm", "list"), ("pm", "path"), ("settings", "get"), ("wm", "size"), ("wm", "density")}


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


def tokenize(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def simple_commands(tokens):
    current = []
    for token in tokens:
        if token in SEPARATORS or set(token) <= set(";&|()"):
            if current:
                yield current
            current = []
        else:
            current.append(token)
    if current:
        yield current


def strip_prefixes(words):
    """Drop VAR=value assignments and wrappers like `env`, `timeout 600`, `nice -n 5`."""
    index = 0
    while index < len(words):
        word = words[index]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", word):
            index += 1
        elif word == "env":
            index += 1
            while index < len(words) and (words[index].startswith("-") or "=" in words[index]):
                index += 1
        elif word == "timeout":
            index += 1
            while index < len(words) and words[index].startswith("-"):
                index += 1
            index += 1
        elif word in PREFIX_COMMANDS:
            index += 1
            while index < len(words) and words[index].startswith("-"):
                index += 1
        else:
            break
    return words[index:]


def adb_is_read_only(arguments):
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        index += 2 if arguments[index] in ADB_OPTIONS_TAKING_A_VALUE else 1
    if index >= len(arguments):
        return True
    verb, rest = arguments[index], arguments[index + 1 :]
    if verb in ADB_READ_ONLY:
        return True
    if verb in {"shell", "exec-out"}:
        if len(rest) == 1:
            try:
                rest = tokenize(rest[0])
            except ValueError:
                return False
        return bool(rest) and all(shell_segment_read_only(segment) for segment in simple_commands(rest))
    return False


def shell_segment_read_only(words):
    words = [word for word in words if not word.startswith("-")] or words
    if not words:
        return True
    if words[0] in SHELL_READ_ONLY:
        return True
    return len(words) >= 2 and (words[0], words[1]) in SHELL_READ_ONLY_PAIRS


def needs(words):
    """The resources a simple command needs: a subset of {'device', 'checkout'}."""
    if not words:
        return set()
    program, arguments = os.path.basename(words[0]), words[1:]
    verbs = [argument for argument in arguments if not argument.startswith("-")]
    verb = verbs[0] if verbs else None
    if program == "flutter":
        required = set()
        if verb in FLUTTER_CHECKOUT:
            required.add("checkout")
        if verb in FLUTTER_DEVICE:
            required.add("device")
        return required
    if program == "dart":
        return {"checkout"} if verb in DART_CHECKOUT else set()
    if program == "gradlew":
        return {"checkout"}
    if program == "adb":
        return set() if adb_is_read_only(arguments) else {"device"}
    return set()


def unwrap_testlock(words):
    """For `testlock run <resource> ... -- cmd`, return (resource, cmd); else (None, words)."""
    if not words or os.path.basename(words[0]) != "testlock" or len(words) < 3 or words[1] != "run":
        return None, words
    if "--" not in words:
        return None, []
    directory = None
    if "-C" in words[: words.index("--")]:
        position = words.index("-C")
        directory = words[position + 1] if position + 1 < len(words) else None
    return (words[2], directory), words[words.index("--") + 1 :]


def field(lock, name):
    try:
        for line in (lock / "info").read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1]
    except OSError:
        pass
    return ""


def sanitize(text):
    return re.sub(r"[^A-Za-z0-9._-]", "_", text)


def checkout_lock(directory):
    try:
        top = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return LOCK_ROOT / f"checkout{sanitize(top)}" if top else None


def device_locks(words):
    serial = None
    if words and os.path.basename(words[0]) == "adb" and "-s" in words:
        position = words.index("-s")
        serial = words[position + 1] if position + 1 < len(words) else None
    serial = serial or os.environ.get("ANDROID_SERIAL")
    if serial:
        return [LOCK_ROOT / f"device-{sanitize(serial)}"]
    return sorted(LOCK_ROOT.glob("device-*"))


def session_lease(locks, session):
    """True when one of the locks is a live lease stamped with this session."""
    for lock in locks:
        if not lock or not (lock / "info").is_file():
            continue
        expires = field(lock, "expires")
        if (
            session
            and field(lock, "session") == session
            and not field(lock, "pid")
            and expires.isdigit()
            and int(expires) > time.time()
        ):
            return True
    return False


def holder(locks):
    for lock in locks:
        if lock and (lock / "info").is_file():
            return f" Currently held by '{field(lock, 'owner')}' ({field(lock, 'what')})."
    return ""


def resolve(base, target):
    return os.path.normpath(os.path.join(base, os.path.expanduser(target)))


def main():
    if os.environ.get("TESTLOCK_ENFORCE") == "0":
        return
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError):
        return
    session = payload.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    directory = payload.get("cwd") or os.getcwd()

    try:
        tokens = tokenize(command)
    except ValueError:
        return

    for raw in simple_commands(tokens):
        words = strip_prefixes(raw)
        if words and words[0] == "cd" and len(words) > 1:
            directory = resolve(directory, words[1])
            continue
        wrapped, inner = unwrap_testlock(words)
        inner = strip_prefixes(inner)
        run_directory = directory
        covered = set()
        if wrapped:
            covered.add(wrapped[0])
            if wrapped[1]:
                run_directory = resolve(directory, wrapped[1])
        missing = needs(inner) - covered
        if not missing:
            continue

        problems = []
        if "checkout" in missing:
            lock = checkout_lock(run_directory)
            if lock and not session_lease([lock], session):
                problems.append(
                    "checkout: run it as `testlock run checkout --owner \"<branch>:<what>\" "
                    f"-C {run_directory} -- {' '.join(inner)}`; if the checkout is busy, test in "
                    "your own worktree." + holder([lock])
                )
        if "device" in missing:
            locks = device_locks(inner)
            if not session_lease(locks, session):
                problems.append(
                    "device: take the lease first — `testlock acquire device --owner "
                    "\"<branch>:<what>\" --ttl 30` (renew before it expires, release when done), "
                    "or wrap one command in `testlock run device --owner ... -- <cmd>`. If it is "
                    "busy, wait (`--wait 540`) and do non-device work meanwhile." + holder(locks)
                )
        if problems:
            deny(
                "Blocked: this needs the shared test lock (another session may be using it). "
                + " ".join(problems)
                + f" Script: {TESTLOCK_HELP}. See device-verification § Sharing the device and the checkout."
            )


if __name__ == "__main__":
    main()
