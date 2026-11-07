#!/usr/bin/env python3
"""Independent scoreboard 2.0: local configuration API and read-only readers."""
import argparse
from functools import lru_cache
import copy
from datetime import date, datetime
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

import requests
import updater
from bs4 import BeautifulSoup
import web4sport_client as web

ROOT = Path(__file__).resolve().parent
DEFAULTS = {
    'version': '2.0', 'dataSource': 'janova',
    'display': {'mode': 'rotate', 'intervalSeconds': 30, 'footerHeightPercent': 8.5},
    'background': {'mode': 'css', 'overlayPercent': 58},
    'sponsors': {'enabled': False, 'intervalSeconds': 10, 'introText': 'unterstützt von:', 'items': []},
    'club': {'name': 'Mein Tischtennisverein', 'website': '',
             'primary': '#f10d1d', 'background': '#080b10'},
    'janova': {'refereeId': ''},
    'web4sport': {'username': '', 'password': '', 'selection': None},
}


class JanovaLoginError(Exception):
    pass


@lru_cache(maxsize=1)
def janova_auth_key():
    # Read Janova's public browser configuration; never store a user credential.
    response = requests.get('https://janova.app/live/main.dart.js', timeout=15, allow_redirects=False)
    if response.status_code != 200 or len(response.content) > 8 * 1024 * 1024:
        raise JanovaLoginError('Janova-Anmeldung derzeit nicht verfügbar. Bitte die Live-Link-ID verwenden.')
    match = re.search(r'"(AIza[A-Za-z0-9_-]{20,})"[^\n]{0,300}"janova-99680"', response.text)
    if not match:
        raise JanovaLoginError('Janova-Anmeldung derzeit nicht verfügbar. Bitte die Live-Link-ID verwenden.')
    return match.group(1)


def janova_login(email, password):
    if not isinstance(email, str) or not isinstance(password, str) or not email.strip() or not password or len(email) > 320 or len(password) > 4096:
        raise JanovaLoginError('Bitte Janova-E-Mail und Passwort eingeben.')
    try:
        response = requests.post(
            'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword',
            params={'key': janova_auth_key()},
            json={'email': email.strip(), 'password': password, 'returnSecureToken': True},
            timeout=20, allow_redirects=False)
        if response.status_code != 200:
            code = response.json().get('error', {}).get('message', '')
            if code.startswith('TOO_MANY_ATTEMPTS'):
                raise JanovaLoginError('Zu viele Anmeldeversuche. Bitte später erneut versuchen.')
            raise JanovaLoginError('Janova-Anmeldung fehlgeschlagen. Zugangsdaten prüfen; gegebenenfalls direkt bei Janova anmelden.')
        identity = response.json().get('localId', '')
        if not identity or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', identity):
            raise JanovaLoginError('Janova hat keine gültige Konto-ID geliefert.')
        return identity
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        raise JanovaLoginError('Janova ist gerade nicht erreichbar oder hat eine unerwartete Antwort geliefert.') from None


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as output:
        os.chmod(temporary, 0o600)
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def parse_games(html):
    """Only started reports from the authenticated overview; no navigation writes."""
    soup = BeautifulSoup(html, 'html.parser')
    if soup.find('input', {'name': 'password'}):
        raise RuntimeError('Sitzung abgelaufen')
    heading = next((h for h in soup.find_all('h2')
                    if 'Laufende Live-Spielberichte' in h.get_text(' ', strip=True)), None)
    if heading is None:
        raise RuntimeError('Spielübersicht nicht erkannt')
    table = heading.find_next('table')
    if table is None:
        raise RuntimeError('Spielübersicht nicht erkannt')
    games = {}
    for row in table.find_all('tr'):
        if not row.find('img', title=lambda value: bool(value) and 'Spiel gestartet' in value):
            continue
        links = [row.get('onclick', '')] + [a.get('href', '') for a in row.find_all('a')]
        match = next((re.search(r'[?&]Area=Report&SAID=(\d+)&SID=(\d+)', link, re.I)
                      for link in links if re.search(r'[?&]Area=Report&SAID=(\d+)&SID=(\d+)', link, re.I)), None)
        if match is None:
            continue
        said, sid = match.groups()
        label = ' '.join(row.stripped_strings)
        dates = re.search(r'\b(\d{2}\.\d{2}\.(?:\d{4}|\d{2}))\b', label)
        game_date = ''
        if dates:
            value = dates.group(1)
            try:
                game_date = datetime.strptime(value, '%d.%m.%Y' if len(value) == 10 else '%d.%m.%y').date().isoformat()
            except ValueError:
                pass
        games[(said, sid)] = {'said': said, 'sid': sid, 'date': game_date,
                              'label': label[:240] or f'Spiel {sid}'}
    return list(games.values())


