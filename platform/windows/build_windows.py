"""Build a portable distribution from the shared source; run on Windows x64."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

SOURCE = Path(__file__).resolve().parents[2]
PYTHON_URL = 'https://www.python.org/ftp/python/3.13.15/python-3.13.15-embed-amd64.zip'
PYTHON_SHA256 = 'd1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf'
CORE = ['server.py', 'janova_reader.py', 'web4sport_client.py', 'test_v2.py',
        'public', 'VERSION', 'RELEASE-NOTES.md', 'requirements.txt', 'requirements.lock']


def build(target, runtime_zip=None):
    target = target.resolve()
    if target.exists():
        raise RuntimeError('Ausgabeordner muss neu sein: ' + str(target))
    target.mkdir(parents=True)
    runtime = target/'runtime'
    runtime.mkdir()
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(runtime_zip) if runtime_zip else Path(temp)/'python.zip'
        if not runtime_zip:
            urllib.request.urlretrieve(PYTHON_URL, archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != PYTHON_SHA256:
            raise RuntimeError('Python-Prüfsumme stimmt nicht.')
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(runtime)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--only-binary=:all:',
                    '--target', str(runtime/'Lib/site-packages'),
                    '-r', str(SOURCE/'requirements.lock')], check=True)
    (runtime/'python313._pth').write_text(
        'python313.zip\n.\nLib/site-packages\n../app\n..\nimport site\n', encoding='utf-8')
    (target/'app').mkdir()
    for name in CORE:
        source, destination = SOURCE/name, target/'app'/name
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(source, destination)
    shutil.copy2(SOURCE/'platform/windows/launcher.py', target/'launcher.py')
    for name, option in [('Starten', ''), ('Einstellungen', '--settings'), ('Beenden', '--stop')]:
        (target/(name+'.cmd')).write_text(
            '@echo off\nstart "" "%~dp0runtime\\pythonw.exe" -X utf8 "%~dp0launcher.py" '+option+'\n',
            encoding='ascii')
    shutil.copy2(SOURCE/'platform/windows/BITTE-LESEN.md', target/'BITTE-LESEN.md')
    shutil.copy2(SOURCE/'docs/UPDATES.md', target/'UPDATES.md')
    manifest = {'version': (SOURCE/'VERSION').read_text().strip(), 'platform': 'windows-x64',
                'pythonUrl': PYTHON_URL, 'pythonSha256': PYTHON_SHA256,
                'files': {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(target.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}}
    (target/'build-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('target', type=Path)
    parser.add_argument('--runtime-zip', type=Path)
    options = parser.parse_args()
    build(options.target, options.runtime_zip)
