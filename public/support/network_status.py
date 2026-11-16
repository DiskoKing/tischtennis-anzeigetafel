"""Read-only platform adapters. Never change Wi-Fi, start hotspots or probe Internet."""
import ipaddress
import json
import os
import platform
import shutil
import socket
import re
import subprocess
import threading
import time


def local_hostname():
    name = socket.gethostname().split('.')[0].lower()
    return name + '.local' if re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', name) else None


def run(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=10 if os.name == 'nt' else 3,
                          encoding='utf-8', errors='replace',
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0).stdout


def ipv4(value):
    try:
        address = ipaddress.IPv4Address(value)
        return str(address) if not address.is_loopback and not address.is_link_local else None
    except ValueError:
        return None


def linux_status():
    addresses = json.loads(run(['ip', '-j', '-4', 'address', 'show', 'up']))
    routes = json.loads(run(['ip', '-j', '-4', 'route', 'show', 'default']))
    preferred = [r.get('dev') for r in routes]
    interfaces = []
    for item in addresses:
        for address in item.get('addr_info', []):
            local = ipv4(address.get('local', ''))
            if local:
                interfaces.append((item['ifname'], local))
    interfaces.sort(key=lambda item: (item[0] not in preferred, item[0]))
    if not interfaces:
        return {'connection': 'offline', 'ips': [], 'ip': None, 'ssid': None, 'signalPercent': None}
    name, address = interfaces[0]
    from pathlib import Path
    wireless = (Path('/sys/class/net')/name/'wireless').exists()
    ssid = None
    signal = None
    if wireless and shutil.which('nmcli'):
        # SSIDs are separate unescaped lines; do not parse colon-delimited user text.
        rows = run(['nmcli', '-t', '--escape', 'no', '-f', 'IN-USE,SIGNAL,SSID', 'device', 'wifi',
                    'list', 'ifname', name, '--rescan', 'no'])
        for row in rows.splitlines():
            if row.startswith('*:'):
                _, strength, ssid = row.split(':', 2)
                signal = int(strength) if strength.isdigit() else None
                break
    return {'connection': 'wifi' if wireless else 'ethernet', 'ips': [ip for _, ip in interfaces],
            'ip': address, 'ssid': ssid or None, 'signalPercent': signal}


def windows_status():
    # Structured PowerShell objects avoid localized netsh/ipconfig parsing.
    script = """$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new();
$a=@(Get-NetIPConfiguration | Where-Object {$_.NetAdapter.Status -eq 'Up' -and $_.IPv4Address} | ForEach-Object {
[pscustomobject]@{ip=$_.IPv4Address.IPAddress; wireless=($_.NetAdapter.NdisPhysicalMedium -in @(1,9)); gateway=[bool]$_.IPv4DefaultGateway}
}); ConvertTo-Json -Compress -InputObject $a"""
    values = json.loads(run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script]).lstrip('\ufeff'))
    values.sort(key=lambda v: not v['gateway'])
    addresses = [(v, ipv4(ip)) for v in values for ip in (v['ip'] if isinstance(v['ip'], list) else [v['ip']])]
    addresses = [(v, ip) for v, ip in addresses if ip]
    if not addresses:
        return {'connection': 'offline', 'ips': [], 'ip': None, 'ssid': None, 'signalPercent': None}
    first, address = addresses[0]
    ssid, signal = windows_wifi() if first['wireless'] else (None, None)
    return {'connection': 'wifi' if first['wireless'] else 'ethernet', 'ips': [ip for _, ip in addresses],
            'ip': address, 'ssid': ssid, 'signalPercent': signal}


