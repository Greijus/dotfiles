---
name: cra-code-review
description: Review an embedded C/C++/Python/Yocto repo for security and EU CRA readiness, produce status report, findings and fix plan; or execute approved fixes.
---

# CRA Code Review & Remediation

Two modes. Never run both in one invocation.
- `review <path> [scope]`: read-only analysis. Produces reports. Changes no source code.
- `fix <path> [ids...]`: executes ONLY findings with "approval": "approved" in findings.json.

All outputs go to `<repo>/cra-review/`. Overwrite STATUS.md and PLAN.md; never delete entries in findings.json (preserve IDs and human decisions across runs).
Work on the CURRENT branch only. Never switch branches, never touch other worktrees, never push.

## MODE: review

### Step 1 - Recon (STATUS.md section 1)
- Component name, languages, build system (CMake, Make, Yocto layers/recipes, TI CCS), targets (Linux host, DSP, MCU).
- Every external interface: TCP/UDP ports + protocols (grep bind/listen/socket/port constants), UART, USB, file import, config files, debug interfaces.
- Auth / encryption per interface. Facts only.
- Update mechanism (SWUpdate, RAUC, Mender, custom, none) and image signing.
- Third-party deps: Yocto layers + versions, vendored libs, vendor SDKs (TI RTS/CSL), pip requirements.

### Step 2 - Deterministic tools first (record which ran / were missing; never invent output)
- C/C++: cppcheck --enable=all --inconclusive; clang-tidy (bugprone-*, cert-*, clang-analyzer-*); -Wall -Wextra -Wformat-security.
- Python: bandit -r, pip-audit.
- Yocto: create-spdx, cve-check/vex, security_flags.inc, read-only rootfs, root login, debug-tweaks, open services.
- Binaries: checksec.

### Step 3 - Manual review focus
- Network/IPC parsers: length fields trusted before bounds check, size-math overflow, unterminated strings, circular buffer wrap/overflow, malformed/out-of-order input, connect/disconnect races, unbounded allocation, no connection limits.
- Memory safety: memcpy/strcpy/sprintf/scanf, indexing from external data, UAF, double free.
- Secrets: hardcoded passwords/keys, default or service credentials, backdoor commands.
- Integrity: firmware/DSP image or config loaded without signature/validation.
- Ignored return values on security-relevant calls; asserts as only validation.
- Security event logging.
- DSP/fixed-point code only where reachable from external input.

### Step 4 - findings.json (array)
{"id":"CRA-001","title":"","severity":"P0|P1|P2|P3","category":"","cra_ref":"Annex I.1(x)","location":"file:line","evidence":"code excerpt + how external input reaches it","confidence":"high|medium|low","source":"tool|manual","fix_type":"auto|design|human","proposed_fix":"","effort":"S|M|L","verification":"","approval":"pending","status":"open"}
- P0: remote memory corruption, auth bypass, hardcoded creds, unsigned code exec path.
- P1: unauthenticated control interface, cleartext sensitive data, single-packet DoS, exploitable CVE in shipped dep.
- P2: missing hardening, missing logging, weak validation without proven path.
- P3: hygiene, defense-in-depth.
- auto = localized, testable change; design = architecture decision (auth/TLS, secure boot, updates); human = process/legal.
- No non-human finding without file:line evidence. Don't inflate severity. Merge duplicates.

### Step 5 - STATUS.md
1. Recon + interface table (interface | port | auth | encryption | notes).
2. Tools run / not run.
3. Count table severity x fix_type.
4. CRA Annex I matrix: Part I (a)-(m), Part II 1-8; status met/partial/gap/unknown, evidence, finding IDs.
5. Top 5 risks, plain language.
6. Limitations (what couldn't be built/tested). State: supporting evidence, not a compliance sign-off.

### Step 6 - PLAN.md
Batches: 1) P0 auto 2) P1 auto 3) design proposals + decision questions 4) P2/P3 auto 5) human actions. Per item: ID, files, test, effort, deps.

End with: "Review complete. Set approval in findings.json, then run fix." STOP. No source changes.

## MODE: fix
1. Select approval=="approved" and status=="open" (optionally filtered by ids). None -> stop.
2. Per finding, in PLAN order:
   - One commit per finding on the current branch, using the repo's commit-message convention.
   - design: implement only if the approval note specifies the design; else write cra-review/design/<id>.md.
   - Minimal change, existing style, no unrelated refactoring.
   - Add test: unit/regression, or libFuzzer harness for parsers (-fsanitize=fuzzer,address,undefined).
   - Build + test. If not buildable here (DSP/cross), status fixed-unverified with reason.
   - Update finding: status fixed|fixed-unverified|blocked, commit, test, notes.
3. Never mark fixed without passing build or explicit unverified note.
4. FIX_REPORT.md: id | title | status | commit | test | notes; remaining items; regressions.
5. Regenerate STATUS.md Annex I matrix.
