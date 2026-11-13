"""A small Google Play Developer API v3 client for play-release.

Service-account auth with a locally signed JWT (requests + cryptography; no Google SDK). Every
write goes through an *edit*: open → change → commit, so a failure half-way leaves Play
untouched (the edit is deleted). Nothing here prints a token or the key.

Docs: https://developers.google.com/android-publisher/api-ref/rest/v3/edits
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from errors import Stop

API = 'https://androidpublisher.googleapis.com/androidpublisher/v3/applications'
UPLOAD = 'https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications'
SCOPE = 'https://www.googleapis.com/auth/androidpublisher'


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


class PlayClient:
    def __init__(self, key_path: str, package: str):
        path = Path(key_path)
        if not path.exists():
            raise Stop('Service-account key missing', f'{path} does not exist.',
                       'Fix `play_service_account_json` in release.local.yaml (a path, never the JSON).')
        self._key = json.loads(path.read_text())
        self.package = package
        self._token = None
        self._token_expires = 0.0

    # ---------------------------------------------------------------- auth

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        now = int(time.time())
        header = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
        claims = _b64(json.dumps({
            'iss': self._key['client_email'], 'scope': SCOPE, 'aud': self._key['token_uri'],
            'iat': now, 'exp': now + 3600,
        }).encode())
        signing_input = f'{header}.{claims}'.encode()
        private_key = serialization.load_pem_private_key(self._key['private_key'].encode(), password=None)
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        assertion = f'{header}.{claims}.{_b64(signature)}'
        resp = requests.post(self._key['token_uri'], timeout=30, data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': assertion})
        if resp.status_code != 200:
            raise Stop('Service-account sign-in failed', f'HTTP {resp.status_code}: {_error(resp)}',
                       'Check the key file is current (not deleted in Cloud IAM) and the clock is right.')
        body = resp.json()
        self._token = body['access_token']
        self._token_expires = time.time() + int(body.get('expires_in', 3600))
        return self._token

    def _call(self, method: str, url: str, **kwargs) -> dict:
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {self._access_token()}'
        resp = requests.request(method, url, headers=headers, timeout=kwargs.pop('timeout', 120), **kwargs)
        if resp.status_code >= 300:
            raise Stop(f'Play API {method} failed', f'HTTP {resp.status_code} on {url.split("?")[0]}: {_error(resp)}',
                       _hint(resp))
        return resp.json() if resp.content else {}

    # ---------------------------------------------------------------- edits

    def _edit(self) -> str:
        return self._call('POST', f'{API}/{self.package}/edits', json={})['id']

    def _delete(self, edit: str) -> None:
        try:
            self._call('DELETE', f'{API}/{self.package}/edits/{edit}')
        except Stop:
            pass

    def _commit(self, edit: str, changes_not_sent_for_review: bool) -> None:
        params = {'changesNotSentForReview': 'true'} if changes_not_sent_for_review else {}
        self._call('POST', f'{API}/{self.package}/edits/{edit}:commit', params=params)

    def check_access(self) -> None:
        """Opens and deletes an empty edit: proves the account can reach this app, changes nothing."""
        self._delete(self._edit())

    IMAGE_TYPES = ('icon', 'featureGraphic', 'phoneScreenshots', 'sevenInchScreenshots',
                   'tenInchScreenshots', 'tvBanner', 'tvScreenshots', 'wearScreenshots')

    def readout(self) -> dict:
        """Reads what Play holds for this app. Read-only: the edit is deleted, never committed."""
        edit = self._edit()
        base = f'{API}/{self.package}/edits/{edit}'
        try:
            out = {'details': self._call('GET', f'{base}/details'),
                   'tracks': self._call('GET', f'{base}/tracks').get('tracks', []),
                   'listings': self._call('GET', f'{base}/listings').get('listings', []),
                   'images': {}}
            for listing in out['listings']:
                lang = listing['language']
                out['images'][lang] = {
                    kind: len(self._call('GET', f'{base}/listings/{lang}/{kind}').get('images', []))
                    for kind in self.IMAGE_TYPES}
        finally:
            self._delete(edit)
        out['subscriptions'] = self._call('GET', f'{API}/{self.package}/subscriptions').get('subscriptions', [])
        return out

    def _track(self, edit: str, track: str) -> dict:
        return self._call('GET', f'{API}/{self.package}/edits/{edit}/tracks/{track}')

    def _bundle_codes(self, edit: str) -> set[int]:
        bundles = self._call('GET', f'{API}/{self.package}/edits/{edit}/bundles').get('bundles', [])
        return {int(b['versionCode']) for b in bundles}

    # ---------------------------------------------------------------- operations

    def upload_to_track(self, aab: Path, version_code: int, track: str, release_name: str, status: str,
                        notes: dict[str, str], changes_not_sent_for_review: bool,
                        in_app_update_priority: int = 0) -> str:
        """Uploads the bundle (unless Play already has this versionCode) and puts it on [track].

        Idempotent: a versionCode already on the track is reported, not re-sent. The update
        priority is set only here, when the release is created; Play never lets it change.
        """
        edit = self._edit()
        try:
            on_track = self._track(edit, track)
            for release in on_track.get('releases', []):
                if str(version_code) in release.get('versionCodes', []):
                    self._delete(edit)
                    return f'already on `{track}` as "{release.get("name")}" ({release.get("status")}) — nothing sent'
            if version_code in self._bundle_codes(edit):
                uploaded = 'bundle already on Play'
            else:
                with open(aab, 'rb') as fh:
                    got = self._call('POST', f'{UPLOAD}/{self.package}/edits/{edit}/bundles',
                                     params={'uploadType': 'media'}, data=fh,
                                     headers={'Content-Type': 'application/octet-stream'}, timeout=1800)
                if int(got['versionCode']) != version_code:
                    raise Stop('Play read a different versionCode', f'Uploaded bundle is {got["versionCode"]}, '
                               f'expected {version_code}.', 'Check VERSION and the build; nothing was committed.')
                uploaded = 'bundle uploaded'
            release = {
                'name': release_name, 'versionCodes': [str(version_code)], 'status': status,
                'releaseNotes': [{'language': lang, 'text': text} for lang, text in notes.items()],
                'inAppUpdatePriority': in_app_update_priority,
            }
            self._call('PUT', f'{API}/{self.package}/edits/{edit}/tracks/{track}',
                       json={'track': track, 'releases': [release]})
            self._commit(edit, changes_not_sent_for_review)
            return f'{uploaded}; edit committed'
        except Stop:
            self._delete(edit)
            raise

    def promote(self, version_code: int, source: str, target: str, release_name: str, fraction: float,
                changes_not_sent_for_review: bool) -> str:
        """Puts the versionCode already on [source] onto [target], at [fraction] rollout."""
        edit = self._edit()
        try:
            src = self._track(edit, source)
            found = next((r for r in src.get('releases', []) if str(version_code) in r.get('versionCodes', [])), None)
            if not found:
                raise Stop('Not on the source track', f'versionCode {version_code} is not on `{source}`.',
                           'Upload it there first.')
            dst = self._track(edit, target)
            for r in dst.get('releases', []):
                if str(version_code) in r.get('versionCodes', []) and r.get('userFraction', 1.0) == fraction:
                    self._delete(edit)
                    return f'already on `{target}` at {fraction:.0%} — nothing sent'
            release = {'name': release_name, 'versionCodes': [str(version_code)],
                       'releaseNotes': found.get('releaseNotes', []),
                       'inAppUpdatePriority': found.get('inAppUpdatePriority', 0)}
            if fraction < 1:
                release.update(status='inProgress', userFraction=fraction)
            else:
                release['status'] = 'completed'
            self._call('PUT', f'{API}/{self.package}/edits/{edit}/tracks/{target}',
                       json={'track': target, 'releases': [release]})
            self._commit(edit, changes_not_sent_for_review)
            return 'edit committed'
        except Stop:
            self._delete(edit)
            raise


def _error(resp: requests.Response) -> str:
    try:
        return resp.json().get('error', {}).get('message', resp.text[:300])
    except ValueError:
        return resp.text[:300]


def _hint(resp: requests.Response) -> str:
    msg = _error(resp).lower()
    if resp.status_code == 401:
        return 'The token was refused: re-create the key, or check the service account still exists.'
    if resp.status_code == 403 or 'permission' in msg:
        return ('The service account lacks permission for this app: Play Console › Users and permissions › '
                'the account › App permissions — tick the release permissions for this app.')
    if 'draft app' in msg or 'only releases with status draft' in msg:
        return 'The app has never been published: set `play.upload_status: draft` in release.config.yaml.'
    if 'changesnotsentforreview' in msg:
        return 'Set `play.changes_not_sent_for_review` the way the message asks, then run again.'
    if 'version code' in msg and 'already' in msg:
        return 'Play already has this versionCode: run again (the upload step detects it) or use a new version.'
    return 'Read the message above; nothing was committed to Play (the edit was deleted).'