def candidate_pool(games, today=None):
    today = today or date.today().isoformat()
    todays = [game for game in games if game['date'] == today]
    return todays or games


def choose_game(games, selection, today=None):
    today = today or date.today().isoformat()
    pool = candidate_pool(games, today)
    if selection and selection.get('selectedOn') == today:
        manual = next((game for game in pool if (game['said'], game['sid']) ==
                       (selection.get('said'), selection.get('sid'))), None)
        if manual:
            return manual, 'ready'
    if len(pool) == 1:
        return pool[0], 'ready'
    return None, 'selection_required' if pool else 'waiting'


def reader_key(config):
    return (config['dataSource'], config['janova']['refereeId'],
            config['web4sport']['username'], config['web4sport']['password'],
            json.dumps(config['web4sport']['selection'], sort_keys=True))


def janova_identity(value):
    """Accept an ID or the user's official Janova live URL, without fetching it."""
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Janova-ID oder Live-Link ungültig')
    value = value.strip()
    if '://' in value:
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or parsed.hostname != 'janova.app' or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.path.rstrip('/') != '/live/stream':
            raise ValueError('Bitte einen Janova-Live-Link verwenden')
        identities = parse_qs(parsed.query).get('id', [])
        if len(identities) != 1:
            raise ValueError('Der Live-Link enthält keine eindeutige Janova-ID')
        value = identities[0]
    if not re.fullmatch(r'[A-Za-z0-9_-]{0,128}', value):
        raise ValueError('Janova-ID ungültig')
    return value


