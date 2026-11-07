"""Einmalige lokale Migration des Update-Kanals; keine Benutzerdaten ändern."""
from pathlib import Path
import argparse
import os

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
args = parser.parse_args()
folder = args.root.resolve()
targets = [folder / 'app/updater.py', folder / 'updater.py']
target = next((path for path in targets if path.is_file()), None)
if target is None:
    raise SystemExit('Bitte in den Anzeigetafel-Ordner neben Starten.cmd legen oder --root APP-ORDNER angeben.')
old = "REPOSITORY = 'frankfehrmann-stack/tischtennis-anzeigetafel'"
new = "REPOSITORY = 'DiskoKing/tischtennis-anzeigetafel'"
original = target.read_bytes()
if new.encode() in original:
    print('Die neue GitHub-Adresse ist bereits eingestellt.')
elif original.count(old.encode()) == 1:
    backup = target.with_name('updater.py.vor-github-umstellung.bak')
    if not backup.exists():
        backup.write_bytes(original)
    temporary = target.with_name('updater.py.github-umstellung.tmp')
    temporary.write_bytes(original.replace(old.encode(), new.encode()))
    os.replace(temporary, target)
    print('Update-Adresse umgestellt. Konfiguration und Zugangsdaten bleiben erhalten.')
else:
    raise SystemExit('Unbekannte Updater-Version. Keine Datei wurde geändert.')
print('Anzeigetafel beenden und neu starten. Danach in den Einstellungen nach Updates suchen.')
