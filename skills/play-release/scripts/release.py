#!/usr/bin/env python3
"""play-release — the step runner.

Takes one release of one app from "cut" to "live on Play". Every app-specific value comes from
`release.config.yaml` at the app repo's root; every secret from the gitignored
`release.local.yaml` beside it. The tracker, docs/releases/<version>.md, is the single source of
truth: every status change is written there first, then printed.

    release.py status  <version>                 create the tracker if missing, print it
    release.py run     <version>                 run from the first open step until a manual step,
                                                 a gate that fails, or a step that needs your go
    release.py done    <version> <step> <evidence>   record a manual step as done
    release.py cut     <version> --go            make the Version marker (step 12)
    release.py cherry-pick <version> <sha>...    bring a fix into the release worktree
    release.py ack     <version> <package> <why> accept a new direct dependency (step 11)
    release.py promote <version> --to <track> --fraction <0-1> --go
    release.py gate    <version> <policy|priv1|sdk>   run one gate against the release worktree,
                                                 without touching the tracker
    release.py readout <version>                 read tracks, listing, images and subscriptions
                                                 from Play (read-only) into the state file

Run it from the app repo's main checkout (or pass --repo). It never prints a secret: evidence
names a path, a count or a check result, never a value.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import html.parser
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

OPEN, DOING, DONE, BLOCKED = '☐', '◐', '✅', '⛔'

# (key, title, who, where). The tracker's rows are rendered from this list, so the runner and
# the table can never disagree about what step N is.
STEPS = [
    ('preflight', 'Preflight: config, tools, local secrets present (names only)', 'auto', 'this machine'),
    ('service_account', 'Play API service account works', 'me', 'Google Cloud + Play Console › Users and permissions'),
    ('worktree', 'Release worktree on `{rc}`, clean; local files linked', 'auto', '`{worktree_rel}`'),
    ('fixes', 'Fixes to bring in (cherry-pick, or "none")', 'me', 'chat'),
    ('format_l10n', '`dart format` clean; l10n + pseudo-locale regenerated, no diff', 'auto', 'worktree'),
    ('analyze', '`flutter analyze`', 'auto', 'worktree'),
    ('tests', 'Full `flutter test`', 'auto', 'worktree'),
    ('ci', 'CI green at the tested commit', 'auto', 'GitHub Actions'),
    ('gate_policy', 'Gate: policy parity (in-app = site repo = deployed)', 'auto', '{policy_url}'),
    ('gate_priv1', 'Gate: PRIV-1 AI request fields = Data safety list = policy', 'auto', '`{priv1_builder}`'),
    ('gate_sdk', 'Gate: no analytics/crash SDK; new direct deps acknowledged', 'auto', '`pubspec` vs `{baseline}`'),
    ('cut', '`Version {version}` marker (VERSION → name + code)', 'auto, **on your go**', '`{rc}`'),
    ('changelog', 'Changelog + Play release notes (≤ {notes_limit} chars)', 'auto', 'this tracker'),
    ('gate_secrets', 'Gate: reviewer hash from `release.local.yaml`; no App Check debug token', 'auto', 'local config + Gradle guard'),
    ('build', 'Signed AAB built and verified (signer, id, version, hash)', 'auto', '`{aab_rel}`'),
    ('tag_push', 'Tag `{tag}` at the built commit; push branch + tag', 'auto', 'origin'),
    ('upload', 'Upload to the `{upload_track}` track + release notes', 'auto', 'Play Developer API'),
    ('phone', 'Phone check on the Play-installed build', 'me', 'phone + Firebase + Cloud console'),
    ('firebase', 'Firebase checks: AI monitoring off, spend caps, prepay balance', 'me', 'Firebase / Cloud console'),
    ('declarations', 'Play Console declarations flagged for re-check', 'me', 'Play Console › App content'),
    ('sign_in', 'Sign in details (text regenerated from the app)', 'me', 'Play Console › App content › App access'),
    ('promote', 'Promote to closed/production, rollout %', 'auto, **on your go**', 'Play Developer API'),
    ('publish', 'Send for review / Publish changes', 'me, **on your go**', 'Play Console › Publishing overview'),
    ('close', 'Close: state file dates, tracker final', 'auto', '`docs/releases/`'),
]
STEP_NO = {key: i + 1 for i, (key, *_rest) in enumerate(STEPS)}
# Where an auto step's evidence comes from (the tracker's Source column). Manual steps record
# "manual (<operator>, <date>)" when `done` is run.
STEP_SOURCE = {'service_account': 'api', 'ci': 'gh', 'gate_policy': 'repo + site', 'upload': 'api',
               'promote': 'api'}
CODE_STEPS = range(STEP_NO['format_l10n'], STEP_NO['upload'] + 1)


from errors import Stop, Wait  # noqa: E402  (after the sys.path insert)


# --------------------------------------------------------------------------------------------
# Shell
# --------------------------------------------------------------------------------------------

def sh(args: list[str], cwd: Path | None = None, check: bool = True, redact: list[str] = ()) -> str:
    """Runs a command and returns its stdout. On failure raises Stop with the redacted tail."""
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    for secret in redact:
        if secret:
            out = out.replace(secret, '<redacted>')
    if check and proc.returncode != 0:
        shown = ' '.join(a if not any(s and s in a for s in redact) else '<redacted>' for a in args)
        tail = '\n'.join(out.strip().splitlines()[-25:])
        raise Stop(f'`{shown}` exited {proc.returncode}', tail or '(no output)',
                   'Read the output above, fix the cause, then run again.')
    return proc.stdout


def git(repo: Path, *args: str, check: bool = True) -> str:
    return sh(['git', '-C', str(repo), *args], check=check).strip()


# --------------------------------------------------------------------------------------------
# Context
# --------------------------------------------------------------------------------------------

class Ctx:
    def __init__(self, repo: Path, version: str):
        self.repo = repo
        self.version = version
        cfg_path = repo / 'release.config.yaml'
        if not cfg_path.exists():
            raise Stop('No release.config.yaml', f'{repo} has no release.config.yaml at its root.',
                       'Copy the skill\'s templates/release.config.example.yaml there and fill it in.')
        self.cfg = yaml.safe_load(cfg_path.read_text())
        local_path = repo / self.cfg.get('local_config', 'release.local.yaml')
        self.local_path = local_path
        self.local = yaml.safe_load(local_path.read_text()) if local_path.exists() else None
        app = self.cfg['app']
        self.flutter_dir = app.get('flutter_dir', '.')
        self.rc = app['rc_branch'].format(version=version)
        self.tag = app['tag'].format(version=version)
        self.worktree = repo / app['worktree'].format(version=version)
        self.trackers = repo / self.cfg.get('trackers_dir', 'docs/releases')
        self.tracker = self.trackers / f'{version}.md'
        self.state_file = repo / self.cfg.get('state_file', 'docs/releases/play-console-state.md')

    # Paths inside the release worktree
    def wt(self, rel: str = '') -> Path:
        return self.worktree / rel if rel else self.worktree

    def mobile(self) -> Path:
        return self.wt(self.flutter_dir)

    def local_value(self, key: str) -> str | None:
        if not self.local:
            return None
        value = self.local.get(key)
        return str(value).strip() if value else None

    def fmt(self) -> dict:
        play = self.cfg['play']
        return {
            'version': self.version,
            'rc': self.rc,
            'tag': self.tag,
            'worktree_rel': os.path.relpath(self.worktree, self.repo),
            'policy_url': self.cfg['policy']['url'],
            'priv1_builder': self.cfg['gates']['priv1']['builder'],
            'baseline': 'last release',
            'notes_limit': play['release_notes_limit'],
            'notes_language': play['release_notes_language'],
            'upload_track': play['upload_track'],
            'aab_rel': self.cfg['build']['aab'],
            'app_name': self.cfg['app']['name'],
        }


# --------------------------------------------------------------------------------------------
# Tracker
# --------------------------------------------------------------------------------------------

ROW = re.compile(r'^\|\s*(\d+)\s*\|')


def split_row(line: str) -> list[str]:
    cells = re.split(r'(?<!\\)\|', line.strip())[1:-1]
    return [c.strip() for c in cells]


def cell(text: str) -> str:
    return text.replace('|', '\\|').replace('\n', ' ').strip()


class Tracker:
    def __init__(self, ctx: Ctx):
        self.ctx = ctx
        self.path = ctx.tracker
        self.lines = self.path.read_text().splitlines()

    @staticmethod
    def create(ctx: Ctx) -> None:
        ctx.trackers.mkdir(parents=True, exist_ok=True)
        f = ctx.fmt()
        rows = ['| # | Step | Who | Where | Status | Evidence | Source |',
                '|---|------|-----|-------|--------|----------|--------|']
        for i, (_key, title, who, where) in enumerate(STEPS, 1):
            rows.append(f'| {i} | {title.format(**f)} | {who} | {where.format(**f)} | {OPEN} | | |')
        template = (SCRIPTS / 'templates' / 'release-tracker.md').read_text()
        ctx.tracker.write_text(template.format(table='\n'.join(rows), **f))

    def row_index(self, n: int) -> int:
        for i, line in enumerate(self.lines):
            m = ROW.match(line)
            if m and int(m.group(1)) == n:
                return i
        raise Stop(f'Step {n} is not in the tracker', f'{self.path} has no row {n}.',
                   'The tracker was edited by hand; restore its table from git.')

    def status(self, n: int) -> str:
        return split_row(self.lines[self.row_index(n)])[4]

    def evidence(self, n: int) -> str:
        return split_row(self.lines[self.row_index(n)])[5]

    def set(self, n: int, status: str, evidence: str | None = None, source: str | None = None) -> None:
        i = self.row_index(n)
        cells = split_row(self.lines[i])
        before = cells[4]
        cells[4] = status
        if evidence is not None:
            cells[5] = cell(evidence)
            if len(cells) > 6:
                key = STEPS[n - 1][0]
                cells[6] = cell(source or (STEP_SOURCE.get(key, 'repo') if evidence else ''))
        self.lines[i] = '| ' + ' | '.join(cells) + ' |'
        if before != status or evidence is not None:
            self.log(f'step {n} {before} → {status}' + (f': {cell(evidence)}' if evidence else ''))
        self.save()

    def first_open(self) -> int | None:
        for n in range(1, len(STEPS) + 1):
            if self.status(n) != DONE:
                return n
        return None

    def section_bounds(self, header: str) -> tuple[int, int]:
        try:
            start = self.lines.index(header)
        except ValueError:
            raise Stop(f'Section "{header}" missing', f'{self.path} has no "{header}".',
                       'Restore the section header from the template.')
        end = start + 1
        while end < len(self.lines) and not self.lines[end].startswith('#'):
            end += 1
        return start, end

    def section(self, header: str) -> str:
        start, end = self.section_bounds(header)
        return '\n'.join(self.lines[start + 1:end]).strip()

    def set_section(self, header: str, body: str) -> None:
        start, end = self.section_bounds(header)
        self.lines[start + 1:end] = [''] + body.strip().splitlines() + ['']
        self.save()

    def append_section(self, header: str, line: str) -> None:
        body = self.section(header)
        if body.startswith('_None'):
            body = ''
        self.set_section(header, (body + '\n' + line).strip())

    def log(self, text: str) -> None:
        start, end = self.section_bounds('## Log')
        stamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
        insert_at = end
        while insert_at > start + 1 and not self.lines[insert_at - 1].strip():
            insert_at -= 1
        self.lines.insert(insert_at, f'- {stamp} — {text}')

    def table(self) -> str:
        out, in_table = [], False
        for line in self.lines:
            if line.startswith('| # |'):
                in_table = True
            if in_table:
                if not line.startswith('|'):
                    break
                out.append(line)
        return '\n'.join(out)

    def save(self) -> None:
        self.path.write_text('\n'.join(self.lines) + '\n')


def commit_records(ctx: Ctx, message: str) -> None:
    """Commits the tracker (and the state file) in the main checkout — those paths only."""
    paths = [p for p in (ctx.tracker, ctx.state_file) if p.exists()]
    rel = [str(p.relative_to(ctx.repo)) for p in paths]
    changed = git(ctx.repo, 'status', '--porcelain', '--', *rel)
    if not changed:
        return
    git(ctx.repo, 'add', '--', *rel)
    git(ctx.repo, 'commit', '-m', message, '--', *rel)


# --------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------

def testlock(ctx: Ctx, what: str, cmd: list[str], cwd: Path, redact: list[str] = ()) -> str:
    lock = os.path.expanduser(ctx.cfg['tools']['testlock'])
    return sh([lock, 'run', 'checkout', '--owner', f'release/{ctx.version}:{what}', '-C', str(cwd), '--', *cmd],
              redact=redact)


def head(ctx: Ctx) -> str:
    return git(ctx.wt(), 'rev-parse', '--short=8', 'HEAD')


def require_worktree(ctx: Ctx) -> None:
    if not (ctx.wt() / '.git').exists():
        raise Stop('No release worktree', f'{ctx.worktree} does not exist yet.',
                   f'Run step {STEP_NO["worktree"]} first (`release.py run {ctx.version}`).')


def require_clean(ctx: Ctx) -> None:
    dirty = git(ctx.wt(), 'status', '--porcelain')
    if dirty:
        files = '\n'.join('  ' + line for line in dirty.splitlines())
        raise Stop('The release worktree is dirty', f'Uncommitted files in {ctx.worktree}:\n{files}',
                   'Commit them on a fix branch and cherry-pick, or discard them. Nothing may reach '
                   'a release except through a commit.')


def baseline_ref(ctx: Ctx) -> str:
    """The last release: the newest `v*` tag reachable from the RC, else the previous marker."""
    tags = git(ctx.wt(), 'tag', '--merged', 'HEAD', '--sort=-creatordate', '--list', 'v*', check=False)
    for t in tags.splitlines():
        if t.strip() and t.strip() != ctx.tag:
            return t.strip()
    markers = git(ctx.wt(), 'log', '--format=%H %s', '--grep', ctx.cfg['app']['marker_grep'], 'HEAD')
    for line in markers.splitlines():
        sha, subject = line.split(' ', 1)
        if subject.strip() != f'Version {ctx.version}':
            return sha[:8]
    raise Stop('No baseline', 'No earlier release tag or Version marker on this branch.',
               'Tag the last release (`git tag v<version> <sha>`) and run again.')


def marker_sha(ctx: Ctx) -> str | None:
    out = git(ctx.wt(), 'log', '--format=%H', '--grep', f'^Version {re.escape(ctx.version)}$', 'HEAD')
    return out.splitlines()[0][:8] if out else None


def version_code(version: str) -> int:
    m = re.fullmatch(r'(\d+)\.(\d+)(?:b(\d+))?', version)
    if not m:
        raise Stop('Unreadable version', f'"{version}" is not <major>.<minor>[b<N>].', 'Use e.g. 1.0b18.')
    major, minor, beta = int(m.group(1)), int(m.group(2)), m.group(3)
    return major * 10000 + minor * 100 + (int(beta) if beta else 99)


def expected_version_name(ctx: Ctx) -> str:
    """What the build reports: bare at the marker, `+sha` past it (the beta-versioning scheme)."""
    at_marker = marker_sha(ctx) == head(ctx)
    return ctx.version if at_marker else f'{ctx.version}+{git(ctx.wt(), "rev-parse", "--short=7", "HEAD")}'


def words(text: str) -> list[str]:
    text = (text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
            .replace('\u00a0', ' '))
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)*", text.lower())


def markdown_text(md: str) -> str:
    md = re.sub(r'^---\n.*?\n---\n', '', md, flags=re.S)        # front matter
    md = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', md)          # links, images
    md = re.sub(r'<[^>]+>', ' ', md)                            # inline html
    return md


class _Text(html.parser.HTMLParser):
    SKIP = {'script', 'style', 'nav', 'header', 'footer', 'noscript', 'svg'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth, self.cf, self.parts = 0, 0, []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1
        if self.cf:
            self.cf += 1
            return
        # Cloudflare's email obfuscation replaces an address with "[email protected]" and a
        # hex blob XOR-coded with its first byte. Decode it, so the page reads as written.
        coded = dict(attrs).get('data-cfemail')
        if coded:
            raw = bytes.fromhex(coded)
            self.parts.append(' ' + bytes(b ^ raw[0] for b in raw[1:]).decode('utf-8', 'replace') + ' ')
            self.cf = 1

    def handle_endtag(self, tag):
        if self.cf:
            self.cf -= 1
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth and not self.cf:
            self.parts.append(data)


def html_text(page: str) -> str:
    p = _Text()
    p.feed(page)
    return ' '.join(p.parts)


def body_words(text: str, start_heading: str) -> list[str]:
    all_words = words(text)
    key = words(start_heading.lstrip('#'))
    for i in range(len(all_words) - len(key) + 1):
        if all_words[i:i + len(key)] == key:
            return all_words[i:]
    raise Stop('Policy section not found', f'No "{start_heading}" in the text compared.',
               'Check `policy.body_starts_at` in release.config.yaml against the policy.')


def first_difference(a: list[str], b: list[str], name_a: str, name_b: str) -> str:
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal':
            ctx_a = ' '.join(a[max(0, i1 - 6):i2 + 6])
            ctx_b = ' '.join(b[max(0, j1 - 6):j2 + 6])
            return f'{name_a}: …{ctx_a}…\n{name_b}: …{ctx_b}…'
    return 'no difference'


def arb(ctx: Ctx) -> dict:
    return json.loads((ctx.mobile() / ctx.cfg['l10n']['arb']).read_text())


# --------------------------------------------------------------------------------------------
# Gates (pure checks: they raise Stop or return evidence)
# --------------------------------------------------------------------------------------------

def gate_policy(ctx: Ctx) -> str:
    import requests
    pol = ctx.cfg['policy']
    start = pol['body_starts_at']
    in_app = body_words(markdown_text((ctx.wt() / pol['in_app']).read_text()), start)
    site_md = sh(['gh', 'api', f'repos/{pol["site_repo"]}/contents/{pol["site_path"]}',
                  '-H', 'Accept: application/vnd.github.raw'])
    site = body_words(markdown_text(site_md), start)
    if in_app != site:
        raise Stop('Policy copies differ', 'The in-app body and the site repo body are not the same text:\n'
                   + first_difference(in_app, site, 'in-app', 'site repo'),
                   f'Make both copies say the same thing (one change, both repos), then run again.')
    resp = requests.get(pol['url'], timeout=30, headers={'Cache-Control': 'no-cache'})
    if resp.status_code != 200:
        raise Stop('Deployed policy unreachable', f'{pol["url"]} answered HTTP {resp.status_code}.',
                   'Check the site deploy; the policy URL must answer 200 before release.')
    deployed = body_words(html_text(resp.text), start)
    if deployed[:len(site)] != site:
        raise Stop('Deployed policy is stale', 'The live page does not match the site repo:\n'
                   + first_difference(site, deployed[:len(site)], 'site repo', 'deployed'),
                   'Redeploy the site from its repo, wait for it to go live, then run again.')
    return f'in-app = site repo = deployed ({len(site)} words from "{start.lstrip("# ")}")'


def priv1_fields(ctx: Ctx) -> set[str]:
    g = ctx.cfg['gates']['priv1']
    src = (ctx.wt() / g['builder']).read_text()
    found = set()
    for m in re.finditer(r'\brequest\.([a-zA-Z]+)(?:\.([a-zA-Z]+))?', src):
        field, sub = m.group(1), m.group(2)
        found.add(f'{field}.{sub}' if field in g.get('expand', []) and sub else field)
    return found


def priv1_declared(ctx: Ctx) -> dict:
    text = ctx.state_file.read_text()
    m = re.search(r'```yaml priv1\n(.*?)```', text, re.S)
    if not m:
        raise Stop('No AI request field list', f'{ctx.state_file} has no ```yaml priv1 block.',
                   'Restore the § Data safety → AI request fields block.')
    return yaml.safe_load(m.group(1)) or {}


def gate_priv1(ctx: Ctx) -> str:
    used = priv1_fields(ctx)
    declared = priv1_declared(ctx)
    new = sorted(used - set(declared))
    gone = sorted(set(declared) - used)
    if new or gone:
        raise Stop('The AI request changed', f'Fields sent but not declared: {new or "none"}; '
                   f'declared but no longer sent: {gone or "none"}.',
                   'A new field means: update the privacy policy (both copies), the Data safety form, '
                   'and do the PRIV-2 consent re-ask (bump consentVersion). Then update the priv1 block in '
                   f'{ctx.state_file.name}. A removed field: drop it from the block.')
    policy = ' '.join(words(markdown_text((ctx.wt() / ctx.cfg['policy']['in_app']).read_text())))
    missing = [f'{k} ("{v}")' for k, v in declared.items() if v and ' '.join(words(v)) not in policy]
    if missing:
        raise Stop('The policy does not name every field sent', 'Not found in the in-app policy: '
                   + ', '.join(missing), 'Say it in the policy (both copies), or fix the phrase in the priv1 block.')
    return f'{len(used)} fields sent = {len(declared)} declared; each named in the policy'


def direct_deps(pubspec_text: str) -> set[str]:
    data = yaml.safe_load(pubspec_text) or {}
    return set((data.get('dependencies') or {}).keys())


def gate_sdk(ctx: Ctx, tracker: Tracker | None) -> str:
    g = ctx.cfg['gates']['sdk']
    lock = yaml.safe_load((ctx.mobile() / 'pubspec.lock').read_text())
    packages = set((lock.get('packages') or {}).keys())
    denied = sorted(p for p in packages if any(re.fullmatch(d, p) for d in g['deny']))
    if denied:
        raise Stop('A denied SDK is in the app', f'pubspec.lock contains: {", ".join(denied)}.',
                   'Remove it, or — if it is wanted — update the privacy policy and Data safety first, '
                   'then remove it from `gates.sdk.deny`.')
    base = baseline_ref(ctx)
    rel = f'{ctx.flutter_dir}/pubspec.yaml' if ctx.flutter_dir != '.' else 'pubspec.yaml'
    before = direct_deps(git(ctx.wt(), 'show', f'{base}:{rel}'))
    now = direct_deps((ctx.mobile() / 'pubspec.yaml').read_text())
    new = sorted(now - before)
    acked = set()
    if tracker:
        for line in tracker.section('## Acknowledgements').splitlines():
            m = re.match(r'- `([^`]+)`', line)
            if m:
                acked.add(m.group(1))
    pending = [p for p in new if p not in acked]
    if pending:
        raise Stop('New direct dependencies since the last release', f'Added since {base}: '
                   + ', '.join(pending) + '. Any of them may send data off the device.',
                   'For each: check what it transmits. If nothing, acknowledge it: '
                   f'`release.py ack {ctx.version} <package> "<what it does, why it sends nothing>"`. '
                   'If it sends data, update the policy and Data safety first.')
    return f'no denied SDK; {len(new)} new direct dep(s) since {base}' + (f', acknowledged: {", ".join(new)}' if new else '')


# --------------------------------------------------------------------------------------------
# Steps (each returns evidence, or raises Stop / Wait). Each checks its own postcondition first.
# --------------------------------------------------------------------------------------------

def step_preflight(ctx: Ctx, t: Tracker) -> str:
    for tool in ('git', 'gh', 'flutter', 'dart', 'keytool'):
        if not shutil_which(tool):
            raise Stop(f'`{tool}` not found', f'{tool} is not on PATH.', f'Install {tool} or fix PATH.')
    if not os.path.exists(os.path.expanduser(ctx.cfg['tools']['testlock'])):
        raise Stop('testlock not found', ctx.cfg['tools']['testlock'], 'Fix `tools.testlock` in release.config.yaml.')
    sh(['gh', 'auth', 'status'])
    for module in ('requests', 'cryptography'):
        try:
            __import__(module)
        except ImportError:
            raise Stop(f'Python module {module} missing', 'The Play API client needs it.', f'pip install {module}')
    if ctx.local is None:
        raise Stop('No release.local.yaml', f'{ctx.local_path} does not exist.',
                   'Create it from the skill\'s templates/release.local.example.yaml (it is gitignored).')
    if subprocess.run(['git', '-C', str(ctx.repo), 'check-ignore', '-q', str(ctx.local_path)]).returncode != 0:
        raise Stop('release.local.yaml is not gitignored', 'It holds secrets and git would track it.',
                   'Add `release.local.yaml` to the repo root .gitignore.')
    keys = sorted(k for k, v in ctx.local.items() if v)
    return f'tools ok; config ok; local keys set: {", ".join(keys) or "none"}'


def shutil_which(name: str) -> str | None:
    import shutil
    return shutil.which(name)


def step_service_account(ctx: Ctx, t: Tracker) -> str:
    import play_api
    path = ctx.local_value('play_service_account_json')
    if path and os.path.exists(os.path.expanduser(path)):
        client = play_api.PlayClient(os.path.expanduser(path), ctx.cfg['app']['package'])
        client.check_access()
        return f'service account reaches {ctx.cfg["app"]["package"]} (edit opened and deleted)'
    raise Wait(guide_service_account(ctx))


def step_worktree(ctx: Ctx, t: Tracker) -> str:
    wt = ctx.wt()
    listing = git(ctx.repo, 'worktree', 'list', '--porcelain')
    holder = None
    for block in listing.split('\n\n'):
        lines = dict(line.split(' ', 1) for line in block.splitlines() if ' ' in line)
        if lines.get('branch') == f'refs/heads/{ctx.rc}':
            holder = Path(lines['worktree'])
    if holder and holder.resolve() != wt.resolve():
        raise Stop(f'`{ctx.rc}` is checked out elsewhere', f'{holder} has {ctx.rc} checked out, and a branch can '
                   'live in one worktree only. Release work owns the RC branch.',
                   f'Move that checkout to the next development branch (e.g. the next rc/), then run again.')
    if not holder:
        git(ctx.repo, 'fetch', 'origin', ctx.rc, check=False)
        exists = git(ctx.repo, 'rev-parse', '--verify', '--quiet', f'refs/heads/{ctx.rc}', check=False)
        if not exists:
            remote = git(ctx.repo, 'rev-parse', '--verify', '--quiet', f'refs/remotes/origin/{ctx.rc}', check=False)
            if not remote:
                raise Stop(f'No branch {ctx.rc}', 'Neither a local nor an origin branch of that name exists.',
                           'Create the RC branch first.')
            git(ctx.repo, 'branch', '--track', ctx.rc, f'origin/{ctx.rc}')
        git(ctx.repo, 'worktree', 'add', str(wt), ctx.rc)
    linked = []
    for rel in ctx.cfg['build'].get('local_files', []):
        target, source = wt / rel, ctx.repo / rel
        if not source.exists():
            raise Stop(f'Local file missing: {rel}', f'{source} does not exist in the main checkout.',
                       'Create it there (it is gitignored), then run again.')
        if target.is_symlink() or target.exists():
            if not (target.is_symlink() and os.readlink(target) == str(source)):
                raise Stop(f'{rel} in the worktree is not the link', f'{target} exists and is not a link to {source}.',
                           'Delete it from the worktree; the skill links the main checkout\'s copy.')
        else:
            target.symlink_to(source)
        linked.append(Path(rel).name)
    require_clean(ctx)
    return f'{os.path.relpath(wt, ctx.repo)} on {ctx.rc} @ {head(ctx)}, clean; linked: {", ".join(linked) or "none"}'


def step_fixes(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    current = git(ctx.repo, 'rev-parse', '--abbrev-ref', 'HEAD')
    candidates = git(ctx.repo, 'log', '--no-merges', '--format=%h %s', f'{ctx.rc}..HEAD', check=False)
    code = [l for l in candidates.splitlines() if not re.match(r'^\w+ docs(\(|:)', l)]
    listing = '\n'.join('  ' + l for l in code[:30]) or '  (none)'
    raise Wait(f'''Step {STEP_NO["fixes"]} — Fixes to bring in                    (Who: me)
Where:   chat. Non-doc commits on `{current}` that are not in `{ctx.rc}`:
{listing}
Do:      name the shas to bring in, or say "none". Nothing is merged: each is cherry-picked
         (`release.py cherry-pick {ctx.version} <sha>…`) and recorded in § Cherry-picks.
Done when: you said "none", or every named fix is in § Cherry-picks.
Give back: "none", or the shas.''')


def step_format_l10n(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    require_clean(ctx)
    m = ctx.mobile()
    testlock(ctx, 'format', ['dart', 'format', '--output=none', '--set-exit-if-changed', '.'], m)
    for cmd in ctx.cfg['l10n'].get('regenerate', []):
        testlock(ctx, 'l10n', cmd, m)
    dirty = git(ctx.wt(), 'status', '--porcelain')
    if dirty:
        raise Stop('Regeneration changed files', 'Committed generated files are stale:\n' + dirty,
                   'Regenerate on a fix branch, commit, cherry-pick it here (`release.py cherry-pick`).')
    return f'format clean, l10n + pseudo-locale unchanged @ {head(ctx)}'


def step_analyze(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    out = testlock(ctx, 'analyze', ['flutter', 'analyze'], ctx.mobile())
    if 'No issues found' not in out:
        raise Stop('flutter analyze found issues', out[-2000:], 'Fix them on a fix branch and cherry-pick.')
    return f'No issues found @ {head(ctx)}'


def step_tests(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    require_clean(ctx)
    out = testlock(ctx, 'tests', ['flutter', 'test'], ctx.mobile())
    m = re.findall(r'\+(\d+)(?: ~(\d+))?(?: -(\d+))?: All tests passed!', out)
    if not m:
        raise Stop('The suite did not pass', '\n'.join(out.splitlines()[-30:]), 'Fix on a fix branch and cherry-pick.')
    passed, skipped, _ = m[-1]
    return f'{passed} passed, {skipped or 0} skipped @ {head(ctx)}'


def step_ci(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    sha = git(ctx.wt(), 'rev-parse', 'HEAD')
    remote = git(ctx.repo, 'ls-remote', 'origin', f'refs/heads/{ctx.rc}').split()
    if not remote or remote[0] != sha:
        git(ctx.wt(), 'push', 'origin', f'HEAD:refs/heads/{ctx.rc}')
    runs = json.loads(sh(['gh', 'run', 'list', '--repo', ctx.cfg['app']['github_repo'], '--commit', sha,
                          '--json', 'status,conclusion,workflowName,url', '--limit', '20']))
    wanted = ctx.cfg['gates']['ci_workflows']
    for name in wanted:
        hits = [r for r in runs if r['workflowName'] == name]
        if not hits:
            raise Wait(f'CI has not started for {sha[:8]} ({name}). Run again in a few minutes.')
        r = hits[0]
        if r['status'] != 'completed':
            raise Wait(f'CI is {r["status"]} for {sha[:8]} ({name}): {r["url"]}. Run again when it finishes.')
        if r['conclusion'] != 'success':
            raise Stop(f'CI {r["conclusion"]} at {sha[:8]}', f'{name}: {r["url"]}',
                       'Read the failing job, fix on a fix branch, cherry-pick, and run again.')
    return f'{", ".join(wanted)} green @ {sha[:8]}'


def step_gate_policy(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    return gate_policy(ctx)


def step_gate_priv1(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    return gate_priv1(ctx)


def step_gate_sdk(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    return gate_sdk(ctx, t)


def step_cut(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    sha = marker_sha(ctx)
    vf = ctx.wt(ctx.cfg['app']['version_file'])
    current = vf.read_text().splitlines()[0].strip()
    if sha and current == ctx.version:
        return f'`Version {ctx.version}` = {sha}; versionCode {version_code(ctx.version)}'
    base = baseline_ref(ctx)
    log = git(ctx.wt(), 'log', '--no-merges', '--format=  %h %s', f'{base}..HEAD')
    raise Wait(f'''Step {STEP_NO["cut"]} — Cut `Version {ctx.version}`                     (Who: auto, on your go)
VERSION reads {current}. Gates 9–11 are green, so the cut is ready. Commits since {base}:
{log or "  (none)"}
Say "cut {ctx.version}" to make the marker (it changes VERSION only), or name fixes to pick first.''')


def do_cut(ctx: Ctx) -> str:
    require_worktree(ctx)
    require_clean(ctx)
    if marker_sha(ctx):
        return marker_sha(ctx)
    vf = ctx.wt(ctx.cfg['app']['version_file'])
    lines = vf.read_text().splitlines()
    lines[0] = ctx.version
    vf.write_text('\n'.join(lines) + '\n')
    base = baseline_ref(ctx)
    changes = git(ctx.wt(), 'log', '--no-merges', '--format=- %s', f'{base}..HEAD')
    msg = f'Version {ctx.version}\n\n- Release {ctx.version}, cut by play-release.\n\nChangelog:\n{changes}\n'
    git(ctx.wt(), 'add', '--', ctx.cfg['app']['version_file'])
    proc = subprocess.run(['git', '-C', str(ctx.wt()), 'commit', '-F', '-'], input=msg, text=True,
                          capture_output=True)
    if proc.returncode != 0:
        raise Stop('The marker commit failed', proc.stderr[-1500:], 'Fix the cause and run `cut` again.')
    return marker_sha(ctx)


def step_changelog(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    base = baseline_ref(ctx)
    raw = git(ctx.wt(), 'log', '--no-merges', '--format=%h\t%s', f'{base}..HEAD')
    groups = {'Features': [], 'Fixes': [], 'Content': [], 'Other': []}
    for line in raw.splitlines():
        sha, subject = line.split('\t', 1)
        if re.match(r'^(docs|chore)(\(|:)', subject) or subject.startswith('Version '):
            continue
        kind = ('Features' if subject.startswith('feat') else 'Fixes' if subject.startswith('fix')
                else 'Content' if subject.startswith('content') else 'Other')
        groups[kind].append(f'- {subject} ({sha})')
    body = '\n\n'.join(f'**{k}**\n' + '\n'.join(v) for k, v in groups.items() if v) or '_No app changes._'
    t.set_section('## Changelog', f'Since `{base}`:\n\n{body}')
    header = f'### Play release notes ({ctx.cfg["play"]["release_notes_language"]})'
    notes = t.section(header)
    limit = ctx.cfg['play']['release_notes_limit']
    if notes.startswith('_Drafted'):
        draft = []
        for subject in [l.split(' (')[0][2:] for l in groups['Features'] + groups['Fixes'] + groups['Content']]:
            plain = re.sub(r'^\w+(\([^)]*\))?:\s*', '', subject)
            plain = re.sub(r'\s*\((R\d+[-\d.,\s]*|[A-Z]+-\d+)\)\s*$', '', plain)
            draft.append('• ' + plain[0].upper() + plain[1:])
        text = ''
        for d in draft:
            if len(text) + len(d) + 1 > limit:
                break
            text += d + '\n'
        t.set_section(header, (text.strip() or '• Improvements and fixes.') +
                      '\n\n<!-- DRAFT: rewrite in plain words for users, then delete this line. -->')
    notes = t.section(header)
    return f'{sum(len(v) for v in groups.values())} changes since {base}; notes draft {len(notes_text(notes))}/{limit} chars'


def notes_text(section: str) -> str:
    return re.sub(r'<!--.*?-->', '', section, flags=re.S).strip()


def step_gate_secrets(ctx: Ctx, t: Tracker) -> str:
    h = ctx.local_value('reviewer_code_sha256')
    if not h or not re.fullmatch(r'[0-9a-f]{64}', h):
        raise Stop('No reviewer hash', f'`reviewer_code_sha256` in {ctx.local_path.name} is missing or not 64 '
                   'lower-case hex characters.',
                   'Put the hash of the reviewer code there (`printf %s CODE | sha256sum | cut -d" " -f1`).')
    for rel in ctx.cfg['build'].get('cross_check_files', []):
        other = ctx.repo / rel
        if other.exists():
            m = re.search(r'^REVIEWER_CODE_SHA256=([0-9a-fA-F]{64})\s*$', other.read_text(), re.M)
            if m and m.group(1).lower() != h:
                raise Stop('Two reviewer hashes disagree', f'{rel} and {ctx.local_path.name} hold different hashes.',
                           'Make them the same (or delete the stale one) so ad-hoc and release builds unlock '
                           'with the same code.')
    gradle = ctx.wt(ctx.cfg['build']['gradle_file']).read_text()
    for name in ctx.cfg['build']['forbidden_defines']:
        if f'"{name}" in dartDefineNames' not in gradle:
            raise Stop(f'The {name} guard is gone', f'{ctx.cfg["build"]["gradle_file"]} no longer refuses {name}.',
                       'Restore the Gradle guard before releasing.')
        if os.environ.get(name):
            raise Stop(f'{name} is set in the environment', 'A debug token must never reach a store build.',
                       f'unset {name}, then run again.')
    return 'reviewer hash present (64 hex, never printed); debug-token guard present; no token in env'


def step_build(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    require_clean(ctx)
    h = ctx.local_value('reviewer_code_sha256')
    b = ctx.cfg['build']
    aab = ctx.wt(b['aab'])
    started = dt.datetime.now().timestamp()
    cmd = list(b['command']) + [f'--dart-define=REVIEWER_CODE_SHA256={h}']
    testlock(ctx, 'build', cmd, ctx.mobile(), redact=[h])
    if not aab.exists() or aab.stat().st_mtime < started:
        raise Stop('No fresh AAB', f'{aab} was not written by this build.', 'Read the build output; run again.')
    return verify_aab(ctx, aab, h)


def verify_aab(ctx: Ctx, aab: Path, h: str) -> str:
    b = ctx.cfg['build']
    want_name = expected_version_name(ctx)
    with zipfile.ZipFile(aab) as z:
        manifest = z.read('base/manifest/AndroidManifest.xml')
        libs = [n for n in z.namelist() if n.endswith('/libapp.so')]
        hashes_ok = bool(libs) and all(h.encode() in z.read(n) for n in libs)
    pkg = ctx.cfg['app']['package'].encode()
    problems = []
    if pkg not in manifest:
        problems.append(f'package {ctx.cfg["app"]["package"]} not in the manifest')
    for suffix in b.get('forbidden_package_suffixes', []):
        if pkg + suffix.encode() in manifest:
            problems.append(f'manifest names {ctx.cfg["app"]["package"]}{suffix}')
    if want_name.encode() not in manifest:
        problems.append(f'versionName {want_name} not in the manifest')
    if b'.dirty' in manifest:
        problems.append('versionName is .dirty')
    if not hashes_ok:
        problems.append('reviewer hash missing from a libapp.so')
    cert = sh(['keytool', '-printcert', '-jarfile', str(aab)])
    m = re.search(r'SHA256:\s*([0-9A-F:]{95})', cert)
    if not m or m.group(1) != b['upload_cert_sha256']:
        problems.append('not signed with the upload key in `build.upload_cert_sha256`')
    if problems:
        raise Stop('The AAB failed verification', '; '.join(problems),
                   'Fix the cause (signing config, clean tree, define), then run the build step again.')
    size = aab.stat().st_size / 1e6
    return (f'{os.path.relpath(aab, ctx.repo)} {size:.0f} MB @ {head(ctx)}; versionName {want_name}, '
            f'versionCode {version_code(ctx.version)}; upload-key signed; hash in {len(libs)} libapp.so')


def step_tag_push(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    built = t.evidence(STEP_NO['build'])
    m = re.search(r'@ ([0-9a-f]{8})', built)
    if not m:
        raise Stop('No built commit recorded', 'Step 15 has no "@ <sha>" evidence.', 'Run the build step again.')
    sha = m.group(1)
    if head(ctx) != sha:
        raise Stop('The worktree moved after the build', f'Built {sha}, worktree is at {head(ctx)}.',
                   'Rebuild (reset steps from the build on) — a tag must name what was built.')
    existing = git(ctx.wt(), 'rev-parse', '--verify', '--quiet', f'refs/tags/{ctx.tag}^{{commit}}', check=False)
    if existing and not existing.startswith(sha):
        raise Stop(f'{ctx.tag} already exists elsewhere', f'{ctx.tag} points at {existing[:8]}, not {sha}.',
                   'A published version is never moved. Use a new version.')
    if not existing:
        git(ctx.wt(), 'tag', '-a', ctx.tag, '-m', f'Release {ctx.version}', sha)
    git(ctx.wt(), 'push', 'origin', f'HEAD:refs/heads/{ctx.rc}')
    git(ctx.wt(), 'push', 'origin', f'refs/tags/{ctx.tag}')
    return f'{ctx.tag} → {sha}; {ctx.rc} and tag pushed'


def step_upload(ctx: Ctx, t: Tracker) -> str:
    import play_api
    notes = notes_text(t.section(f'### Play release notes ({ctx.cfg["play"]["release_notes_language"]})'))
    raw = t.section(f'### Play release notes ({ctx.cfg["play"]["release_notes_language"]})')
    limit = ctx.cfg['play']['release_notes_limit']
    if 'DRAFT' in raw or not notes:
        raise Wait('The release notes are still the draft. Rewrite § Play release notes in plain words for users '
                   f'(≤ {limit} characters) and delete the DRAFT line, then run again.')
    if len(notes) > limit:
        raise Stop('Release notes too long', f'{len(notes)} characters; Play allows {limit}.', 'Shorten them.')
    path = ctx.local_value('play_service_account_json')
    client = play_api.PlayClient(os.path.expanduser(path), ctx.cfg['app']['package'])
    play = ctx.cfg['play']
    code = version_code(ctx.version)
    result = client.upload_to_track(
        aab=ctx.wt(ctx.cfg['build']['aab']), version_code=code, track=play['upload_track'],
        release_name=ctx.version, status=play['upload_status'],
        notes={play['release_notes_language']: notes},
        changes_not_sent_for_review=play.get('changes_not_sent_for_review', False))
    return f'versionCode {code} on `{play["upload_track"]}` ({play["upload_status"]}); {result}'


def manual(guide_fn):
    def step(ctx: Ctx, t: Tracker) -> str:
        raise Wait(guide_fn(ctx, t))
    return step


def guide_from_config(key: str):
    def guide(ctx: Ctx, t: Tracker) -> str:
        g = ctx.cfg['manual'][key]
        n = STEP_NO[key]
        f = {**ctx.fmt(), 'firebase_project': ctx.cfg['firebase']['project_id'], 'package': ctx.cfg['app']['package']}
        return (f'Step {n} — {g["title"]}                                    (Who: me)\n'
                f'Where:   {g["where"].format(**f)}\n'
                'Do:\n' + '\n'.join(f'  {i}. {s.format(**f)}' for i, s in enumerate(g['do'], 1)) + '\n'
                f'Done when: {g["done_when"].format(**f)}\n'
                f'Give back: {g["give_back"].format(**f)}')
    return guide


STATE_COLUMNS = ('Declaration', 'Current answer', 'Status', 'Source', 'Last confirmed', 'Re-check when')


def state_table(ctx: Ctx) -> tuple[list[str], int, dict[str, int]]:
    """The declarations table: all lines, the header's index, and each column's position."""
    lines = ctx.state_file.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith('| Declaration |'):
            cols = {name: j for j, name in enumerate(split_row(line))}
            missing = [c for c in STATE_COLUMNS if c not in cols]
            if missing:
                raise Stop('State table columns missing', f'{ctx.state_file.name} lacks: {", ".join(missing)}.',
                           f'Its header must be: | {" | ".join(STATE_COLUMNS)} |')
            return lines, i, cols
    raise Stop('No declarations table', f'{ctx.state_file} has no "| Declaration |" table.',
               'Restore it from git.')


def state_rows(ctx: Ctx) -> list[dict]:
    lines, header, col = state_table(ctx)
    rows = []
    for line in lines[header + 2:]:
        if not line.startswith('| '):
            break
        c = split_row(line)
        rows.append({'name': c[col['Declaration']], 'answer': c[col['Current answer']],
                     'status': c[col['Status']], 'confirmed': c[col['Last confirmed']],
                     'inputs': re.findall(r'`([a-z_]+)`', c[col['Re-check when']])})
    return rows


def changed_inputs(ctx: Ctx) -> dict[str, str]:
    """Which re-check inputs changed since the last release, with the reason."""
    base = baseline_ref(ctx)
    diff = set(git(ctx.wt(), 'diff', '--name-only', f'{base}..HEAD').splitlines())
    out = {}
    for name, globs in ctx.cfg['recheck_inputs'].items():
        hits = [p for p in diff if any(Path(p).match(g) for g in globs)]
        if hits:
            out[name] = f'{hits[0]}' + (f' (+{len(hits) - 1})' if len(hits) > 1 else '')
    return out


def step_declarations(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    changed = changed_inputs(ctx)
    flagged = []
    for r in state_rows(ctx):
        if r['name'].startswith('Sign in details'):
            continue                                   # step 21 owns it
        why = [f'{i} changed ({changed[i]})' for i in r['inputs'] if i in changed]
        if r['status'].startswith((OPEN, DOING)):
            why.append(f'status {r["status"]}')
        if why:
            flagged.append((r, why))
    if not flagged:
        return f'nothing to re-check (inputs unchanged since {baseline_ref(ctx)})'
    items = '\n'.join(f'  - {r["name"]}: now "{r["answer"]}" — because {"; ".join(w)}' for r, w in flagged)
    raise Wait(f'''Step {STEP_NO["declarations"]} — Play Console declarations to re-check      (Who: me)
Where:   Play Console › {ctx.cfg["app"]["name"]} › Policy › App content
Check each, one at a time:
{items}
Done when: each page shows the answer you intend, saved.
Give back: per declaration "<name>: same" or "<name>: <new answer>". I update
         {ctx.state_file.name} with today's date.''')


def sign_in_text(ctx: Ctx) -> str:
    strings = arb(ctx)
    s = ctx.cfg['manual']['sign_in']
    vals = {k: strings[k] for k in s['arb_keys']}
    for k, v in vals.items():
        vals[k] = re.sub(r'\{[a-zA-Z]+\}', '<date>', v)
    return s['text'].format(**vals).strip()


def step_sign_in(ctx: Ctx, t: Tracker) -> str:
    require_worktree(ctx)
    changed = changed_inputs(ctx)
    row = next((r for r in state_rows(ctx) if r['name'].startswith('Sign in details')), None)
    needs = (row is None or row['status'].startswith((OPEN, DOING))
             or any(i in changed for i in (row['inputs'] if row else [])))
    if not needs:
        return f'unchanged since {row["confirmed"]}; labels unchanged'
    text = sign_in_text(ctx)
    s = ctx.cfg['manual']['sign_in']
    limit = s.get('limit')
    # Counted as it will be pasted: with the code in place of the placeholder.
    length = len(text) - len('<REVIEWER CODE>') + int(s.get('code_length', len('<REVIEWER CODE>')))
    if limit and length > limit:
        raise Stop('Sign in text too long', f'{length} characters with the code in place; the field takes {limit}.',
                   'Shorten `manual.sign_in.text` in release.config.yaml, then run again.')
    count = f'[{length}/{limit} with the code]' if limit else f'[{length} chars; check the field\'s limit]'
    raise Wait(f'''Step {STEP_NO["sign_in"]} — Sign in details                              (Who: me)
Where:   Play Console › {ctx.cfg["app"]["name"]} › Policy › App content › App access › Manage
         → "All or some functionality is restricted" → Add instructions
Enter:   Name: {ctx.cfg["manual"]["sign_in"]["name"]}
         Any other information (replace <REVIEWER CODE> with the code from your
         release.local.yaml; never paste the code into chat):
---
{text}
---  {count}
Done when: the instructions are saved and App access shows them.
Give back: "sign in done" and today's date.''')


def step_promote(ctx: Ctx, t: Tracker) -> str:
    raise Wait(f'''Step {STEP_NO["promote"]} — Promote                                   (Who: auto, on your go)
The build is on `{ctx.cfg["play"]["upload_track"]}`. Tell me the target track and rollout, e.g.
"promote {ctx.version} to production at 10%". Nothing moves without that.
Tracks: {", ".join(ctx.cfg["play"]["tracks"])}''')


def step_close(ctx: Ctx, t: Tracker) -> str:
    return f'release {ctx.version} closed {dt.date.today().isoformat()}'


def guide_service_account(ctx: Ctx) -> str:
    project = ctx.cfg['firebase']['project_id']
    return f'''Step {STEP_NO["service_account"]} — Play API service account          (Who: me, once per app)
1. console.cloud.google.com → project `{project}` → APIs & Services → Library →
   "Google Play Android Developer API" → Enable.
2. IAM & Admin → Service accounts → Create service account. Name: `play-release`.
   Grant it NO project roles (skip that page) → Done.
3. Open it → Keys → Add key → Create new key → JSON. Save the file OUTSIDE every repo,
   e.g. ~/.config/belmia/play-release-{project}.json, then: chmod 600 <file>.
4. Put the path (not the contents) in {ctx.local_path.name}:
     play_service_account_json: ~/.config/belmia/play-release-{project}.json
5. play.google.com/console → Users and permissions → Invite new users → the service
   account's email (…@{project}.iam.gserviceaccount.com) → App permissions → Add app →
   {ctx.cfg["app"]["name"]} only → tick ONLY: "View app information (read-only)",
   "Release to testing tracks", "Release apps to production, exclude devices, and use
   Play App Signing" (only needed for promote) → Invite user. No account permissions,
   nothing financial, no admin.
Done when: the account shows under Users and permissions with those app permissions.
Then run again: I open and delete an empty edit to prove access (nothing is changed).
Give back: nothing — the check is automatic. Never paste the JSON into chat.'''


RUNNERS = {
    'preflight': step_preflight,
    'service_account': step_service_account,
    'worktree': step_worktree,
    'fixes': step_fixes,
    'format_l10n': step_format_l10n,
    'analyze': step_analyze,
    'tests': step_tests,
    'ci': step_ci,
    'gate_policy': step_gate_policy,
    'gate_priv1': step_gate_priv1,
    'gate_sdk': step_gate_sdk,
    'cut': step_cut,
    'changelog': step_changelog,
    'gate_secrets': step_gate_secrets,
    'build': step_build,
    'tag_push': step_tag_push,
    'upload': step_upload,
    'phone': manual(guide_from_config('phone')),
    'firebase': manual(guide_from_config('firebase')),
    'declarations': step_declarations,
    'sign_in': step_sign_in,
    'promote': step_promote,
    'publish': manual(guide_from_config('publish')),
    'close': step_close,
}


# --------------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------------

def load(ctx: Ctx) -> Tracker:
    if not ctx.tracker.exists():
        Tracker.create(ctx)
        t = Tracker(ctx)
        t.log('tracker created')
        t.save()
        commit_records(ctx, f'docs(release): open the {ctx.version} release tracker')
    return Tracker(ctx)


def show(t: Tracker, current: str | None = None) -> None:
    if current:
        print(current)
        print()
    print(t.table())


def cmd_run(ctx: Ctx) -> int:
    t = load(ctx)
    message = None
    while True:
        n = t.first_open()
        if n is None:
            message = f'Release {ctx.version}: every step is ✅.'
            break
        key = STEPS[n - 1][0]
        t.set(n, DOING)
        try:
            evidence = RUNNERS[key](ctx, t)
        except Wait as w:
            message = w.guide
            break
        except Stop as s:
            t.set(n, BLOCKED, f'{s.what} — see § Log')
            t.log(f'step {n} failed: {s.what}. Why: {s.why} Fix: {s.fix}')
            t.save()
            message = f'⛔ Step {n} — {s.what}\nWhy: {s.why}\nFix: {s.fix}'
            break
        t.set(n, DONE, evidence)
        commit_records(ctx, f'docs(release): {ctx.version} step {n} ✅')
    commit_records(ctx, f'docs(release): {ctx.version} tracker')
    show(t, message)
    return 0


def cmd_done(ctx: Ctx, n: int, evidence: str) -> int:
    t = load(ctx)
    key = STEPS[n - 1][0]
    who = STEPS[n - 1][2]
    if not who.startswith('me'):
        print(f'Step {n} is automatic; `run` records it.')
        return 2
    if not evidence.strip() or evidence.strip().lower() in ('done', 'ok', 'yes'):
        print('Evidence must say what was seen (a date, count, sha or path), not just "done".')
        return 2
    operator = ctx.cfg['app'].get('operator', 'operator')
    t.set(n, DONE, evidence, source=f'manual ({operator}, {dt.date.today().isoformat()})')
    if key == 'declarations' or key == 'sign_in':
        stamp_state(ctx, key, evidence)
    commit_records(ctx, f'docs(release): {ctx.version} step {n} ✅ (operator)')
    show(t)
    return 0


def stamp_state(ctx: Ctx, key: str, evidence: str) -> None:
    today = dt.date.today().isoformat()
    operator = ctx.cfg['app'].get('operator', 'operator')
    lines, header, col = state_table(ctx)
    for i in range(header + 2, len(lines)):
        if not lines[i].startswith('| '):
            break
        c = split_row(lines[i])
        name = c[col['Declaration']]
        if key == 'sign_in' and name.startswith('Sign in details'):
            c[col['Status']] = f'{DONE} set'
        elif not (key == 'declarations' and name.split(' (')[0].lower() in evidence.lower()):
            continue
        c[col['Last confirmed']] = today
        c[col['Source']] = f'manual ({operator}, {today})'
        lines[i] = '| ' + ' | '.join(c) + ' |'
    ctx.state_file.write_text('\n'.join(lines) + '\n')


def cmd_cut(ctx: Ctx, go: bool) -> int:
    t = load(ctx)
    n = STEP_NO['cut']
    for gate in ('gate_policy', 'gate_priv1', 'gate_sdk'):
        if t.status(STEP_NO[gate]) != DONE:
            print(f'Refused: step {STEP_NO[gate]} ({gate}) is not ✅. The privacy gates come before the cut.')
            return 2
    if not go:
        print('Refused: the cut needs the operator\'s go (`--go`).')
        return 2
    try:
        sha = do_cut(ctx)
    except Stop as s:
        print(f'⛔ {s.what}\nWhy: {s.why}\nFix: {s.fix}')
        return 1
    t.set(n, DONE, f'`Version {ctx.version}` = {sha}; versionCode {version_code(ctx.version)}')
    commit_records(ctx, f'docs(release): {ctx.version} cut at {sha}')
    show(t)
    return 0


def cmd_cherry_pick(ctx: Ctx, shas: list[str]) -> int:
    t = load(ctx)
    if t.status(STEP_NO['upload']) == DONE:
        print('Refused: this version is already uploaded. A new fix needs a new version.')
        return 2
    try:
        require_worktree(ctx)
        require_clean(ctx)
        for sha in shas:
            full = git(ctx.repo, 'rev-parse', '--verify', f'{sha}^{{commit}}')
            if subprocess.run(['git', '-C', str(ctx.wt()), 'merge-base', '--is-ancestor', full, 'HEAD']).returncode == 0:
                t.append_section('## Cherry-picks', f'- `{full[:8]}` already in {ctx.rc} — skipped')
                continue
            proc = subprocess.run(['git', '-C', str(ctx.wt()), 'cherry-pick', '-x', full], capture_output=True, text=True)
            if proc.returncode != 0:
                subprocess.run(['git', '-C', str(ctx.wt()), 'cherry-pick', '--abort'], capture_output=True)
                raise Stop(f'Cherry-pick of {full[:8]} conflicts', proc.stderr[-1200:] or proc.stdout[-1200:],
                           'Nothing was applied. Rebase that fix onto the RC on its own branch, then pick the result.')
            subject = git(ctx.wt(), 'log', '-1', '--format=%s')
            t.append_section('## Cherry-picks', f'- `{full[:8]}` → `{head(ctx)}` {subject} ({dt.date.today().isoformat()})')
    except Stop as s:
        print(f'⛔ {s.what}\nWhy: {s.why}\nFix: {s.fix}')
        commit_records(ctx, f'docs(release): {ctx.version} cherry-pick refused')
        return 1
    reopened = [n for n in CODE_STEPS if t.status(n) == DONE]
    for n in reopened:
        t.set(n, OPEN, '')
    if reopened:
        t.log(f'steps {reopened[0]}–{reopened[-1]} reopened: the code changed')
        t.save()
    commit_records(ctx, f'docs(release): {ctx.version} cherry-picked {", ".join(s[:8] for s in shas)}')
    show(t)
    return 0


def cmd_ack(ctx: Ctx, package: str, why: str) -> int:
    t = load(ctx)
    if len(why.strip()) < 10:
        print('Say what the package does and why it sends nothing off the device.')
        return 2
    t.append_section('## Acknowledgements', f'- `{package}` — {why.strip()} ({dt.date.today().isoformat()})')
    if t.status(STEP_NO['gate_sdk']) == BLOCKED:
        t.set(STEP_NO['gate_sdk'], OPEN, '')
    commit_records(ctx, f'docs(release): {ctx.version} acknowledge {package}')
    show(t)
    return 0


def cmd_promote(ctx: Ctx, to: str, fraction: float, go: bool) -> int:
    import play_api
    t = load(ctx)
    if not go:
        print('Refused: promotion needs the operator\'s explicit go (`--go`).')
        return 2
    if t.status(STEP_NO['upload']) != DONE:
        print('Refused: the build is not uploaded yet.')
        return 2
    if to not in ctx.cfg['play']['tracks']:
        print(f'Unknown track {to}; known: {", ".join(ctx.cfg["play"]["tracks"])}')
        return 2
    if not 0 < fraction <= 1:
        print('Rollout must be between 0 (exclusive) and 1.')
        return 2
    n = STEP_NO['promote']
    t.set(n, DOING)
    path = ctx.local_value('play_service_account_json')
    try:
        client = play_api.PlayClient(os.path.expanduser(path), ctx.cfg['app']['package'])
        result = client.promote(version_code=version_code(ctx.version), source=ctx.cfg['play']['upload_track'],
                                target=ctx.cfg['play']['tracks'][to], release_name=ctx.version, fraction=fraction,
                                changes_not_sent_for_review=ctx.cfg['play'].get('changes_not_sent_for_review', False))
    except Stop as s:
        t.set(n, BLOCKED, f'{s.what} — see § Log')
        t.log(f'step {n} failed: {s.what}. Why: {s.why} Fix: {s.fix}')
        t.save()
        commit_records(ctx, f'docs(release): {ctx.version} promote failed')
        print(f'⛔ {s.what}\nWhy: {s.why}\nFix: {s.fix}')
        return 1
    t.set(n, DONE, f'versionCode {version_code(ctx.version)} → `{to}` at {fraction:.0%}; {result}')
    commit_records(ctx, f'docs(release): {ctx.version} promoted to {to}')
    show(t)
    return 0


LISTING_NEEDS = [  # what Play requires before a listing can be published (Play Console Help)
    ('shortDescription', 'Short description (≤ 80 characters)'),
    ('fullDescription', 'Full description (≤ 4,000 characters)'),
]
IMAGE_NEEDS = [('icon', 1, 'App icon, 512 × 512 PNG'), ('featureGraphic', 1, 'Feature graphic, 1024 × 500'),
               ('phoneScreenshots', 2, 'At least 2 phone screenshots')]


def readout_markdown(ctx: Ctx, r: dict) -> str:
    today = dt.date.today().isoformat()
    out = [f'Read through the Play Developer API on {today} (`release.py readout`). Source: api. '
           'Read-only: the edit was deleted, never committed.', '', '**Tracks**', '',
           '| Track | Releases |', '|---|---|']
    for t in sorted(r['tracks'], key=lambda t: t['track']):
        rel = '; '.join(f'{x.get("name")} — codes {", ".join(x.get("versionCodes", []))}, {x.get("status")}'
                        + (f' at {x["userFraction"]:.0%}' if x.get('userFraction') else '')
                        for x in t.get('releases', [])) or 'none'
        out.append(f'| `{t["track"]}` | {rel} |')
    d = r['details']
    out += ['', '**App details**', '',
            f'- Default language: {d.get("defaultLanguage") or "not set"}',
            f'- Contact email: {d.get("contactEmail") or "**not set** (required)"}',
            f'- Contact website: {d.get("contactWebsite") or "not set"}',
            f'- Contact phone: {d.get("contactPhone") or "not set"}', '', '**Store listing**', '']
    missing = []
    if not d.get('contactEmail'):
        missing.append('Contact email (App details)')
    for l in r['listings']:
        lang = l['language']
        out.append(f'- `{lang}`: title "{l.get("title") or ""}"; short description '
                   f'{len(l.get("shortDescription") or "")} chars; full description '
                   f'{len(l.get("fullDescription") or "")} chars; video {"set" if l.get("video") else "none"}')
        imgs = r['images'].get(lang, {})
        out.append('  - images: ' + ', '.join(f'{k} {v}' for k, v in imgs.items()))
        for field, label in LISTING_NEEDS:
            if not l.get(field):
                missing.append(f'{label} — `{lang}`')
        for kind, need, label in IMAGE_NEEDS:
            if imgs.get(kind, 0) < need:
                missing.append(f'{label} — `{lang}` has {imgs.get(kind, 0)}')
    if not r['listings']:
        missing.append('A store listing in the default language')
    out += ['', '**Missing before the listing can go live:** ' + ('none' if not missing else ''), '']
    out += [f'- {m}' for m in missing]
    out += ['', '**Subscriptions**', '', '| Product | Base plan | State | Billing period | Regions |',
            '|---|---|---|---|---|']
    for s in r['subscriptions']:
        for b in s.get('basePlans', []):
            period = (b.get('autoRenewingBasePlanType') or {}).get('billingPeriodDuration', '—')
            flag = ''
            if 'yearly' in b.get('basePlanId', '') and period != 'P1Y':
                flag = ' ⚠ **not yearly**'
            if 'monthly' in b.get('basePlanId', '') and period != 'P1M':
                flag = ' ⚠ **not monthly**'
            out.append(f'| `{s["productId"]}` | `{b["basePlanId"]}` | {b.get("state")} | {period}{flag} | '
                       f'{len(b.get("regionalConfigs") or [])} |')
    return '\n'.join(out)


def cmd_readout(ctx: Ctx) -> int:
    import play_api
    path = ctx.local_value('play_service_account_json')
    try:
        if not path:
            raise Stop('No service account', '`play_service_account_json` is empty.', 'Do step 2 first.')
        r = play_api.PlayClient(os.path.expanduser(path), ctx.cfg['app']['package']).readout()
    except Stop as s:
        print(f'⛔ {s.what}\nWhy: {s.why}\nFix: {s.fix}')
        return 1
    body = readout_markdown(ctx, r)
    text = ctx.state_file.read_text()
    header = '## Play readout'
    if header in text:
        start = text.index(header)
        nxt = text.find('\n## ', start + len(header))
        text = text[:start] + f'{header}\n\n{body}\n' + (text[nxt:] if nxt != -1 else '')
    else:
        text = text.rstrip() + f'\n\n{header}\n\n{body}\n'
    ctx.state_file.write_text(text)
    if ctx.tracker.exists():
        t = Tracker(ctx)
        t.log(f'Play readout recorded in {ctx.state_file.name} § Play readout (api)')
        t.save()
    commit_records(ctx, f'docs(release): Play readout {dt.date.today().isoformat()}')
    print(body)
    return 0


def cmd_gate(ctx: Ctx, which: str) -> int:
    try:
        require_worktree(ctx)
        t = Tracker(ctx) if ctx.tracker.exists() else None
        out = {'policy': lambda: gate_policy(ctx), 'priv1': lambda: gate_priv1(ctx),
               'sdk': lambda: gate_sdk(ctx, t)}[which]()
        print(f'✅ {which}: {out}')
        return 0
    except Stop as s:
        print(f'⛔ {s.what}\nWhy: {s.why}\nFix: {s.fix}')
        return 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repo', default='.', help='the app repo (its main checkout)')
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('status', 'run'):
        sub.add_parser(name).add_argument('version')
    d = sub.add_parser('done')
    d.add_argument('version')
    d.add_argument('step', type=int)
    d.add_argument('evidence')
    c = sub.add_parser('cut')
    c.add_argument('version')
    c.add_argument('--go', action='store_true')
    cp = sub.add_parser('cherry-pick')
    cp.add_argument('version')
    cp.add_argument('shas', nargs='+')
    a = sub.add_parser('ack')
    a.add_argument('version')
    a.add_argument('package')
    a.add_argument('why')
    pr = sub.add_parser('promote')
    pr.add_argument('version')
    pr.add_argument('--to', required=True)
    pr.add_argument('--fraction', type=float, required=True)
    pr.add_argument('--go', action='store_true')
    sub.add_parser('readout').add_argument('version')
    g = sub.add_parser('gate')
    g.add_argument('version')
    g.add_argument('which', choices=['policy', 'priv1', 'sdk'])
    g.add_argument('--worktree', help='check this checkout instead of the release worktree')
    args = p.parse_args()

    repo = Path(git(Path(args.repo).resolve(), 'rev-parse', '--show-toplevel'))
    try:
        ctx = Ctx(repo, args.version)
    except Stop as s:
        print(f'⛔ {s.what}\nWhy: {s.why}\nFix: {s.fix}')
        return 1
    if getattr(args, 'worktree', None):
        ctx.worktree = Path(args.worktree).resolve()
    if args.cmd == 'status':
        show(load(ctx))
        return 0
    if args.cmd == 'run':
        return cmd_run(ctx)
    if args.cmd == 'done':
        return cmd_done(ctx, args.step, args.evidence)
    if args.cmd == 'cut':
        return cmd_cut(ctx, args.go)
    if args.cmd == 'cherry-pick':
        return cmd_cherry_pick(ctx, args.shas)
    if args.cmd == 'ack':
        return cmd_ack(ctx, args.package, args.why)
    if args.cmd == 'promote':
        return cmd_promote(ctx, args.to, args.fraction, args.go)
    if args.cmd == 'gate':
        return cmd_gate(ctx, args.which)
    if args.cmd == 'readout':
        return cmd_readout(ctx)
    return 2


if __name__ == '__main__':
    sys.exit(main())