def validate_update(previous, patch):
    if not isinstance(patch, dict) or set(patch) - {'club', 'dataSource', 'janova', 'web4sport', 'display', 'sponsors', 'background'}:
        raise ValueError('Ungültige Konfiguration')
    result = copy.deepcopy(previous)
    if 'background' in patch:
        value = patch['background']
        if not isinstance(value, dict) or set(value) != {'mode', 'overlayPercent'}:
            raise ValueError('Hintergrund ungültig')
        if value['mode'] not in ('css', 'original', 'classic', 'custom') or type(value['overlayPercent']) is not int or not 0 <= value['overlayPercent'] <= 100:
            raise ValueError('Hintergrund ungültig')
        result['background'] = copy.deepcopy(value)
    if 'sponsors' in patch:
        value = patch['sponsors']
        if not isinstance(value, dict) or not {'enabled', 'intervalSeconds'}.issubset(value) or set(value) - {'enabled', 'intervalSeconds', 'introText'}:
            raise ValueError('Sponsoren-Einstellungen ungültig')
        seconds = value['intervalSeconds']
        if type(value['enabled']) is not bool or type(seconds) is not int or not 1 <= seconds <= 3600:
            raise ValueError('Sponsoren-Einstellungen ungültig')
        if 'introText' in value and (not isinstance(value['introText'], str) or len(value['introText']) > 100):
            raise ValueError('Sponsoren-Einleitung ungültig')
        if 'introText' in value:
            value = {**value, 'introText': value['introText'].strip()}
        result['sponsors'].update(value)
    if 'display' in patch:
        display = patch['display']
        if not isinstance(display, dict) or not {'mode', 'intervalSeconds'}.issubset(display) or set(display) - {'mode', 'intervalSeconds', 'footerHeightPercent'}:
            raise ValueError('Ansicht ungültig')
        if display['mode'] not in ('compact', 'detail', 'rotate'):
            raise ValueError('Ansicht ungültig')
        seconds = display['intervalSeconds']
        if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 3600:
            raise ValueError('Intervall muss zwischen 1 und 3600 Sekunden liegen')
        height = display.get('footerHeightPercent', previous['display'].get('footerHeightPercent', 8.5))
        if isinstance(height, bool) or not isinstance(height, (int, float)) or not 5 <= height <= 15:
            raise ValueError('Fußleistenhöhe muss zwischen 5 und 15 Prozent liegen')
        result['display'] = {**copy.deepcopy(display), 'footerHeightPercent': height}
    if 'dataSource' in patch:
        if patch['dataSource'] not in ('janova', 'web4sport'):
            raise ValueError('Datenquelle ungültig')
        result['dataSource'] = patch['dataSource']
    if 'club' in patch:
        club = patch['club']
        if not isinstance(club, dict) or set(club) - {'name', 'website', 'primary', 'background'}:
            raise ValueError('Vereinsdaten ungültig')
        for key, value in club.items():
            if not isinstance(value, str) or len(value) > (160 if key == 'website' else 80):
                raise ValueError('Vereinsdaten ungültig')
            if key in ('primary', 'background') and not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                raise ValueError('Farbe ungültig')
            result['club'][key] = value.strip()
    if 'janova' in patch:
        value = patch['janova']
        if not isinstance(value, dict) or set(value) != {'refereeId'}:
            raise ValueError('Janova-ID ungültig')
        result['janova']['refereeId'] = janova_identity(value['refereeId'])
    if 'web4sport' in patch:
        values = patch['web4sport']
        if not isinstance(values, dict) or set(values) - {'username', 'password', 'clearPassword'}:
            raise ValueError('Web4Sport-Eingaben ungültig')
        for key in ('username', 'password'):
            if key in values and (not isinstance(values[key], str) or len(values[key]) > 256):
                raise ValueError('Web4Sport-Eingaben ungültig')
        if values.get('clearPassword') not in (None, False, True):
            raise ValueError('Web4Sport-Eingaben ungültig')
        username = values.get('username', result['web4sport']['username']).strip()
        if username != result['web4sport']['username']:
            result['web4sport']['password'] = ''
        result['web4sport']['username'] = username
        if values.get('clearPassword'):
            result['web4sport']['password'] = ''
        elif values.get('password'):
            result['web4sport']['password'] = values['password']
        if (result['web4sport']['username'], result['web4sport']['password']) != (
                previous['web4sport']['username'], previous['web4sport']['password']):
            result['web4sport']['selection'] = None
    return result


