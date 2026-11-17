"""Remote security and shared scoring, using real HTTP with simulated LAN peers."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

import server
from public.support.remote_access import AccessError, RemoteAccess
from public.support import network_status


class LanHandler(server.Handler):
    # Tests connect over loopback but exercise the untrusted LAN path.
    def local_client(self):
        return False


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'public').mkdir()
        for name in ('remote.html', 'remote.js', 'remote.css', 'settings.html', 'manual-controls.js', 'live-sync.js', 'remote.webmanifest'):
            shutil.copy2(server.ROOT/'public'/name, self.root/'public'/name)
        self.app = server.App(self.root)
        self.app.config['web4sport'].update(username='private-user', password='private-password')
        self.app.config['janova']['refereeId'] = 'private-janova-id'
        self.app.update({'dataSource': 'manual'})
        self.app.remote.configure({'pin': '938471', 'enabled': True})
        self.app.network.get = lambda: {'connection': 'ethernet', 'ips': ['10.0.0.2'], 'ip': '10.0.0.2', 'ssid': None, 'signalPercent': None}
        self.http = server.ThreadingHTTPServer(('127.0.0.1', 0), LanHandler)
        self.http.app = self.app
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = self.csrf = ''
        self.host = f'10.0.0.2:{self.http.server_port}'

    def tearDown(self):
        self.http.shutdown(); self.http.server_close(); self.thread.join()
        self.temp.cleanup()

    def call(self, path, body=None, origin=True, host=None, csrf=None, cookie=None):
        connection = HTTPConnection('127.0.0.1', self.http.server_port, timeout=5)
        headers = {'Host': host or self.host, 'Cookie': self.cookie if cookie is None else cookie}
        if body is not None:
            headers.update({'Content-Type': 'application/json', 'X-Scoreboard-CSRF': self.csrf if csrf is None else csrf})
            if origin: headers['Origin'] = 'http://' + (host or self.host) if origin is True else origin
        connection.request('POST' if body is not None else 'GET', path,
                           body=None if body is None else json.dumps(body), headers=headers)
        response = connection.getresponse()
        raw = response.read()
        result = (response.status, dict(response.getheaders()), raw)
        connection.close()
        return result

    def login(self):
        status, headers, raw = self.call('/api/session')
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.csrf = json.loads(raw)['csrf']
        old = self.cookie
        status, headers, _ = self.call('/api/remote/login', {'pin': '938471'})
        self.assertEqual(status, 200)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.assertNotEqual(old, self.cookie)
        self.csrf = json.loads(self.call('/api/session')[2])['csrf']

    def test_camera_tunnel_requires_login_origin_and_optional_setup(self):
        self.assertEqual(self.call('/api/cameras/1/ws')[0],401)
        self.login()
        def upgrade(origin,key='AAAAAAAAAAAAAAAAAAAAAA=='):
            connection=HTTPConnection('127.0.0.1',self.http.server_port,timeout=5)
            connection.request('GET','/api/cameras/1/ws',headers={'Host':self.host,'Cookie':self.cookie,
                'Origin':origin,'Upgrade':'websocket','Connection':'Upgrade','Sec-WebSocket-Version':'13','Sec-WebSocket-Key':key})
            response=connection.getresponse();status=response.status;response.read();connection.close();return status
        self.assertEqual(upgrade('http://evil.example'),403)
        self.assertEqual(upgrade('http://'+self.host,'invalid'),400)
        self.assertEqual(upgrade('http://'+self.host),409)
        self.app.update({'vip':{'cameras':[{'enabled':True,'url':'rtsp://192.168.1.10/stream'},{}]}})
        self.assertEqual(upgrade('http://'+self.host),503)

    def command(self, side='home', delta=1, event='test-event-001', state=None):
        return {'gameId': (state or self.app.manual_state())['gameId'], 'eventId': event, 'side': side, 'delta': delta}

    def test_authentication_reads_writes_csrf_and_origin(self):
        self.assertEqual(self.call('/api/config')[0], 401)
        self.assertEqual(self.call('/api/manual', self.command())[0], 403)
        self.assertEqual(self.call('/api/config', host='localhost')[0], 401)
        self.assertEqual(self.call('/api/config', host='attacker.example')[0], 403)
        self.assertEqual(self.call('/remote')[0], 200)
        self.assertEqual(self.call('/support/remote_access.py')[0], 404)
        self.login()
        self.assertEqual(self.call('/api/manual', self.command(), origin=False)[0], 403)
        self.assertEqual(self.call('/api/manual', self.command(), origin='http://evil.test')[0], 403)
        self.assertEqual(self.call('/api/manual', self.command(), csrf='wrong')[0], 403)
        self.assertEqual(self.call('/api/manual', self.command())[0], 200)
        self.assertEqual(self.call('/api/remote/access', {'enabled': False})[0], 403)
        self.assertEqual(self.call('/api/remote/access')[0], 403)
        self.assertEqual(self.call('/api/remote/logout', {})[0], 200)
        self.assertEqual(self.call('/api/manual')[0], 401)

    def test_score_dedup_zero_reset_persistence_and_revision(self):
        self.login()
        revision = json.loads(self.call('/api/system')[2])['revision']
        command = self.command()
        self.assertEqual(self.call('/api/manual', command)[0], 200)
        self.call('/api/manual', command)
        self.assertEqual(self.app.manual_state()['home'], 1)
        self.assertNotEqual(json.loads(self.call('/api/system')[2])['revision'], revision)
        self.call('/api/manual', self.command('away', -1, 'test-event-002'))
        self.assertEqual(self.app.manual_state()['away'], 0)
        reset = dict(gameId=command['gameId'], eventId='reset-event-001', action='reset')
        response = json.loads(self.call('/api/manual', reset)[2])
        retry = json.loads(self.call('/api/manual', reset)[2])
        self.assertEqual(response['gameId'], retry['gameId'])
        self.assertEqual(self.call('/api/manual', command)[0], 400)
        loaded = server.App(self.root)
        self.assertEqual(loaded.manual_state()['home'], 0)
        self.assertEqual(loaded.manual_state()['gameId'], response['gameId'])
        self.assertEqual(loaded.manual_action(reset)['gameId'], response['gameId'])
        self.assertNotIn('lastReset', response)

    def test_concurrent_inputs_share_one_atomic_state(self):
        state = self.app.manual_state()
        actions = [self.command(event=f'parallel-event-{i:03}', state=state) for i in range(60)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(self.app.manual_action, actions + actions))
        self.assertEqual(self.app.manual_state()['home'], 60)
        self.assertEqual(server.App(self.root).manual_state()['home'], 60)

    def test_config_validation_redaction_and_keep_secrets(self):
        self.login()
        status, _, raw = self.call('/api/config')
        self.assertEqual(status, 200)
        for value in ('private-user', 'private-password', 'private-janova-id', 'pinHash', 'pinSalt'):
            self.assertNotIn(value, raw.decode())
        patch_config = {'dataSource': 'manual', 'manual': {'opponent': 'Gast B'},
                        'display': {'mode': 'compact', 'intervalSeconds': 45},
                        'janova': {'refereeId': ''},
                        'web4sport': {'username': '', 'password': '', 'clearPassword': False}}
        self.assertEqual(self.call('/api/config', patch_config)[0], 200)
        self.assertEqual(self.app.config['web4sport']['username'], 'private-user')
        self.assertEqual(self.app.config['web4sport']['password'], 'private-password')
        self.assertEqual(self.app.config['janova']['refereeId'], 'private-janova-id')
        self.assertEqual(server.App(self.root).config['manual']['opponent'], 'Gast B')
        self.assertEqual(self.call('/api/config', {'display': {'mode': 'compact', 'intervalSeconds': 0}})[0], 400)

    def test_disabled_lan_revokes_access_and_status_is_separate(self):
        self.login()
        status = json.loads(self.call('/api/system')[2])
        self.assertEqual(status['network']['connection'], 'ethernet')
        self.assertIsNone(status['network']['ssid'])
        self.assertEqual(status['dataSource'], 'manual')
        self.assertEqual(status['sourceStatus'], 'ready')
        self.app.remote.configure({'enabled': False})
        self.assertEqual(self.call('/api/config')[0], 403)
        self.assertEqual(self.call('/api/session', host='localhost')[0], 403)

    def test_pin_rate_limit_and_session_expiry(self):
        self.call('/api/session')
        _, headers, raw = self.call('/api/session')
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.csrf = json.loads(raw)['csrf']
        for _ in range(5): self.assertEqual(self.call('/api/remote/login', {'pin': '000000'})[0], 401)
        self.assertEqual(self.call('/api/remote/login', {'pin': '938471'})[0], 429)
        clock = [0]
        remote = RemoteAccess(self.root/'private/test-access.json', server.atomic_json, clock=lambda: clock[0])
        token, _ = remote.new_session()
        self.assertIsNotNone(remote.session(token))
        clock[0] = remote.TTL
        self.assertIsNone(remote.session(token))

    def test_local_dock_and_pc_keep_existing_csrf_flow(self):
        from public.support.streamdock import Client
        with patch.object(LanHandler, 'local_client', return_value=True):
            client = Client(f'http://127.0.0.1:{self.http.server_port}')
            state = client.request('/api/manual')
            result = client.press(state, 'home', 1)
            self.assertEqual(result['home'], 1)
            session = json.loads(self.call('/api/session')[2])
            self.assertEqual(session['csrf'], self.app.csrf)
            self.assertTrue(session['local'])
            self.assertEqual(self.call('/api/manual', self.command('away', 1, 'pc-event-0001'), csrf=self.app.csrf)[0], 200)
            self.assertEqual(self.app.manual_state()['away'], 1)

    def test_pairing_qr_current_addresses_only_and_no_secrets(self):
        self.assertEqual(self.call('/api/remote/pairing')[0],401)
        self.assertEqual(self.call('/api/remote/qr.svg?ip=10.0.0.2')[0],401)
        self.login()
        # Fixture listener is loopback only; pretend an explicitly enabled LAN bind.
        with patch.object(self.http,'server_address',('0.0.0.0', self.http.server_port)):
            info=json.loads(self.call('/api/remote/pairing')[2])
            self.assertEqual(info['urls'],[f'http://10.0.0.2:{self.http.server_port}/remote'])
            self.assertEqual(info['qrImages'],['/api/remote/qr.svg?ip=10.0.0.2'])
            status,headers,raw=self.call(info['qrImages'][0])
            self.assertEqual(status,200)
            self.assertEqual(headers['Content-Type'],'image/svg+xml')
            self.assertIn(info['urls'][0].encode(),raw)
            for secret in (b'938471',b'pinHash',b'pinSalt',b'private-user',b'private-password'):
                self.assertNotIn(secret,raw)
            self.assertEqual(self.call('/api/remote/qr.svg?ip=https://evil.test')[0],409)
            self.app.network.get=lambda:{'connection':'ethernet','ips':['10.0.0.3'],'ip':'10.0.0.3','ssid':None,'signalPercent':None}
            self.assertEqual(self.call('/api/remote/qr.svg?ip=10.0.0.2',host='localhost')[0],409)
            updated=json.loads(self.call('/api/remote/pairing',host='localhost')[2])
            self.assertIn('10.0.0.3',updated['urls'][0])
            self.app.remote.configure({'enabled':False})
            with patch.object(LanHandler,'local_client',return_value=True):
                self.assertEqual(json.loads(self.call('/api/remote/pairing',host='localhost')[2])['urls'],[])

    def test_own_hostname_and_web_manifest(self):
        with patch.object(server,'local_hostname',return_value='tt-test.local'):
            self.assertEqual(self.call('/api/session',host='tt-test.local')[0],200)
            self.assertEqual(self.call('/api/session',host='another-device.local')[0],403)
        status,headers,raw=self.call('/remote.webmanifest')
        self.assertEqual(status,200)
        self.assertEqual(headers['Content-Type'],'application/manifest+json')
        manifest=json.loads(raw)
        self.assertEqual(manifest['start_url'],'/remote')
        self.assertEqual(manifest['display'],'standalone')
        self.assertEqual({icon['sizes'] for icon in manifest['icons']},{'192x192','512x512'})


class NetworkAndBindingTests(unittest.TestCase):
    def test_default_loopback_and_no_lan_without_pin(self):
        with tempfile.TemporaryDirectory() as folder:
            app = server.App(Path(folder))
            self.assertEqual(app.remote.bind_address(), '127.0.0.1')
            http = server.create_server(app, 0)
            self.assertEqual(http.server_address[0], '127.0.0.1')
            http.server_close()
            with self.assertRaises(ValueError): server.create_server(app, 0, '0.0.0.0')
            with self.assertRaises(AccessError): app.remote.configure({'enabled': True})
            with self.assertRaises(AccessError): app.remote.configure({'pin': '123'})
            for address in ('127.0.0.2', '169.254.1.1', '224.0.0.1', 'example.org', '::'):
                with self.assertRaises(AccessError): app.remote.configure({'bindAddress': address})
            app.remote.configure({'pin': '928471', 'enabled': True})
            self.assertEqual(app.remote.bind_address(), '0.0.0.0')
            raw = (app.private/'remote-access.json').read_text()
            self.assertNotIn('928471', raw)
            self.assertIn('pinHash', raw)
            self.assertTrue(server.App(Path(folder)).remote.public()['pinSet'])

    def test_network_offline_unknown_and_windows_adapter(self):
        with patch.object(network_status, 'run', side_effect=['[]', '[]']):
            self.assertEqual(network_status.linux_status()['connection'], 'offline')
        with patch.object(network_status.platform, 'system', return_value='Other'):
            provider = network_status.NetworkStatus(); provider.refresh()
            self.assertEqual(provider.get()['connection'], 'unsupported')
        with patch.object(network_status.platform, 'system', return_value='Linux'), patch.object(network_status, 'run', side_effect=OSError()):
            provider = network_status.NetworkStatus(); provider.refresh()
            self.assertEqual(provider.get()['connection'], 'unknown')
        with patch.object(network_status, 'run', return_value='[{"ip":"10.0.0.2","wireless":false,"gateway":true}]'):
            self.assertEqual(network_status.windows_status()['connection'], 'ethernet')


if __name__ == '__main__':
    unittest.main()
