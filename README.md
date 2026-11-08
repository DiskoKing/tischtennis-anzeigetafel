# TT-Anzeigetafel

Konfigurierbare Anzeigetafel für Janova-Zählgeräte und TischtennisLive/Web4Sport. Eine gemeinsame Python-/Browser-Codebasis für Linux/NUC und Windows-USB; ein Veröffentlichungskanal.

## Anleitung für den praktischen Betrieb

[PDF-Anleitung](docs/TT-Anzeigetafel-Anleitung.pdf) · [HTML zum Öffnen und Drucken](docs/ANLEITUNG.html) · [Anleitung direkt auf GitHub lesen](docs/ANLEITUNG.md)

Die Anleitung beschreibt Windows-USB sowie die Neueinrichtung auf Raspi/NUC mit Linux, gemeinsame Konfiguration, Spieltag, Updates und Fehlerhilfe. Sie liegt den Paketen unter docs (Linux) bzw. app/docs (Windows) bei. Unter Windows öffnet ANLEITUNG.html im Paketordner die mitgelieferte Fassung. Die PDF ist außerdem ein eigener Release-Download.

## Funktionen

- Manueller Modus: Gegner und Mannschaftsstand, PC-Bedienfenster, Nummernblock und optional Stream Dock 293 V3 unter Linux.
- Vereinsname, Website, Farben und eigenes Vereinslogo.
- Kompaktansicht, Detailansicht oder zeitgesteuerter Wechsel.
- Janova-ID bzw. Live-Link; optionale Anmeldung zur Ermittlung der ID.
- Web4Sport-Anmeldung und Begegnungsauswahl bei mehreren gestarteten Spielen.
- Eigene Hintergründe mit einstellbarer Abdunklung.
- Sponsorenlogos mit Einleitung und Rotation.
- Einstellungen als Overlay für die Bedienung im Kioskmodus.
- Web4Sport: 1, 2 oder 3 Partien in der Detailansicht; Janova bleibt dynamisch.
- Einstellbare Höhe der Fußleiste; Homepage, Uhr und Sponsorenlogos skalieren mit.

## Linux / lokale Entwicklung

Python 3.13 und eine virtuelle Umgebung verwenden:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python server.py --port 8081
```

Anzeige: http://127.0.0.1:8081/spiele.html
Einstellungen: http://127.0.0.1:8081/settings.html

Der Server lauscht nur lokal. Zugriff vom anderen Rechner ist über einen SSH-Tunnel möglich. Für Kioskstart und den Dienst siehe platform/linux.

## Windows-USB

Der Plattformstarter und der Build liegen unter platform/windows. Auf einem Windows-Buildrechner mit Python und pip:

```powershell
python platform/windows/build_windows.py dist/Anzeigetafel-Windows-USB
```

Das Paket enthält eine offizielle Python-Laufzeit und benötigt am Zielrechner keine Python-Installation. Starten.cmd startet Edge/Chrome im Vollbild auf dem ersten zusätzlichen Bildschirm. Einstellungen.cmd öffnet die Konfiguration, Beenden.cmd beendet die Instanz. Windows-Anzeige auf Erweitern stellen. Details und Einschränkungen stehen in platform/windows/BITTE-LESEN.md.

## Daten und Veröffentlichung

Zugangsdaten, Vereinslogo und Uploads liegen unter private/ und werden nicht versioniert. Auf Windows-USB liegt dieser Ordner unter app/private; zusätzlich gibt es browser-data. Ein verlorener Stick kann daher Zugangsdaten enthalten.

Diese öffentliche Fassung enthält neutrale SVG-Standardgrafiken und das vom Ersteller freigegebene Original-Hintergrundbild aus Version 1. Es ist unter Hintergrund → Originalbild aus Version 1 auswählbar. Vereinslogos bleiben außerhalb des öffentlichen Standardkatalogs. Bestehende Praxisinstallationen werden durch einen Git-Upload nicht verändert.

Die optionale Janova-Anmeldung liest die öffentliche Web-App-Konfiguration von Janova. Sie speichert nur die ermittelte Konto-ID; Passwort und Sitzung werden nicht dauerhaft gespeichert. Änderungen an Janovas Web-App können die Erkennung beeinträchtigen; die direkte ID-Eingabe bleibt verfügbar.

## Tests

```sh
python -m unittest -v test_v2
```

GitHub Actions führt diese Tests unter Windows und Linux aus. Eine bewusste Änderung von VERSION auf main startet den getesteten Release-Build und veröffentlicht das passende v-Tag. Andere Änderungen auf main veröffentlichen kein Release. Ab 2.2.0 enthält die Konfiguration Version & Updates: Version prüfen, Release Notes ansehen und Jetzt aktualisieren. Details und Grenzen stehen in docs/UPDATES.md.

## Rechte

Eine Open-Source-Lizenz wurde noch nicht festgelegt. Öffentliche Sichtbarkeit bedeutet keine pauschale Erlaubnis zur Weiterverteilung. Logos, Namen und Dienste Dritter behalten ihre jeweiligen Rechte.