class App:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.private = self.root/'private'
        self.data = self.private/'data'
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.private.chmod(0o700)
        self.path = self.private/'config.json'
        self.config = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else copy.deepcopy(DEFAULTS)
        migrated = 'display' not in self.config or 'background' not in self.config or 'sponsors' not in self.config or 'introText' not in self.config.get('sponsors', {})
        self.config.setdefault('background', copy.deepcopy(DEFAULTS['background']))
        self.config.setdefault('display', copy.deepcopy(DEFAULTS['display']))
        self.config['display'].setdefault('footerHeightPercent', 8.5)
        self.config.setdefault('sponsors', copy.deepcopy(DEFAULTS['sponsors']))
        self.config['sponsors'].setdefault('introText', DEFAULTS['sponsors']['introText'])
        if not self.path.exists() or migrated:
            atomic_json(self.path, self.config)
        self.path.chmod(0o600)
        self.lock = threading.RLock()
        self.csrf = secrets.token_urlsafe(32)
        self.update_lock = threading.Lock()
        self.stop = threading.Event()
        self.restart_requested = threading.Event()
        self.process = None
        self.running_key = None
        self.epoch = time.time()
        self.payload = None
        self.candidates = []
        self.status = 'starting'
        self.message = 'Reader wird gestartet'

    def public_config(self):
        with self.lock:
            config = copy.deepcopy(self.config)
            config['version'] = updater.version(self.root)
            config['lastUpdate'] = updater.last_result(self.root)
            configured = bool(config['web4sport'].pop('password'))
            config['web4sport']['passwordSet'] = configured
            logo = self.private/'club-logo'
            config['club']['logo'] = '/api/logo?v=' + str(logo.stat().st_mtime_ns) if logo.exists() else 'assets/default-logo.svg'
            custom = self.private/'custom-background'
            config['background']['customSet'] = custom.exists()
            config['background']['customImage'] = '/api/background?v=' + str(custom.stat().st_mtime_ns) if custom.exists() else ''
            mode = config['background']['mode']
            config['background']['image'] = 'assets/v1-background.jpg' if mode == 'classic' else 'assets/default-background.svg' if mode == 'original' else config['background']['customImage'] if mode == 'custom' else ''
            return config

    def update(self, patch):
        with self.lock:
            updated = validate_update(self.config, patch)
            if updated['background']['mode'] == 'custom' and not (self.private/'custom-background').exists():
                raise ValueError('Bitte zuerst ein eigenes Hintergrundbild auswählen')
            self._save(updated)
            return self.public_config()

    def _save(self, updated):
        atomic_json(self.path, updated)
        if reader_key(updated) != reader_key(self.config):
            self.epoch = time.time()
            self.payload = None
            self.candidates = []
            self.status, self.message = 'starting', 'Neue Datenquelle wird gestartet'
        self.config = updated

    def select(self, said, sid):
        with self.lock:
            game = next((game for game in self.candidates if game['said'] == said and game['sid'] == sid), None)
            if game is None:
                raise ValueError('Das Spiel ist nicht mehr in der aktuellen Auswahl. Bitte neu laden.')
            updated = copy.deepcopy(self.config)
            updated['web4sport']['selection'] = {**game, 'selectedOn': date.today().isoformat()}
            self._save(updated)

    def clear_selection(self):
        with self.lock:
            updated = copy.deepcopy(self.config)
            updated['web4sport']['selection'] = None
            self._save(updated)

    def add_sponsor(self, image, name):
        if image_type(image) is None:
            raise ValueError('Bitte PNG, JPEG, GIF oder WebP verwenden')
        with self.lock:
            if len(self.config['sponsors']['items']) >= 20:
                raise ValueError('Maximal 20 Sponsorenlogos')
            identity = secrets.token_hex(16)
            folder = self.private/'sponsors'
            folder.mkdir(mode=0o700, exist_ok=True)
            path = folder/identity
            path.write_bytes(image)
            path.chmod(0o600)
            updated = copy.deepcopy(self.config)
            updated['sponsors']['items'].append({'id': identity, 'name': str(name)[:100] or 'Sponsor',
                                                'logo': '/api/sponsors/logo/' + identity})
            try:
                self._save(updated)
            except BaseException:
                path.unlink()
                raise
            return self.public_config()

    def remove_sponsor(self, identity):
        with self.lock:
            items = self.config['sponsors']['items']
            if not any(item['id'] == identity for item in items):
                raise ValueError('Sponsor nicht gefunden')
            updated = copy.deepcopy(self.config)
            updated['sponsors']['items'] = [item for item in items if item['id'] != identity]
            self._save(updated)
            # Preserve removed images privately for rollback, but stop serving them.
            path = self.private/'sponsors'/identity
            if path.exists():
                archive = self.private/'sponsor-archive'
                archive.mkdir(mode=0o700, exist_ok=True)
                path.rename(archive/identity)
            return self.public_config()

    def publish(self, key, status, message, candidates=None, payload=None):
        with self.lock:
            if key != reader_key(self.config):
                return
            self.status, self.message = status, message
            if candidates is not None:
                self.candidates = candidates
            self.payload = payload

    def get_data(self, source):
        with self.lock:
            status, message = self.status, self.message
            if source != self.config['dataSource']:
                return {'status': 'inactive', 'message': 'Datenquelle wird umgeschaltet', 'matches': [], 'scoreboards': []}
            if source == 'janova' and self.running_key == reader_key(self.config) and self.process and self.process.poll() is None:
                path = self.data/'scoreboards.json'
                if path.exists() and path.stat().st_mtime >= self.epoch:
                    try:
                        payload = json.loads(path.read_text(encoding='utf-8'))
                        age = time.time() - path.stat().st_mtime
                        if age <= 90:
                            return {**payload, 'status': 'ready', 'message': 'Janova verbunden'}
                        status, message = 'error', 'Keine aktuellen Janova-Daten. Referee-ID und Verbindung prüfen.'
                    except (OSError, ValueError):
                        pass
            if self.payload is not None and source == 'web4sport':
                return copy.deepcopy({**self.payload, 'status': status, 'message': message, 'candidates': self.candidates})
            return {'status': status, 'message': message, 'candidates': copy.deepcopy(self.candidates),
                    'matches': [], 'scoreboards': []}

    def stop_janova(self):
        process, self.process = self.process, None
        self.running_key = None
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def supervise(self):
        last_key = None
        session = None
        next_poll = 0
        current = None
        game_day = date.today()
        try:
            while not self.stop.is_set():
                with self.lock:
                    config = copy.deepcopy(self.config)
                key = reader_key(config)
                if self.restart_requested.is_set():
                    self.restart_requested.clear()
                    last_key = None
                if key != last_key:
                    self.stop_janova()
                    if session:
                        session.close()
                    session, current, next_poll = None, None, 0
                    last_key = key
                    if config['dataSource'] == 'janova':
                        identity = config['janova']['refereeId']
                        if identity:
                            env = {**os.environ, 'JANOVA_REFEREE_ID': identity}
                            for path in self.data.glob('scoreboard*.json'):
                                path.unlink()
                            self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-u', str(self.root/'janova_reader.py')],
                                                            cwd=self.data, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                            self.running_key = key
                            self.publish(key, 'starting', 'Janova-Daten werden geladen')
                        else:
                            self.publish(key, 'configuration_required', 'Bitte eine Janova-Referee-ID in den Einstellungen hinterlegen.')
                if config['dataSource'] == 'janova':
                    if self.process and self.process.poll() is not None:
                        self.publish(key, 'error', 'Janova-Reader beendet. Konfiguration prüfen oder Reader neu verbinden.')
                    self.stop.wait(1)
                    continue
                if time.monotonic() < next_poll:
                    self.stop.wait(1)
                    continue
                next_poll = time.monotonic() + 15
                credentials = config['web4sport']
                if not credentials['username'] or not credentials['password']:
                    self.publish(key, 'configuration_required', 'Bitte Web4Sport-Benutzername und Passwort hinterlegen.')
                    continue
                try:
                    if session is None:
                        session = requests.Session()
                        session.headers['User-Agent'] = 'TTSV-Scoreboard/2.0'
                        # The overview login has no dependency on a historical game ID.
                        web.login(session, credentials['username'], credentials['password'], '96', '')
                    response = session.get(web.BASE + '?Area=Report', timeout=20)
                    response.raise_for_status()
                    games = parse_games(response.text)
                    pool = candidate_pool(games)
                    selected, status = choose_game(games, credentials['selection'])
                    if date.today() != game_day:
                        current, game_day = None, date.today()
                    if status == 'selection_required':
                        current = None
                        self.publish(key, status, 'Mehrere gestartete Spiele gefunden. Bitte eine Begegnung auswählen.', pool)
                        continue
                    if selected is None:
                        selected = current
                    if selected is None:
                        self.publish(key, 'waiting', 'Noch kein gestartetes Spiel über die gewählte Datenquelle (TischtennisLive/Web4Sport) gefunden.', pool)
                        continue
                    matches, teams = web.read(session, selected['said'], selected['sid'])
                    score = {side: sum(m['finished'] and m['sets_won'][side] > m['sets_won']['away' if side == 'home' else 'home'] for m in matches)
                             for side in ('home', 'away')}
                    payload = {'source': 'web4sport', 'sid': selected['sid'], 'said': selected['said'],
                               'updated': datetime.now().astimezone().isoformat(), 'teams': teams,
                               'team_score': score, 'matches': matches}
                    with self.lock:
                        if key == reader_key(self.config):
                            atomic_json(self.data/'web4sport.json', payload)
                    self.publish(key, 'ready', 'Web4Sport verbunden', pool, payload)
                    current = selected
                except Exception as exc:
                    if session:
                        session.close()
                    session = None
                    known = str(exc) if isinstance(exc, RuntimeError) else ''
                    message = known if known in ('Login fehlgeschlagen', 'Sitzung abgelaufen', 'Spielübersicht nicht erkannt') else 'Web4Sport nicht erreichbar oder Spielbericht noch nicht lesbar.'
                    self.publish(key, 'error', message)
        finally:
            self.stop_janova()
            if session:
                session.close()


