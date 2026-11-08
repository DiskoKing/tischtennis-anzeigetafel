"""One GitHub release channel; staged application updates, separate from user data."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import zipfile

import requests

REPOSITORY = 'DiskoKing/tischtennis-anzeigetafel'
API = 'https://api.github.com/repos/' + REPOSITORY + '/releases/latest'
PREFIX = 'https://github.com/' + REPOSITORY + '/releases/download/'
MAX_DOWNLOAD = 24 * 1024 * 1024
FILES = {'server.py', 'updater.py', 'janova_reader.py', 'web4sport_client.py',
         'VERSION', 'UPDATE.json', 'README.md', 'RELEASE-NOTES.md', 'requirements.txt', 'requirements.lock'}


def version(root):
    try:
        value = (Path(root)/'VERSION').read_text(encoding='utf-8').strip()
        if re.fullmatch(r'\d+\.\d+\.\d+', value):
            return value
    except OSError:
        pass
    return '2.0.0'


def last_result(root):
    path = Path(root)/'private/update-result.json'
    try:
        result = json.loads(path.read_text(encoding='utf-8'))
        return {'ok': bool(result.get('ok')), 'message': str(result.get('message', ''))[:500], 'time': path.stat().st_mtime_ns}
    except (OSError, ValueError, AttributeError):
        return None


def newer(candidate, installed):
    if not re.fullmatch(r'\d+\.\d+\.\d+', candidate):
        return False
    return tuple(map(int, candidate.split('.'))) > tuple(map(int, installed.split('.')))


def service_for_current_process():
    if os.name == 'nt':
        return None
    for name in ('ttsv-scoreboard-v2.service', 'anzeigetafel.service'):
        try:
            result = subprocess.run(['systemctl', '--user', 'show', name, '-p', 'MainPID', '--value'],
                                    capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout.strip() == str(os.getpid()):
                return name
        except (OSError, subprocess.TimeoutExpired):
            pass
    return None


def installation(root):
    if os.name == 'nt':
        supported = (Path(root).parent/'launcher.py').is_file()
        return supported, None
    unit = service_for_current_process()
    return bool(unit), unit


def fetch_bytes(url, limit):
    # Only fixed repository assets are accepted as starting URLs. GitHub may redirect
    # downloads to its release-asset CDN; requests retains normal TLS verification.
    if not url.startswith(PREFIX):
        raise ValueError('Downloadquelle ist nicht das konfigurierte GitHub-Projekt.')
    with requests.get(url, stream=True, timeout=(10, 45)) as response:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError('Update-Datei überschreitet die Größenbegrenzung.')
        return bytes(data)


def latest(root):
    response = requests.get(API, timeout=(10, 20), headers={'Accept': 'application/vnd.github+json'})
    response.raise_for_status()
    release = response.json()
    tag = release.get('tag_name', '')
    candidate = tag.removeprefix('v')
    if release.get('draft') or release.get('prerelease') or not re.fullmatch(r'\d+\.\d+\.\d+', candidate):
        raise ValueError('Keine passende veröffentlichte Version gefunden.')
    assets = {asset['name']: asset for asset in release.get('assets', [])}
    payload = assets.get('anzeigetafel-update.zip')
    checksums = assets.get('SHA256SUMS')
    supported, _ = installation(root)
    return {'installed': version(root), 'latest': candidate, 'available': newer(candidate, version(root)),
            'installSupported': supported and bool(payload and checksums),
            'notes': str(release.get('body') or '')[:30000],
            'releaseUrl': 'https://github.com/' + REPOSITORY + '/releases/tag/' + tag,
            'payload': payload, 'checksums': checksums}


def unpack(payload, destination, expected_version):
    import io
    destination = Path(destination)
    seen = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
        if len(bundle.infolist()) > 1000:
            raise ValueError('Zu viele Dateien im Update.')
        for item in bundle.infolist():
            if item.is_dir():
                continue
            name = item.filename
            path = PurePosixPath(name)
            if ('\\' in name or ':' in name or path.is_absolute() or '..' in path.parts or
                    name != path.as_posix() or name.casefold() in seen or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError('Unzulässiger Dateipfad im Update.')
            if name not in FILES and path.parts[0] not in ('public', 'docs'):
                raise ValueError('Update versucht, geschützte Dateien zu ersetzen.')
            if path.parts[0] == 'public' and any(part in ('private', 'browser-data') for part in path.parts):
                raise ValueError('Unzulässiger Datenpfad.')
            total += item.file_size
            if total > 64 * 1024 * 1024 or item.file_size > 12 * 1024 * 1024:
                raise ValueError('Entpacktes Update ist zu groß.')
            seen.add(name.casefold())
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(item))
    if not {'version', 'server.py', 'updater.py', 'requirements.lock'} <= seen:
        raise ValueError('Update ist unvollständig.')
    if version(destination) != expected_version:
        raise ValueError('Versionsnummer des Pakets stimmt nicht.')
    # Compile application modules before stopping the working instance.
    for name in seen:
        if name.endswith('.py'):
            compile((destination/name).read_text(encoding='utf-8'), name, 'exec')
    return sorted(item.filename for item in bundle.infolist() if not item.is_dir())


def prepare(root, release):
    root = Path(root).resolve()
    package = fetch_bytes(release['payload']['browser_download_url'], MAX_DOWNLOAD)
    sums = fetch_bytes(release['checksums']['browser_download_url'], 65536).decode('ascii')
    match = re.search(r'^([0-9a-fA-F]{64})\s+\*?anzeigetafel-update\.zip\s*$', sums, re.M)
    digest = hashlib.sha256(package).hexdigest()
    if not match or digest != match.group(1).lower():
        raise ValueError('SHA-256-Prüfung des Updates fehlgeschlagen.')
    published_digest = release['payload'].get('digest')
    if published_digest and published_digest != 'sha256:' + digest:
        raise ValueError('GitHub-Prüfsumme stimmt nicht.')
    folder = root/'private'/'updates'/uuid.uuid4().hex
    folder.mkdir(parents=True, mode=0o700)
    staged = folder/'candidate'
    files = unpack(package, staged, release['latest'])
    if (root/'requirements.lock').read_text(encoding='utf-8').splitlines() != (staged/'requirements.lock').read_text(encoding='utf-8').splitlines():
        raise ValueError('Diese Version benötigt neue Laufzeit-Abhängigkeiten. Bitte das vollständige Paket installieren.')
    if os.name == 'nt':
        metadata = json.loads((staged/'UPDATE.json').read_text(encoding='utf-8'))
        launcher = root.parent/'launcher.py'
        if metadata.get('windowsLauncherSha256') != hashlib.sha256(launcher.read_bytes()).hexdigest():
            raise ValueError('Diese Version benötigt einen neuen Windows-Starter. Bitte das vollständige Paket installieren.')
    # The helper runs from a private copy outside the code being replaced.
    shutil.copy2(Path(__file__), folder/'helper.py')
    shutil.copy2(root/'private/config.json', folder/'config-before.json')
    return folder, files


def begin(app, port, expected_version=None):
    if not hasattr(app, 'update_lock'):
        app.update_lock = threading.Lock()
    if not app.update_lock.acquire(blocking=False):
        raise ValueError('Ein Update wird bereits vorbereitet.')
    try:
        release = latest(app.root)
        if not expected_version or release['latest'] != expected_version:
            raise ValueError('Bitte zuerst die aktuell verfügbare Version prüfen.')
        if not release['available']:
            raise ValueError('Die installierte Version ist bereits aktuell.')
        supported, unit = installation(app.root)
        if not supported or not release['installSupported']:
            raise ValueError('Für diese Installation bitte das vollständige Paket vom Release herunterladen.')
        folder, files = prepare(app.root, release)
        plan = {'root': str(app.root.resolve()), 'folder': str(folder), 'files': files,
                'version': release['latest'], 'oldVersion': version(app.root), 'pid': os.getpid(),
                'unit': unit, 'port': port, 'python': sys.executable}
        planfile = folder/'plan.json'
        planfile.write_text(json.dumps(plan), encoding='utf-8')
        command = [sys.executable, '-X', 'utf8', str(folder/'helper.py'), '--install', str(planfile)]
        if os.name == 'nt':
            subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Separate systemd unit survives stopping the application's own cgroup.
            subprocess.run(['systemd-run', '--user', '--collect', '--unit=anzeigetafel-update-' + folder.name,
                            '--property=UMask=0077'] + command, check=True, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {'ok': True, 'message': 'Update geprüft. Die Anzeigetafel wird neu gestartet.', 'version': release['latest']}
    except Exception:
        app.update_lock.release()
        raise


def stop_instance(plan):
    if os.name != 'nt':
        subprocess.run(['systemctl', '--user', 'stop', plan['unit']], check=True, timeout=45)
        return
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.OpenEventW.restype = wintypes.HANDLE
    kernel.SetEvent.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    base = Path(plan['root']).parent
    name = 'Local\\TTSV-Stop-' + hashlib.sha256(str(base).lower().encode()).hexdigest()[:24]
    event = kernel.OpenEventW(2, False, name)
    if not event:
        raise RuntimeError('Die laufende Windows-Instanz konnte nicht beendet werden.')
    try:
        kernel.SetEvent(event)
    finally:
        kernel.CloseHandle(event)
    session = Path(plan['root'])/'private/portable-session.json'
    for _ in range(240):
        if not session.exists():
            time.sleep(.5)
            return
        time.sleep(.25)
    raise RuntimeError('Beenden der Windows-Instanz hat zu lange gedauert.')


def start_instance(plan):
    if os.name == 'nt':
        subprocess.Popen([plan['python'], '-X', 'utf8', str(Path(plan['root']).parent/'launcher.py')],
                         creationflags=subprocess.CREATE_NO_WINDOW,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(['systemctl', '--user', 'start', plan['unit']], check=True, timeout=30)
        # Optional adapter must pick up its updated Python code as well.
        try:
            subprocess.run(['systemctl', '--user', 'try-restart', 'streamdock.service'],
                           check=False, timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            pass  # An optional controller must not prevent the display from starting.


def healthy(plan, expected):
    for _ in range(120):
        try:
            if os.name == 'nt':
                session = json.loads((Path(plan['root'])/'private/portable-session.json').read_text(encoding='utf-8'))
                url = session['url']
                with urllib.request.urlopen(url+'/api/session', timeout=2) as response:
                    if json.load(response)['csrf'] != session['csrf']:
                        raise ValueError('Falsche Sitzung')
            else:
                url = 'http://127.0.0.1:' + str(plan['port'])
            with urllib.request.urlopen(url+'/api/config', timeout=2) as response:
                if json.load(response)['version'] == expected:
                    return True
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(.25)
    return False


def replace_code(plan):
    root, folder = Path(plan['root']), Path(plan['folder'])
    backup = folder/'backup'
    backup.mkdir()
    existed = []
    # Back up the entire replace set before touching any live file.
    for name in plan['files']:
        target, saved = root/name, backup/name
        if target.exists():
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            existed.append(name)
    (folder/'existed.json').write_text(json.dumps(existed), encoding='utf-8')
    for name in plan['files']:
        target = root/name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name+'.update-stage')
        shutil.copy2(folder/'candidate'/name, temporary)
        os.replace(temporary, target)


def rollback(plan):
    root, folder = Path(plan['root']), Path(plan['folder'])
    existed = json.loads((folder/'existed.json').read_text(encoding='utf-8'))
    for name in plan['files']:
        target, saved = root/name, folder/'backup'/name
        if name in existed:
            shutil.copy2(saved, target)
        else:
            target.unlink(missing_ok=True)
    shutil.copy2(folder/'config-before.json', root/'private/config.json')


def install(plan):
    time.sleep(2)  # Allow the API response to reach the settings page.
    status = Path(plan['root'])/'private/update-result.json'
    stopped = replaced = False
    try:
        stop_instance(plan)
        stopped = True
        replaced = True
        replace_code(plan)
        start_instance(plan)
        if not healthy(plan, plan['version']):
            raise RuntimeError('Neue Version startet nicht korrekt.')
        result = {'ok': True, 'message': 'Update auf ' + plan['version'] + ' erfolgreich.'}
    except Exception as error:
        result = {'ok': False, 'message': str(error)}
        if stopped:
            try:
                # If the new instance started, stop it before restoring its files.
                try:
                    stop_instance(plan)
                except Exception:
                    pass
                if replaced and (Path(plan['folder'])/'existed.json').exists():
                    rollback(plan)
                start_instance(plan)
                result['message'] += ' Vorherige Version wurde wiederhergestellt.'
            except Exception as recovery:
                result['message'] += ' Rücksicherung benötigt Hilfe: ' + str(recovery)
    status.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--install':
        install(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
