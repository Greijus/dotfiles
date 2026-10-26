"""Unit tests for release.py's audit gate — the parts that need no repo.

    python3 -m unittest skills/play-release/scripts/test_release.py      (from dotfiles)
    python3 -m unittest test_release                                     (from scripts/)

git is replaced by a fake that answers from a table, so nothing here touches a checkout.
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import release  # noqa: E402
from errors import Stop  # noqa: E402

AUDIT = {'last_audit_sha': '294c6f3b', 'paths': ['mobile/lib'], 'max_commits': 250,
         'max_lines_changed': 6000}


def ctx(audit=AUDIT):
    gates = {'priv1': {}, **({'audit': audit} if audit is not None else {})}
    return SimpleNamespace(cfg={'gates': gates, 'app': {'marker_grep': '^Version '}}, version='1.0b20',
                           tag='v1.0b20', wt=lambda rel='': Path('/repo'))


class FakeGit:
    """Answers the git calls the audit gate makes."""

    def __init__(self, head='aaaaaaaa', ancestor=True, commits=0, numstat='', changed=None):
        self.head, self.ancestor, self.commits, self.numstat = head, ancestor, commits, numstat
        self.changed = changed or {}            # review sha -> files changed under paths since it

    def __call__(self, repo, *args, check=True):
        if args[:2] == ('rev-parse', '--short=8'):
            return self.head
        if args[0] == 'rev-list' and '--not' in args:
            return '0' if self.ancestor else '3'
        if args[0] == 'rev-list':
            return str(self.commits)
        if args[0] == 'log' and '--numstat' in args:
            return self.numstat
        if args[0] == 'diff':
            return self.changed.get(args[2], '')
        if args[0] == 'tag':
            return 'v1.0b19'
        raise AssertionError(f'unexpected git call: {args}')


class Tracker:
    def __init__(self, section_body=None):
        self.lines = [] if section_body is None else [release.REVIEW_HEADER, '', *section_body.splitlines()]
        self.body = section_body or ''

    def section(self, header):
        assert header == release.REVIEW_HEADER
        return self.body


class NumstatLines(unittest.TestCase):
    def test_sums_insertions_and_deletions(self):
        self.assertEqual(release.numstat_lines('10\t2\ta.dart\n\n3\t0\tb.dart\n'), 15)

    def test_binary_files_count_as_none(self):
        self.assertEqual(release.numstat_lines('-\t-\timg.png\n4\t1\tc.dart'), 5)


class CadenceVerdict(unittest.TestCase):
    def test_at_both_limits_passes(self):
        out = release.cadence_verdict(250, 6000, AUDIT, '294c6f3b')
        self.assertEqual(out, 'audit cadence: 250 commits, 6,000 lines since 294c6f3b (limits 250 / 6,000)')

    def test_one_commit_over_stops(self):
        with self.assertRaises(Stop) as cm:
            release.cadence_verdict(251, 10, AUDIT, '294c6f3b')
        self.assertEqual(cm.exception.what, 'A scored re-audit is owed')
        self.assertIn('251 commits / 10 lines under mobile/lib since the audit at 294c6f3b', cm.exception.why)

    def test_one_line_over_stops(self):
        with self.assertRaises(Stop):
            release.cadence_verdict(1, 6001, AUDIT, '294c6f3b')


class AuditCadence(unittest.TestCase):
    def test_measures_commits_and_churn_under_the_paths(self):
        with mock.patch.object(release, 'git', FakeGit(commits=112, numstat='2000\t340\tx.dart')):
            self.assertEqual(release.audit_cadence(ctx()),
                             'audit cadence: 112 commits, 2,340 lines since 294c6f3b (limits 250 / 6,000)')

    def test_churn_over_the_limit_stops(self):
        with mock.patch.object(release, 'git', FakeGit(commits=40, numstat='5000\t1500\tx.dart')):
            with self.assertRaises(Stop) as cm:
                release.audit_cadence(ctx())
        self.assertIn('6,500 lines', cm.exception.why)

    def test_audit_off_this_branch_stops(self):
        with mock.patch.object(release, 'git', FakeGit(ancestor=False)):
            with self.assertRaises(Stop) as cm:
                release.audit_cadence(ctx())
        self.assertEqual(cm.exception.what, 'The last audit is not on this branch')

    def test_unreadable_sha_stops(self):
        with self.assertRaises(Stop):
            release.audit_sha({'last_audit_sha': 12345678.5})


class DeltaReviewLines(unittest.TestCase):
    def test_parses_the_lines_cmd_review_writes(self):
        body = ('- `aaaaaaaa` — /code-review high v1.0b19..HEAD: 3 findings, 3 fixed (2026-10-26)\n'
                'free text that is not an entry\n'
                '- `bbbbbbbb` — re-review after the fix (2026-10-27)')
        self.assertEqual(release.delta_reviews(body), ['aaaaaaaa', 'bbbbbbbb'])

    def test_placeholder_has_no_entries(self):
        self.assertEqual(release.delta_reviews('_None._'), [])


class DeltaReviewOk(unittest.TestCase):
    def run_gate(self, body, **fake):
        with mock.patch.object(release, 'git', FakeGit(**fake)):
            return release.delta_review_ok(ctx(), Tracker(body))

    def test_review_at_head_passes(self):
        out = self.run_gate('- `aaaaaaaa` — review (2026-10-26)', head='aaaaaaaa')
        self.assertEqual(out, 'delta review @ aaaaaaaa')

    def test_review_behind_head_with_no_code_change_passes(self):
        out = self.run_gate('- `bbbbbbbb` — review (2026-10-26)', head='aaaaaaaa', changed={'bbbbbbbb': ''})
        self.assertEqual(out, 'delta review @ bbbbbbbb; nothing under mobile/lib changed up to aaaaaaaa')

    def test_review_behind_head_with_code_change_stops(self):
        with self.assertRaises(Stop) as cm:
            self.run_gate('- `bbbbbbbb` — review (2026-10-26)', head='aaaaaaaa',
                          changed={'bbbbbbbb': 'mobile/lib/a.dart'})
        self.assertEqual(cm.exception.what, 'The delta review is missing or stale')
        self.assertIn('Review v1.0b19..HEAD', cm.exception.fix)
        self.assertIn('release.py review 1.0b20', cm.exception.fix)

    def test_newest_matching_entry_wins(self):
        body = '- `cccccccc` — old (2026-10-20)\n- `bbbbbbbb` — new (2026-10-26)'
        out = self.run_gate(body, head='aaaaaaaa', changed={'cccccccc': 'mobile/lib/a.dart', 'bbbbbbbb': ''})
        self.assertTrue(out.startswith('delta review @ bbbbbbbb'))

    def test_no_entry_stops(self):
        with self.assertRaises(Stop) as cm:
            self.run_gate('_None._')
        self.assertIn('no entry', cm.exception.why)

    def test_tracker_without_the_section_stops(self):
        with self.assertRaises(Stop):
            self.run_gate(None)


class NotConfigured(unittest.TestCase):
    def test_every_half_is_skipped_without_gates_audit(self):
        def no_git(*_args, **_kw):
            raise AssertionError('git must not run when the gate is not configured')
        with mock.patch.object(release, 'git', no_git):
            self.assertEqual(release.audit_cadence(ctx(None)), 'audit gate: not configured')
            self.assertEqual(release.delta_review_ok(ctx(None), None), 'audit gate: not configured')
            self.assertEqual(release.audit_gate(ctx(None), None), 'audit gate: not configured')


class Step12(unittest.TestCase):
    def test_numbering_is_unchanged(self):
        self.assertEqual(len(release.STEPS), 24)
        self.assertEqual(release.STEP_NO['cut'], 12)
        self.assertIn('after the audit gate (cadence + delta review)', release.STEPS[11][1])


if __name__ == '__main__':
    unittest.main()