class Handler(BaseHTTPRequestHandler):
    server_version = 'Scoreboard/2.0'

    def log_message(self, *_):
        pass  # Request paths, usernames and payloads never enter logs.

    @property
    def app(self):
        return self.server.app

    def send(self, status, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        # Only our own settings document may be embedded by this application's overlay.
        embedded_settings = urlsplit(self.path).path == '/settings.html'
        self.send_header('X-Frame-Options', 'SAMEORIGIN' if embedded_settings else 'DENY')
        if embedded_settings:
            self.send_header('Content-Security-Policy', "frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        try:
            return urlsplit('http://' + self.headers.get('Host', '')).hostname in ('localhost', '127.0.0.1', '::1')
        except ValueError:
            return False

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {'error': 'Nur über lokale Adresse oder SSH-Tunnel erreichbar.'})
        path = unquote(urlsplit(self.path).path)
        if path == '/api/session':
            return self.send(200, {'csrf': self.app.csrf})
        if path == '/api/config':
            return self.send(200, self.app.public_config())
        if path == '/api/state':
            return self.send(200, self.app.get_data(self.app.config['dataSource']))
        if path in ('/api/data/janova', '/api/data/web4sport'):
            return self.send(200, self.app.get_data(path.rsplit('/', 1)[1]))
        if path == '/api/logo':
            logo = self.app.private/'club-logo'
            if not logo.exists():
                return self.send(404, {'error': 'Kein Logo hinterlegt'})
            data = logo.read_bytes()
            return self.send(200, data, image_type(data) or 'application/octet-stream')
        if path == '/api/background':
            background = self.app.private/'custom-background'
            if not background.exists():
                return self.send(404, {'error': 'Kein eigenes Hintergrundbild hinterlegt'})
            data = background.read_bytes()
            return self.send(200, data, image_type(data) or 'application/octet-stream')
        if path.startswith('/api/sponsors/logo/'):
            identity = path.rsplit('/', 1)[1]
            with self.app.lock:
                known = any(item['id'] == identity for item in self.app.config['sponsors']['items'])
                logo = self.app.private/'sponsors'/identity
                if not re.fullmatch(r'[0-9a-f]{32}', identity) or not known or not logo.is_file():
                    return self.send(404, {'error': 'Logo nicht gefunden'})
                data = logo.read_bytes()
            return self.send(200, data, image_type(data) or 'application/octet-stream')
        if path == '/competition.json':
            return self.send(200, {'competition': ''})
        relative = path.lstrip('/') or 'spiele.html'
        public = (self.app.root/'public').resolve()
        target = (public/relative).resolve()
        if not target.is_relative_to(public) or not target.is_file() or (target.suffix.lower() not in ('.html', '.js', '.css', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg') and relative != 'assets/club-logos/catalog.json'):
            return self.send(404, {'error': 'Nicht gefunden'})
        return self.send(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')

    def do_POST(self):
        if not self.valid_host() or self.headers.get('Origin') not in (None, 'http://' + self.headers.get('Host', '')):
            return self.send(403, {'error': 'Fremde Herkunft abgelehnt'})
        if not secrets.compare_digest(self.headers.get('X-Scoreboard-CSRF', ''), self.app.csrf):
            return self.send(403, {'error': 'Bitte Seite neu laden'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 10 * 1024 * 1024:
                return self.send(413, {'error': 'Datei zu groß (maximal 10 MB)'})
            raw = self.rfile.read(size)
            path = urlsplit(self.path).path
            if path == '/api/background':
                if image_type(raw) is None:
                    raise ValueError('Bitte PNG, JPEG, GIF oder WebP hochladen')
                temporary = self.app.private/'custom-background.tmp'
                with self.app.lock:
                    temporary.write_bytes(raw)
                    temporary.chmod(0o600)
                    os.replace(temporary, self.app.private/'custom-background')
                return self.send(200, self.app.public_config())
            if path == '/api/sponsors/upload':
                name = unquote(self.headers.get('X-Logo-Name', 'Sponsor'))
                return self.send(200, self.app.add_sponsor(raw, name))
            if path == '/api/logo':
                if image_type(raw) is None:
                    raise ValueError('Bitte PNG, JPEG, GIF oder WebP hochladen')
                temporary = self.app.private/'club-logo.tmp'
                with self.app.lock:
                    temporary.write_bytes(raw)
                    temporary.chmod(0o600)
                    os.replace(temporary, self.app.private/'club-logo')
                return self.send(200, self.app.public_config())
            patch = json.loads(raw)
            if path == '/api/sponsors/remove':
                return self.send(200, self.app.remove_sponsor(str(patch.get('id', ''))))
            if path == '/api/janova/login':
                try:
                    identity = janova_login(patch.get('email'), patch.get('password'))
                except JanovaLoginError as error:
                    return self.send(400, {'error': str(error)})
                return self.send(200, {'refereeId': identity})
            if path == '/api/update/check':
                try:
                    release = updater.latest(self.app.root)
                    release.pop('payload', None)
                    release.pop('checksums', None)
                    return self.send(200, release)
                except (requests.RequestException, ValueError, KeyError, OSError):
                    return self.send(502, {'error': 'Updateprüfung fehlgeschlagen. Bitte Internetverbindung prüfen und später erneut versuchen.'})
            if path == '/api/update/install':
                try:
                    return self.send(200, updater.begin(self.app, self.server.server_port, patch.get('version')))
                except (ValueError, OSError, requests.RequestException, subprocess.SubprocessError) as error:
                    return self.send(400, {'error': str(error)[:300]})
            if path == '/api/config':
                return self.send(200, self.app.update(patch))
            if path == '/api/game':
                if patch.get('automatic') is True:
                    self.app.clear_selection()
                else:
                    self.app.select(str(patch.get('said', '')), str(patch.get('sid', '')))
                return self.send(200, {'ok': True})
            if path == '/api/reconnect':
                with self.app.lock:
                    self.app.epoch = time.time()
                    self.app.payload = None
                    self.app.status, self.app.message = 'starting', 'Reader verbindet neu'
                self.app.restart_requested.set()
                return self.send(200, {'ok': True})
            return self.send(404, {'error': 'Nicht gefunden'})
        except (ValueError, TypeError, KeyError, AttributeError):
            return self.send(400, {'error': 'Eingaben ungültig oder Spiel nicht mehr verfügbar. Bitte prüfen und neu laden.'})


def image_type(data):
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if len(data) >= 12 and data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8081)
    args = parser.parse_args()
    app = App()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.app = app
    worker = threading.Thread(target=app.supervise, daemon=True)
    worker.start()
    print(f'Scoreboard 2.0: http://127.0.0.1:{args.port}/spiele.html', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop.set()
        app.stop_janova()
        server.server_close()


if __name__ == '__main__':
    main()
