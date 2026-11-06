"""Portable Windows adapter; application code remains in app/ unchanged."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

BASE = Path(__file__).resolve().parent
PRIVATE = BASE / 'app' / 'private'
USER = ctypes.WinDLL('user32', use_last_error=True)
KERNEL = ctypes.WinDLL('kernel32', use_last_error=True)
KERNEL.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
KERNEL.CreateMutexW.restype = wintypes.HANDLE
KERNEL.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
KERNEL.CreateEventW.restype = wintypes.HANDLE
KERNEL.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
KERNEL.OpenEventW.restype = wintypes.HANDLE
KERNEL.SetEvent.argtypes = [wintypes.HANDLE]
KERNEL.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
KERNEL.CloseHandle.argtypes = [wintypes.HANDLE]
INSTANCE = hashlib.sha256(str(BASE).lower().encode()).hexdigest()[:24]
EVENT_NAME = 'Local\\TTSV-Stop-' + INSTANCE


def message(text, error=False):
    USER.MessageBoxW(None, str(text), 'Anzeigetafel – Windows USB', 0x10 if error else 0x40)


def monitors():
    try:
        USER.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        USER.SetProcessDPIAware()

    class Info(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                    ('work', wintypes.RECT), ('flags', wintypes.DWORD)]

    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE,
                                      wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    USER.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info)]

    def visit(handle, dc, rect, data):
        info = Info()
        info.size = ctypes.sizeof(info)
        if USER.GetMonitorInfoW(handle, ctypes.byref(info)):
            r = info.monitor
            found.append(dict(left=r.left, top=r.top, width=r.right-r.left,
                              height=r.bottom-r.top, primary=bool(info.flags & 1)))
        return True

    callback = callback_type(visit)
    USER.EnumDisplayMonitors(None, None, callback, 0)
    if not found:
        raise RuntimeError('Kein Bildschirm erkannt.')
    return sorted(found, key=lambda m: (not m['primary'], m['left'], m['top']))


def choose_monitor(items):
    return next((m for m in items if not m['primary']), items[0])


def browser_path():
    for env, suffix in [('PROGRAMFILES(X86)', 'Microsoft/Edge/Application/msedge.exe'),
                        ('PROGRAMFILES', 'Microsoft/Edge/Application/msedge.exe'),
                        ('PROGRAMFILES', 'Google/Chrome/Application/chrome.exe'),
                        ('LOCALAPPDATA', 'Google/Chrome/Application/chrome.exe')]:
        path = Path(os.environ.get(env, '')) / suffix
        if path.is_file():
            return path
    raise RuntimeError('Bitte Microsoft Edge oder Google Chrome installieren.')


def browser_args(browser, url, monitor, settings=False):
    profile = BASE / 'browser-data' / ('settings' if settings else 'display')
    args = [str(browser), '--user-data-dir=' + str(profile), '--no-first-run',
            '--no-default-browser-check',
            '--window-position=%s,%s' % (monitor['left']+20, monitor['top']+20)]
    if settings:
        return args + ['--app=' + url, '--window-size=1100,850']
    args += ['--kiosk', url, '--window-size=%s,%s' % (monitor['width'], monitor['height'])]
    if browser.name.lower() == 'msedge.exe':
        args.append('--edge-kiosk-type=fullscreen')
    return args


def place_window(process, monitor):
    """Place only this instance's browser, also with negative desktop coordinates."""
    cbtype = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    USER.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    USER.IsWindowVisible.argtypes = [wintypes.HWND]
    USER.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    found = []

    def visit(hwnd, data):
        pid = wintypes.DWORD()
        USER.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid and USER.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    callback = cbtype(visit)
    for _ in range(40):
        USER.EnumWindows(callback, 0)
        if found:
            for hwnd in found:
                USER.SetWindowPos(hwnd, None, monitor['left'], monitor['top'],
                                  monitor['width'], monitor['height'], 0x14)
            return
        if process.poll() is not None:
            return
        time.sleep(.25)


