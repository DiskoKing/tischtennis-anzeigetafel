"""Authenticated, bounded WebSocket tunnel to two fixed local go2rtc streams.

No RTSP credentials or go2rtc administration endpoints reach the browser.
The optional gateway listens only on loopback and is not needed for normal views.
"""
import base64
import hashlib
import select
import socket
import threading
import time

SLOTS = threading.BoundedSemaphore(8)
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def serve(handler, index):
    if index not in (1, 2):
        return handler.send(404, {'error': 'Kamera nicht vorhanden'})
    if handler.headers.get('Origin') != 'http://' + handler.headers.get('Host', ''):
        return handler.send(403, {'error': 'Kamerazugriff nur aus dieser Anzeigetafel'})
    if (handler.headers.get('Upgrade', '').lower() != 'websocket' or
            'upgrade' not in [v.strip().lower() for v in handler.headers.get('Connection', '').split(',')] or
            handler.headers.get('Sec-WebSocket-Version') != '13'):
        return handler.send(400, {'error': 'WebSocket-Verbindung erforderlich'})
    key = handler.headers.get('Sec-WebSocket-Key', '')
    try:
        if len(base64.b64decode(key, validate=True)) != 16:
            raise ValueError()
    except (ValueError, TypeError):
        return handler.send(400, {'error': 'WebSocket-Schlüssel ungültig'})
    if not handler.app.config['vip']['cameras'][index-1]['enabled']:
        return handler.send(409, {'error': 'Kamera ausgeschaltet'})
    if not (handler.app.private/'cameras/go2rtc.json').is_file():
        return handler.send(503, {'error': 'Kameras noch nicht eingerichtet'})
    if not SLOTS.acquire(blocking=False):
        return handler.send(503, {'error': 'Alle Kameraverbindungen belegt'})
    upstream = None
    upgraded = False
    try:
        upstream = socket.create_connection(('127.0.0.1', 1984), timeout=4)
        upstream.settimeout(6)
        request = (f'GET /api/ws?src=table{index} HTTP/1.1\r\nHost: 127.0.0.1:1984\r\n'
                   f'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\n'
                   f'Sec-WebSocket-Key: {key}\r\nOrigin: http://127.0.0.1:1984\r\n\r\n')
        upstream.sendall(request.encode('ascii'))
        response = bytearray()
        while b'\r\n\r\n' not in response:
            part = upstream.recv(4096)
            if not part or len(response) + len(part) > 16384:
                raise OSError('Invalid gateway handshake')
            response.extend(part)
        header, remaining = bytes(response).split(b'\r\n\r\n', 1)
        expected = base64.b64encode(hashlib.sha1((key + GUID).encode('ascii')).digest()).decode('ascii')
        fields = dict(line.split(':', 1) for line in header.decode('ascii').split('\r\n')[1:] if ':' in line)
        fields = {name.lower(): value.strip() for name, value in fields.items()}
        if header.split(b'\r\n')[0].split()[1] != b'101' or fields.get('sec-websocket-accept') != expected:
            raise OSError('Gateway rejected handshake')
        # WebSocket upgrades require HTTP/1.1, independently of static/API replies.
        handler.protocol_version = 'HTTP/1.1'
        handler.send_response(101)
        handler.send_header('Upgrade', 'websocket')
        handler.send_header('Connection', 'Upgrade')
        handler.send_header('Sec-WebSocket-Accept', expected)
        handler.end_headers()
        handler.wfile.flush()
        upgraded = True
        client = handler.connection
        client.settimeout(10)
        if remaining:
            client.sendall(remaining)
        last_auth = time.monotonic()
        while True:
            ready, _, _ = select.select([client, upstream], [], [], 2)
            if time.monotonic() - last_auth > 10:
                if not handler.authorized():
                    break
                last_auth = time.monotonic()
            for source in ready:
                data = source.recv(65536)
                if not data:
                    return
                (upstream if source is client else client).sendall(data)
    except (OSError, ValueError, IndexError, UnicodeError):
        if not upgraded:
            handler.send(503, {'error': 'Kamera-Vermittler nicht erreichbar'})
    finally:
        if upstream:
            upstream.close()
        handler.close_connection = True
        SLOTS.release()
