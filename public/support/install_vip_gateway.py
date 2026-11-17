"""Install the optional, pinned Linux x86_64 VIP gateway in this instance's private directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import requests

VERSION='v1.9.15'
SHA256='20b46c6910734cb05ecefb234066f36868ff19b42ba1418a7a32e13a3e035712'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    args=parser.parse_args()
    if sys.platform!='linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('Der automatische Kameravermittler ist zunächst für Linux/NUC x86_64 vorgesehen.')
    if os.geteuid()==0:parser.error('Als normaler Benutzer in der Python-Umgebung dieser Anzeigetafel ausführen, nicht mit sudo.')
    os.umask(0o077)
    root=args.root.resolve()
    if not (root/'server.py').is_file():parser.error('Kein Anzeigetafel-Projekt im Zielverzeichnis')
    folder=root/'private/cameras';folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    binary=folder/'go2rtc_linux_amd64'
    if not binary.is_file() or hashlib.sha256(binary.read_bytes()).hexdigest()!=SHA256:
        response=requests.get(f'https://github.com/AlexxIT/go2rtc/releases/download/{VERSION}/go2rtc_linux_amd64',timeout=(10,90))
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest()!=SHA256:raise RuntimeError('go2rtc-Prüfsumme stimmt nicht überein')
        temp=binary.with_suffix('.tmp');temp.write_bytes(response.content);temp.chmod(0o700);temp.replace(binary)
    binary.chmod(0o700)
    license=requests.get(f'https://raw.githubusercontent.com/AlexxIT/go2rtc/{VERSION}/LICENSE',timeout=20)
    license.raise_for_status();(folder/'LICENSE.go2rtc').write_bytes(license.content)
    subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-deps','--target',str(folder/'python'),'imageio-ffmpeg==0.6.0'],check=True)
    unit=Path.home()/'.config/systemd/user/tt-anzeigetafel-cameras.service';unit.parent.mkdir(parents=True,exist_ok=True)
    unit.write_text(f'''[Unit]
Description=TT-Anzeigetafel optional local camera gateway
After=network-online.target

[Service]
ExecStart={json.dumps(str(binary))} -config {json.dumps(str(folder/'go2rtc.json'))}
WorkingDirectory={json.dumps(str(folder))}
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
UMask=0077

[Install]
WantedBy=default.target
''',encoding='utf-8')
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','enable',unit.name],check=True)
    print('Kameravermittler installiert. In den VIP-Einstellungen Kameras eintragen, speichern und „Kameras neu verbinden“ wählen.')


if __name__=='__main__':main()