def windows_wifi():
    """Native WLAN API: no localized CLI parsing, scans or connection changes."""
    import ctypes as c
    from ctypes import wintypes as w
    class Guid(c.Structure):
        _fields_ = [('data', c.c_ubyte * 16)]
    class Interface(c.Structure):
        _fields_ = [('guid', Guid), ('description', w.WCHAR * 256), ('state', c.c_int)]
    class Ssid(c.Structure):
        _fields_ = [('length', w.DWORD), ('bytes', c.c_ubyte * 32)]
    class Association(c.Structure):
        _fields_ = [('ssid', Ssid), ('bss', c.c_int), ('bssid', c.c_ubyte * 6), ('phy', c.c_int),
                    ('phyIndex', w.DWORD), ('signal', w.DWORD), ('rx', w.DWORD), ('tx', w.DWORD)]
    class Security(c.Structure):
        _fields_ = [('enabled', w.BOOL), ('oneX', w.BOOL), ('auth', c.c_int), ('cipher', c.c_int)]
    class Connection(c.Structure):
        _fields_ = [('state', c.c_int), ('mode', c.c_int), ('profile', w.WCHAR * 256),
                    ('association', Association), ('security', Security)]
    handle, listing = w.HANDLE(), c.c_void_p()
    try:
        api = c.WinDLL('wlanapi.dll')
        api.WlanOpenHandle.argtypes = [w.DWORD, c.c_void_p, c.POINTER(w.DWORD), c.POINTER(w.HANDLE)]
        api.WlanEnumInterfaces.argtypes = [w.HANDLE, c.c_void_p, c.POINTER(c.c_void_p)]
        api.WlanQueryInterface.argtypes = [w.HANDLE, c.POINTER(Guid), c.c_int, c.c_void_p,
                                           c.POINTER(w.DWORD), c.POINTER(c.c_void_p), c.POINTER(c.c_int)]
        api.WlanFreeMemory.argtypes = [c.c_void_p]
        api.WlanCloseHandle.argtypes = [w.HANDLE, c.c_void_p]
        negotiated = w.DWORD()
        if api.WlanOpenHandle(2, None, c.byref(negotiated), c.byref(handle)):
            return None, None
        if api.WlanEnumInterfaces(handle, None, c.byref(listing)):
            return None, None
        count = c.cast(listing, c.POINTER(w.DWORD))[0]
        for index in range(min(count, 64)):
            interface = Interface.from_address(listing.value + 8 + index * c.sizeof(Interface))
            if interface.state != 1:
                continue
            size, data, opcode = w.DWORD(), c.c_void_p(), c.c_int()
            try:
                if api.WlanQueryInterface(handle, c.byref(interface.guid), 7, None, c.byref(size), c.byref(data), c.byref(opcode)) == 0 and size.value >= c.sizeof(Connection):
                    connection = c.cast(data, c.POINTER(Connection)).contents
                    association = connection.association
                    return bytes(association.ssid.bytes[:min(32, association.ssid.length)]).decode('utf-8', 'replace'), min(100, association.signal)
            finally:
                if data.value: api.WlanFreeMemory(data)
    except (OSError, AttributeError, ValueError):
        pass  # Windows privacy settings may deny SSID access; do not request permissions.
    finally:
        if listing.value: api.WlanFreeMemory(listing)
        if handle.value: api.WlanCloseHandle(handle, None)
    return None, None


class NetworkStatus:
    def __init__(self):
        self.lock = threading.Lock()
        self.checked = -100
        self.cached = {'connection': 'unknown', 'ips': [], 'ip': None, 'ssid': None, 'signalPercent': None}

    def get(self):
        with self.lock:
            if time.monotonic() - self.checked < 10:
                return dict(self.cached)
            self.checked = time.monotonic()
            threading.Thread(target=self.refresh, daemon=True).start()
            return dict(self.cached)

    def refresh(self):
        try:
            system = platform.system()
            result = linux_status() if system == 'Linux' else windows_status() if system == 'Windows' else None
            result = result or {'connection': 'unsupported', 'ips': [], 'ip': None, 'ssid': None, 'signalPercent': None}
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            result = {'connection': 'unknown', 'ips': [], 'ip': None, 'ssid': None, 'signalPercent': None}
        with self.lock:
            self.cached = result
            self.checked = time.monotonic()
