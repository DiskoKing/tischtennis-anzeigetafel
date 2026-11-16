"""Optional LAN policy. No listener, credentials or sessions in public responses."""
from collections import OrderedDict
import hashlib
import ipaddress
import json
import re
import secrets
import threading
import time


class AccessError(ValueError):
    pass


def valid_bind(value):
    try:
        address = ipaddress.IPv4Address(value)
    except (ValueError, TypeError):
        raise AccessError('Bitte eine IPv4-Bind-Adresse angeben.') from None
    if (address.is_multicast or address.is_reserved or address.is_link_local or
            (address.is_loopback and str(address) != '127.0.0.1') or str(address) == '255.255.255.255'):
        raise AccessError('Bind-Adresse ungültig.')
    return str(address)


class RemoteAccess:
    COOKIE = 'tt_remote_v1'
    TTL = 8 * 60 * 60
    ITERATIONS = 600_000

    def __init__(self, path, save, clock=time.monotonic):
        self.path, self.save, self.clock = path, save, clock
        self.lock = threading.RLock()
        self.config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
            'enabled': False, 'bindAddress': '0.0.0.0'}
        self.sessions = OrderedDict()
        self.attempts = OrderedDict()
        self.global_attempts = []

    def public(self):
        with self.lock:
            return {key: self.config[key] for key in ('enabled', 'bindAddress')} | {
                'pinSet': bool(self.config.get('pinHash'))}

    def configure(self, patch):
        if not isinstance(patch, dict) or set(patch) - {'enabled', 'bindAddress', 'pin'}:
            raise AccessError('Ungültige Remote-Einstellungen.')
        with self.lock:
            updated = dict(self.config)
            if 'pin' in patch:
                pin = patch['pin']
                if not isinstance(pin, str) or not re.fullmatch(r'[0-9]{6,12}', pin):
                    raise AccessError('Admin-PIN: 6 bis 12 Ziffern erforderlich.')
                salt = secrets.token_bytes(16)
                updated.update(pinSalt=salt.hex(), pinIterations=self.ITERATIONS,
                               pinHash=hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, self.ITERATIONS).hex())
            if 'bindAddress' in patch:
                updated['bindAddress'] = valid_bind(patch['bindAddress'])
            if 'enabled' in patch:
                if type(patch['enabled']) is not bool:
                    raise AccessError('LAN-Freigabe ungültig.')
                updated['enabled'] = patch['enabled']
            if updated['enabled'] and not updated.get('pinHash'):
                raise AccessError('Vor der LAN-Freigabe zuerst eine Admin-PIN einrichten.')
            self.save(self.path, updated)
            self.config = updated
            # Changing PIN or policy revokes every existing remote session.
            self.sessions.clear()
            return self.public()

    def bind_address(self):
        with self.lock:
            if not self.config.get('enabled') or not self.config.get('pinHash'):
                return '127.0.0.1'
            return valid_bind(self.config['bindAddress'])

    def session(self, cookie):
        if not isinstance(cookie, str) or len(cookie) > 200:
            return None
        key = hashlib.sha256(cookie.encode()).hexdigest()
        with self.lock:
            session = self.sessions.get(key)
            if not session or self.clock() >= session['expires']:
                self.sessions.pop(key, None)
                return None
            return dict(session)

    def new_session(self):
        token = secrets.token_urlsafe(32)
        key = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            now = self.clock()
            self.sessions = OrderedDict((k, v) for k, v in self.sessions.items() if v['expires'] > now)
            while len(self.sessions) >= 64:
                self.sessions.popitem(last=False)
            session = {'csrf': secrets.token_urlsafe(32), 'authenticated': False, 'expires': now + self.TTL}
            self.sessions[key] = session
        return token, dict(session)

    def login(self, token, pin, peer):
        with self.lock:
            now = self.clock()
            attempts = [t for t in self.attempts.pop(peer, []) if now - t < 60]
            self.global_attempts = [t for t in self.global_attempts if now - t < 60]
            if len(attempts) >= 5 or len(self.global_attempts) >= 30:
                self.attempts[peer] = attempts
                raise AccessError('Zu viele PIN-Versuche. Bitte eine Minute warten.')
            attempts.append(now)
            self.attempts[peer] = attempts
            self.global_attempts.append(now)
            while len(self.attempts) > 256:
                self.attempts.popitem(last=False)
            if not self.config['enabled'] or not self.session(token):
                raise AccessError('Remote-Zugriff ist nicht freigegeben.')
            pin = pin if isinstance(pin, str) and re.fullmatch(r'[0-9]{6,12}', pin) else ''
            digest = hashlib.pbkdf2_hmac('sha256', pin.encode(), bytes.fromhex(self.config['pinSalt']),
                                         self.config['pinIterations']).hex()
            if not secrets.compare_digest(digest, self.config['pinHash']):
                raise AccessError('PIN ungültig.')
            self.logout(token)
            replacement, session = self.new_session()
            self.sessions[hashlib.sha256(replacement.encode()).hexdigest()]['authenticated'] = True
            return replacement

    def logout(self, token):
        with self.lock:
            self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)