def stop():
    event = KERNEL.OpenEventW(2, False, EVENT_NAME)
    if not event:
        message('Diese USB-Anzeigetafel läuft nicht.')
        return
    try:
        KERNEL.SetEvent(event)
    finally:
        KERNEL.CloseHandle(event)
    # Wait until readers, browsers and HTTP server have closed their files.
    for _ in range(100):
        if not (PRIVATE / 'portable-session.json').exists():
            return
        time.sleep(.2)
    message('Beenden dauert noch. Bitte den Stick noch nicht abziehen.')


def open_settings():
    event = KERNEL.OpenEventW(2, False, EVENT_NAME + '-settings')
    if not event:
        message('Bitte zuerst Starten doppelklicken.')
        return
    try:
        KERNEL.SetEvent(event)
    finally:
        KERNEL.CloseHandle(event)


def run(no_browser=False, test_seconds=0):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=PRIVATE/'portable.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    mutex = KERNEL.CreateMutexW(None, False, 'Local\\TTSV-Run-' + INSTANCE)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        KERNEL.CloseHandle(mutex)
        message('Diese Anzeigetafel läuft bereits. Mit „Einstellungen“ kannst du sie konfigurieren.')
        return
    event = KERNEL.CreateEventW(None, True, False, EVENT_NAME)
    if not event:
        KERNEL.CloseHandle(mutex)
        raise ctypes.WinError(ctypes.get_last_error())
    settings_event = KERNEL.CreateEventW(None, False, False, EVENT_NAME + '-settings')
    http = app = None
    worker = None
    browsers = []
    try:
        sys.path.insert(0, str(BASE/'app'))
        import server
        from http.server import ThreadingHTTPServer
        first = not (PRIVATE/'config.json').exists()
        app = server.App(BASE/'app')
        http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        http.app = app
        url = 'http://127.0.0.1:' + str(http.server_address[1])
        (PRIVATE/'portable-session.json').write_text(json.dumps({'url': url, 'csrf': app.csrf}))
        threading.Thread(target=http.serve_forever, daemon=True).start()
        worker = threading.Thread(target=app.supervise, daemon=True)
        worker.start()
        if not no_browser:
            screens = monitors()
            browser = browser_path()
            target = choose_monitor(screens)
            process = subprocess.Popen(browser_args(browser, url+'/spiele.html', target))
            browsers.append(process)
            place_window(process, target)
            if first:
                primary = next(m for m in screens if m['primary'])
                browsers.append(subprocess.Popen(browser_args(browser, url+'/settings.html', primary, True)))
        logging.info('Anzeigetafel gestartet: %s', url)
        started = time.monotonic()
        while KERNEL.WaitForSingleObject(event, 250) == 258:
            if KERNEL.WaitForSingleObject(settings_event, 0) == 0 and not no_browser:
                primary = next(m for m in monitors() if m['primary'])
                browsers.append(subprocess.Popen(browser_args(browser_path(), url+'/settings.html', primary, True)))
            if test_seconds and time.monotonic()-started >= test_seconds:
                break
    finally:
        if app:
            app.stop.set()
        if http:
            http.shutdown()
            http.server_close()
        if worker:
            worker.join(timeout=25)
        if app:
            app.stop_janova()
        # Close only windows owned by this launch; leave other browser sessions alone.
        for process in browsers:
            if process.poll() is None:
                subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
        (PRIVATE/'portable-session.json').unlink(missing_ok=True)
        KERNEL.CloseHandle(settings_event)
        KERNEL.CloseHandle(event)
        KERNEL.CloseHandle(mutex)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--settings', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--test-seconds', type=int, default=0)
    args = parser.parse_args()
    try:
        if args.check:
            print(json.dumps({'monitors': monitors(), 'browser': str(browser_path())}))
        elif args.stop:
            stop()
        elif args.settings:
            open_settings()
        else:
            run(args.no_browser, args.test_seconds)
    except Exception as error:
        logging.exception('Start/Bedienung fehlgeschlagen')
        if sys.stdout is not None:
            raise
        message(str(error) + '\nDetails: app/private/portable.log', error=True)
