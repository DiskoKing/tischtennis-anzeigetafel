import os
import copy
import base64
import http.client
from datetime import date
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import server


def row(sid, day='06.11.2026', started=True, said='96'):
    marker = '<img title="Spiel gestartet">' if started else '<img title="Nicht gestartet">'
    return f'<tr onclick="location.href=\'?Area=Report&amp;SAID={said}&amp;SID={sid}\';"><td>{marker}</td><td>{day}</td><td>Heim {sid} gegen Gast {sid}</td></tr>'


class SelectionTests(unittest.TestCase):
    def test_two_games_require_choice_and_finished_are_excluded(self):
        html = '<h2>Laufende Live-Spielberichte</h2><table>' + row('1') + row('2') + row('3', started=False) + '</table>'
        games = server.parse_games(html)
        self.assertEqual([game['sid'] for game in games], ['1', '2'])
        self.assertEqual(server.choose_game(games, None, '2026-11-06'), (None, 'selection_required'))
        choice = {'said': '96', 'sid': '2', 'selectedOn': '2026-11-06'}
        self.assertEqual(server.choose_game(games, choice, '2026-11-06')[0]['sid'], '2')
        self.assertEqual(server.choose_game(games, choice, '2026-11-07')[1], 'selection_required')

    def test_today_preferred_and_no_arbitrary_choice(self):
        games = server.parse_games('<h2>Laufende Live-Spielberichte</h2><table>' + row('4', '05.11.2026') + row('5') + '</table>')
        self.assertEqual(server.choose_game(games, None, '2026-11-06')[0]['sid'], '5')
        self.assertEqual(server.choose_game([], None)[1], 'waiting')
        self.assertEqual(server.choose_game(games[:1], None, '2026-11-06')[0]['sid'], '4')

    def test_link_support_duplicates_and_expired_login(self):
        html = '<h2>Laufende Live-Spielberichte</h2><table><tr><td><img title="Spiel gestartet"><a href="?Area=Report&amp;SAID=96&amp;SID=1">06.11.26 Team A – Team B</a></td></tr>' + row('1') + '</table>'
        self.assertEqual(len(server.parse_games(html)), 1)
        with self.assertRaises(RuntimeError):
            server.parse_games('<input name="password">')


class ConfigAndApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ttsv-v2-test-')
        self.root = Path(self.temp.name)
        (self.root/'public').mkdir()
        (self.root/'public/settings.html').write_text('<h1>Settings</h1>')
        self.app = server.App(self.root)
        self.app.config['web4sport']['password'] = 'TEST-ONLY-NOT-A-REAL-PASSWORD'
        self.app.config['web4sport']['username'] = 'test'
        server.atomic_json(self.app.path, self.app.config)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.http.app = self.app
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.http.server_port}'

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, token=True, origin=None, content_type='application/json'):
        headers = {'Content-Type': content_type}
        if token:
            headers['X-Scoreboard-CSRF'] = self.app.csrf
        if origin:
            headers['Origin'] = origin
        request = urllib.request.Request(self.base + path, data=data, headers=headers)
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.read()

    def test_password_never_returned_and_blank_preserves(self):
        _, body = self.request('/api/config')
        self.assertNotIn(b'TEST-ONLY', body)
        public = json.loads(body)
        self.assertTrue(public['web4sport']['passwordSet'])
        self.assertNotIn('password', public['web4sport'])
        self.request('/api/config', json.dumps({'web4sport': {'username': 'test', 'password': ''}}).encode())
        self.assertEqual(self.app.config['web4sport']['password'], 'TEST-ONLY-NOT-A-REAL-PASSWORD')
        self.request('/api/config', b'{"web4sport":{"clearPassword":true}}')
        self.assertEqual(self.app.config['web4sport']['password'], '')

    def test_username_change_does_not_reuse_another_accounts_password(self):
        result = server.validate_update(self.app.config, {'web4sport': {'username': 'another-user', 'password': ''}})
        self.assertEqual(result['web4sport']['password'], '')

    def test_private_files_are_not_served(self):
        for path in ['/private/config.json', '/../private/config.json', '/%2e%2e/private/config.json', '/server.py', '/janova_reader.py']:
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                self.request(path)
            self.assertEqual(error.exception.code, 404)

    def test_csrf_origin_and_validation(self):
        for token, origin in [(False, None), (True, 'https://example.invalid')]:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/config', b'{"dataSource":"web4sport"}', token, origin)
            self.assertEqual(error.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/config', b'{"club":{"primary":"red"}}')
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.app.config['dataSource'], 'janova')

    def test_persistence_no_design_restart_and_source_reset(self):
        before = self.app.epoch
        self.request('/api/config', b'{"club":{"background":"#112233","website":"www.example.org"}}')
        self.assertEqual(self.app.epoch, before)
        self.assertEqual(server.App(self.root).config['club']['background'], '#112233')
        self.app.payload = {'sid': 'old'}
        self.request('/api/config', b'{"dataSource":"web4sport"}')
        self.assertIsNone(self.app.payload)
        self.assertEqual(self.app.get_data('janova')['status'], 'inactive')
        if os.name != 'nt':
            self.assertEqual(self.app.path.stat().st_mode & 0o777, 0o600)

    def test_selection_only_from_current_candidates(self):
        self.app.config['dataSource'] = 'web4sport'
        self.app.candidates = [{'said': '96', 'sid': '123', 'date': '2026-11-06', 'label': 'Team A gegen Team B'}]
        self.app.status = 'selection_required'
        self.assertEqual(self.app.get_data('web4sport')['matches'], [])
        self.request('/api/game', b'{"said":"96","sid":"123"}')
        self.assertEqual(self.app.config['web4sport']['selection']['sid'], '123')
        restored = server.App(self.root)
        self.assertEqual(restored.config['web4sport']['selection']['sid'], '123')
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/game', b'{"said":"96","sid":"999"}')

    def test_logo_and_reconnect(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/logo', b'<svg/>')
        # A real source image is used by the live installation checks.
        payload = b'\x89PNG\r\n\x1a\n' + b'test'
        self.request('/api/logo', payload, content_type='image/png')
        _, body = self.request('/api/logo')
        self.assertEqual(body, payload)
        if os.name != 'nt':
            self.assertEqual((self.app.private/'club-logo').stat().st_mode & 0o777, 0o600)
        self.request('/api/reconnect', b'{}')
        self.assertTrue(self.app.restart_requested.is_set())

    def test_display_preferences_persist_without_reader_restart(self):
        self.assertEqual(self.app.config['display'], {'mode': 'rotate', 'intervalSeconds': 30})
        epoch = self.app.epoch
        for mode in ('compact', 'detail', 'rotate'):
            self.request('/api/config', json.dumps({'display': {'mode': mode, 'intervalSeconds': 45}}).encode())
            self.assertEqual(server.App(self.root).config['display'], {'mode': mode, 'intervalSeconds': 45})
            self.assertEqual(self.app.epoch, epoch)
        for seconds in (0, -1, 3601, 2.5, True, '30'):
            with self.assertRaises(ValueError):
                server.validate_update(self.app.config, {'display': {'mode': 'rotate', 'intervalSeconds': seconds}})

    def test_existing_configuration_gets_30_second_default(self):
        config = copy.deepcopy(self.app.config)
        config.pop('display')
        server.atomic_json(self.app.path, config)
        migrated = server.App(self.root)
        self.assertEqual(migrated.config['display'], {'mode': 'rotate', 'intervalSeconds': 30})
        self.assertEqual(migrated.config['web4sport']['password'], config['web4sport']['password'])

    def test_sponsor_upload_rotation_config_and_remove(self):
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3foAAAAASUVORK5CYII=')
        epoch = self.app.epoch
        self.assertEqual(self.app.config['sponsors'], {'enabled': False, 'intervalSeconds': 10, 'introText': 'unterstützt von:', 'items': []})
        for _ in range(2):
            self.request('/api/sponsors/upload', png, content_type='image/png')
        items = self.app.public_config()['sponsors']['items']
        self.assertEqual(len(items), 2)
        self.assertNotEqual(items[0]['id'], items[1]['id'])
        self.assertTrue(all(set(item) == {'id', 'name', 'logo'} for item in items))
        _, image = self.request(items[0]['logo'])
        self.assertEqual(image, png)
        self.request('/api/config', b'{"sponsors":{"enabled":true,"intervalSeconds":7}}')
        persisted = server.App(self.root).config['sponsors']
        self.assertTrue(persisted['enabled'])
        self.assertEqual(persisted['intervalSeconds'], 7)
        self.assertEqual(len(persisted['items']), 2)
        self.assertEqual(self.app.epoch, epoch)
        self.request('/api/sponsors/remove', json.dumps({'id': items[0]['id']}).encode())
        self.assertEqual(len(self.app.config['sponsors']['items']), 1)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(items[0]['logo'])
        self.assertEqual(error.exception.code, 404)
        self.assertTrue((self.app.private/'sponsor-archive'/items[0]['id']).exists())

    def test_sponsor_validation_and_csrf(self):
        for patch in [{'enabled': True, 'intervalSeconds': 0}, {'enabled': 1, 'intervalSeconds': 10},
                      {'enabled': True, 'intervalSeconds': 10, 'link': 'https://example.org'},
                      {'enabled': True, 'intervalSeconds': 10, 'items': []}]:
            with self.assertRaises(ValueError):
                server.validate_update(self.app.config, {'sponsors': patch})
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/sponsors/upload', b'not-an-image', token=False)
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/sponsors/upload', b'<svg/>')
        self.assertEqual(self.app.config['sponsors']['items'], [])

    def test_settings_only_allow_same_origin_overlay(self):
        with urllib.request.urlopen(self.base+'/settings.html?embedded=1',timeout=3) as response:
            self.assertEqual(response.headers['X-Frame-Options'],'SAMEORIGIN')
            self.assertEqual(response.headers['Content-Security-Policy'],"frame-ancestors 'self'")
        with urllib.request.urlopen(self.base+'/api/config',timeout=3) as response:
            self.assertEqual(response.headers['X-Frame-Options'],'DENY')

    def test_sponsor_intro_default_custom_empty_and_migration(self):
        self.assertEqual(self.app.config['sponsors']['introText'], 'unterstützt von:')
        epoch = self.app.epoch
        for text in ('Unsere Unterstützer:', '', '<b>Nur Text</b>'):
            self.request('/api/config', json.dumps({'sponsors': {'enabled': True, 'intervalSeconds': 10, 'introText': text}}).encode())
            self.assertEqual(server.App(self.root).config['sponsors']['introText'], text)
            self.assertEqual(self.app.epoch, epoch)
        with self.assertRaises(ValueError):
            server.validate_update(self.app.config, {'sponsors': {'enabled': True, 'intervalSeconds': 10, 'introText': 'x'*101}})
        config = copy.deepcopy(self.app.config)
        config['sponsors'].pop('introText')
        server.atomic_json(self.app.path, config)
        restored = server.App(self.root)
        self.assertEqual(restored.config['sponsors']['introText'], 'unterstützt von:')
        self.assertTrue(restored.config['sponsors']['enabled'])

    def test_gif_club_and_sponsor_logos_preserve_original_bytes(self):
        gif = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        self.request('/api/logo', gif, content_type='image/gif')
        with urllib.request.urlopen(self.base+'/api/logo',timeout=3) as response:
            self.assertEqual(response.headers['Content-Type'],'image/gif')
            self.assertEqual(response.read(),gif)
        self.request('/api/sponsors/upload', gif, content_type='image/gif')
        item=self.app.config['sponsors']['items'][0]
        with urllib.request.urlopen(self.base+item['logo'],timeout=3) as response:
            self.assertEqual(response.headers['Content-Type'],'image/gif')
            self.assertEqual(response.read(),gif)
        self.assertEqual(server.image_type(b'GIF87a'+b'test'),'image/gif')

    def test_ten_megabyte_upload_boundary(self):
        size = 10 * 1024 * 1024
        image = b'GIF89a' + b'\0' * (size - 6)
        self.request('/api/logo', image, content_type='image/gif')
        self.assertEqual((self.app.private/'club-logo').stat().st_size, size)
        self.request('/api/sponsors/upload', image, content_type='image/gif')
        identity = self.app.config['sponsors']['items'][0]['id']
        self.assertEqual((self.app.private/'sponsors'/identity).stat().st_size, size)
        for path in ('/api/logo', '/api/sponsors/upload'):
            connection = http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
            connection.putrequest('POST',path)
            connection.putheader('Content-Length',str(size+1))
            connection.putheader('X-Scoreboard-CSRF',self.app.csrf)
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status,413)
            response.read()
            connection.close()

    def test_background_modes_upload_privacy_and_persistence(self):
        self.assertEqual(self.app.config['background'], {'mode': 'css', 'overlayPercent': 58})
        epoch = self.app.epoch
        self.request('/api/config', b'{"background":{"mode":"original","overlayPercent":35}}')
        public = self.app.public_config()['background']
        self.assertEqual(public['image'], 'assets/default-background.svg')
        self.assertFalse(public['customSet'])
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/config', b'{"background":{"mode":"custom","overlayPercent":35}}')
        gif = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        self.request('/api/background', gif, content_type='image/gif')
        self.request('/api/config', b'{"background":{"mode":"custom","overlayPercent":60}}')
        self.assertEqual(server.App(self.root).config['background'], {'mode': 'custom', 'overlayPercent': 60})
        self.assertTrue(self.app.public_config()['background']['customSet'])
        self.assertTrue(self.app.public_config()['background']['image'].startswith('/api/background?v='))
        _, body = self.request('/api/background')
        self.assertEqual(body, gif)
        if os.name != 'nt':
            self.assertEqual((self.app.private/'custom-background').stat().st_mode & 0o777, 0o600)
        self.request('/api/config', b'{"background":{"mode":"css","overlayPercent":60}}')
        self.assertEqual(self.app.public_config()['background']['image'], '')
        self.assertTrue(self.app.public_config()['background']['customSet'])
        self.assertEqual(self.app.epoch, epoch)
        for value in ({'mode': 'invalid', 'overlayPercent': 20}, {'mode': 'css', 'overlayPercent': -1},
                      {'mode': 'css', 'overlayPercent': 101}, {'mode': 'original', 'overlayPercent': True}):
            with self.assertRaises(ValueError):
                server.validate_update(self.app.config, {'background': value})

    def test_janova_live_link_extracts_only_referee_id(self):
        self.assertEqual(server.janova_identity('  ExampleReferee123  '), 'ExampleReferee123')
        self.assertEqual(server.janova_identity('https://janova.app/live/stream?id=ExampleReferee123&sb=4'), 'ExampleReferee123')
        self.assertEqual(server.janova_identity('https://janova.app/live/stream?sb=1&id=ExampleReferee123'), 'ExampleReferee123')
        self.request('/api/config', b'{"janova":{"refereeId":"https://janova.app/live/stream?id=ExampleReferee123&sb=4"}}')
        self.assertEqual(server.App(self.root).config['janova']['refereeId'], 'ExampleReferee123')
        for value in ('https://evil.example/live/stream?id=abc', 'https://janova.app/live/urls',
                      'https://janova.app/live/stream?id=a&id=b', 'https://janova.app/live/stream?id=',
                      'https://janova.app/live/stream?id=bad%2Fid', 'https://janova.app.evil.example/live/stream?id=abc'):
            with self.assertRaises(ValueError):
                server.janova_identity(value)




class JanovaLoginTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        key = patch('server.janova_auth_key', return_value='test-public-app-key')
        key.start()
        self.addCleanup(key.stop)

    def test_login_returns_only_id_and_uses_fixed_https_endpoint(self):
        from unittest.mock import patch, Mock
        response = Mock(status_code=200)
        response.json.return_value = {'localId': 'account_123', 'idToken': 'secret-token', 'refreshToken': 'secret-refresh'}
        with patch('server.requests.post', return_value=response) as post:
            self.assertEqual(server.janova_login(' user@example.com ', 'secret-password'), 'account_123')
            args, kwargs = post.call_args
            self.assertEqual(args[0], 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword')
            self.assertFalse(kwargs['allow_redirects'])
            self.assertEqual(kwargs['json']['email'], 'user@example.com')
            self.assertEqual(kwargs['timeout'], 20)

    def test_failures_do_not_leak_provider_response(self):
        from unittest.mock import patch, Mock
        for status, data in [(400, {'error': {'message': 'INVALID_LOGIN_CREDENTIALS secret'}}), (200, {'localId': ''}), (302, {})]:
            response = Mock(status_code=status)
            response.json.return_value = data
            with patch('server.requests.post', return_value=response):
                with self.assertRaises(server.JanovaLoginError) as error:
                    server.janova_login('user@example.com', 'secret-password')
                self.assertNotIn('secret', str(error.exception))
        with patch('server.requests.post', side_effect=server.requests.Timeout('secret')):
            with self.assertRaises(server.JanovaLoginError):
                server.janova_login('user@example.com', 'secret-password')

    def test_missing_credentials_do_not_contact_provider(self):
        from unittest.mock import patch
        with patch('server.requests.post') as post:
            for email, password in [('', 'pw'), ('user@example.com', ''), (None, 'pw')]:
                with self.assertRaises(server.JanovaLoginError):
                    server.janova_login(email, password)
            post.assert_not_called()



class JanovaPublicConfigTests(unittest.TestCase):
    def tearDown(self):
        server.janova_auth_key.cache_clear()

    def test_public_configuration_and_cache(self):
        from unittest.mock import Mock, patch
        key = 'AIza' + 'x' * 24
        response = Mock(status_code=200)
        response.text = 'new A.config("' + key + '","app","sender","janova-99680")'
        response.content = response.text.encode()
        server.janova_auth_key.cache_clear()
        with patch('server.requests.get', return_value=response) as get:
            self.assertEqual(server.janova_auth_key(), key)
            self.assertEqual(server.janova_auth_key(), key)
            get.assert_called_once_with('https://janova.app/live/main.dart.js', timeout=15, allow_redirects=False)

    def test_changed_provider_configuration_is_rejected(self):
        from unittest.mock import Mock, patch
        response = Mock(status_code=200, text='no configuration', content=b'no configuration')
        server.janova_auth_key.cache_clear()
        with patch('server.requests.get', return_value=response):
            with self.assertRaises(server.JanovaLoginError):
                server.janova_auth_key()

    def test_redirect_is_not_followed(self):
        from unittest.mock import Mock, patch
        response = Mock(status_code=302, content=b'')
        server.janova_auth_key.cache_clear()
        with patch('server.requests.get', return_value=response):
            with self.assertRaises(server.JanovaLoginError):
                server.janova_auth_key()



class ReaderProcessTests(unittest.TestCase):
    def test_reader_launch_disables_console_only_on_windows(self):
        from unittest.mock import Mock, patch
        with tempfile.TemporaryDirectory() as tmp:
            app = server.App(Path(tmp))
            app.config['janova']['refereeId'] = 'test-id'
            process = Mock()
            process.poll.return_value = None
            def launch(*args, **kwargs):
                app.stop.set()
                return process
            with patch('server.subprocess.Popen', side_effect=launch) as popen:
                app.supervise()
            self.assertEqual(popen.call_args.kwargs['creationflags'], server.subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.assertEqual(popen.call_args.kwargs['stdout'], server.subprocess.DEVNULL)
            process.terminate.assert_called_once()

if __name__ == '__main__':
    unittest.main(verbosity=2)
