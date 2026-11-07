# TT-Anzeigetafel
## Einrichtung und Bedienung

Euer Spiel. Für die ganze Halle.

Die TT-Anzeigetafel übernimmt Spieldaten automatisch aus Janova oder TischtennisLive / Web4Sport. Einmal mit der gewünschten Quelle verbinden, Vereinsdesign einstellen und die passende Begegnung wählen. Ergebnisse werden nicht zusätzlich in der Anzeigetafel eingetragen.

### Zwei Wege zum Betrieb

- **Windows zum Mitnehmen:** Fertiges Windows-Paket entpacken, Bildschirm anschließen, Starten.cmd doppelklicken. Python ist bereits enthalten.
- **Raspi oder NUC für die Halle:** Linux mit grafischer Oberfläche einmal einrichten. Nach der Anmeldung starten Dienst und Browser automatisch. Empfohlen für einen festen Standort.

### Das wird gebraucht

- Bildschirm oder Fernseher mit passendem HDMI-Anschluss bzw. Adapter; Maus und Tastatur oder ein Touchdisplay für die Einstellungen.
- Internetzugang für Live-Daten, Anmeldung und Updates. Die Anwendung selbst läuft auf dem angeschlossenen Rechner.
- Janova-ID / Janova-Live-Link oder ein berechtigter Zugang zu TischtennisLive / Web4Sport.

### Welche Seite brauche ich?

- Seite 2: Windows starten und beenden.
- Seite 3: Vereinsdesign und Datenquelle einrichten.
- Seiten 4 und 5: Raspi / NUC neu einrichten.
- Seite 6: Ansichten, Sponsoren und Spieltag.
- Seite 7: Updates, Sicherung und Zugriff von einem anderen Rechner.
- Seite 8: Hilfe bei Problemen und Kontakt.

**Bereits fertig eingerichteter Hallenrechner?** Die Linux-Neueinrichtung überspringen. Ein vorhandener Dienst oder Autostart darf nicht durch einen zweiten ergänzt werden.

Anleitung zur Version 2.2.15. Projekt: https://github.com/DiskoKing/tischtennis-anzeigetafel

---

# 1. Windows: entpacken und starten

### Einmal vorbereiten

1. Auf https://github.com/DiskoKing/tischtennis-anzeigetafel/releases/latest das Paket **anzeigetafel-windows-x64.zip** herunterladen. Nicht „Source code“ wählen: Darin fehlt die mitgelieferte Windows-Laufzeit.
2. Die komplette ZIP mit „Alle extrahieren“ in einen beschreibbaren Ordner oder auf einen USB-Stick entpacken. Nicht aus der geöffneten ZIP starten. Die Ordner app und runtime bleiben neben Starten.cmd liegen.
3. Fernseher / Bildschirm anschließen und einschalten. In Windows mit **Win + P > Erweitern** einstellen. Edge oder Chrome muss installiert sein. Unterstützt wird Windows x64; Windows-on-ARM ist hier nicht zugesichert.

### Starten

Starten.cmd doppelklicken. Die Anzeigetafel öffnet sich im Vollbild auf dem ersten zusätzlichen Bildschirm. Gibt es mehrere zusätzliche Bildschirme, entscheidet ihre Anordnung auf dem Windows-Desktop. Ohne Zusatzbildschirm wird der Hauptbildschirm benutzt. Bildschirm am besten vor dem Start anschließen.

Erscheint „Der Herausgeber konnte nicht verifiziert werden“, ist das eine Herkunftswarnung für das unsignierte Startskript. Beim bewusst aus diesem Projekt geladenen Paket „Ausführen“ wählen. Für diese Datei kann die Warnung über Rechtsklick auf Starten.cmd > Eigenschaften > Allgemein > Zulassen, sofern angezeigt, einmalig freigegeben werden. Schutzfunktionen nicht pauschal abschalten.

### Einstellen und beenden

- **Zahnrad oben rechts:** Einstellungen direkt in der Anzeige öffnen. „Zur Anzeigetafel“ schließt das Overlay.
- **Einstellungen.cmd:** Einstellungen in einem separaten Browserfenster öffnen.
- **Beenden.cmd:** Diese Instanz einschließlich Server und zugehöriger Browser beenden. Alt + F4 schließt allein das Fenster und beendet nicht zwingend den Hintergrundbetrieb.

Vor dem Abziehen des USB-Sticks Beenden.cmd ausführen und anschließend Windows „Sicher entfernen“ verwenden. Beim nächsten Start bleiben die gespeicherten Vereinsdaten erhalten. Eine neue ZIP nicht unbedacht über eine laufende Installation entpacken; für normale Versionswechsel den Updateknopf verwenden.

**Datenablage:** app/private enthält Konfiguration, Uploads und gegebenenfalls Zugangsdaten. Den Stick entsprechend behandeln und diesen Ordner vor einem Paketwechsel sichern.

---

# 2. Einmal konfigurieren - für beide Wege

### Verein und Design

Über das Zahnrad „Verein & Design“ öffnen. Vereinsname und Homepage eintragen, Akzent- und Hintergrundfarbe wählen und das Vereinslogo hochladen. Möglich sind PNG, JPEG, GIF und WebP bis 10 MB. Ohne neuen Upload bleibt das vorhandene Logo gespeichert.

Beim Hintergrund stehen CSS-Design, neutraler Hintergrund, das Originalbild aus Version 1 oder ein eigenes Bild zur Wahl. Die Abdunklung lässt sich anpassen. Die Designvorschau hilft beim Abstimmen; maßgeblich ist die Anzeige auf dem Hallenbildschirm.

### Janova verbinden

1. Unter „Datenquelle“ Janova wählen. Dann erscheint der passende Loginbereich.
2. Entweder mit Janova anmelden und die ID übernehmen oder eine bekannte Referee-ID bzw. einen Janova-Live-Link einfügen. Einen Live-Link findet ihr nach Anmeldung auf https://janova.app/live/urls.
3. **Einstellungen speichern.** Die optionale Anmeldung dient zum Ermitteln der ID; Janova-Passwort und Sitzung werden nicht dauerhaft gespeichert.

Die Anzahl dargestellter Janova-Partien richtet sich dynamisch nach den aktiven Zählgeräten. Janova liefert Live-Punkte und Sätze. Falls die automatische ID-Erkennung nicht funktioniert, bleibt die direkte ID-/Link-Eingabe verfügbar.

### TischtennisLive / Web4Sport verbinden

1. Unter „Datenquelle“ TischtennisLive / Web4Sport wählen.
2. Benutzername und Passwort eintragen und **Einstellungen speichern**. Ein später leeres Passwortfeld behält das gespeicherte Passwort bei; die separate Löschoption entfernt es.
3. „Verbindung & Spielauswahl“ kontrollieren. Bei mehreren gestarteten Spielen die gewünschte Begegnung wählen. Für dieses Konto muss der Spielbericht zugänglich sein.

Der Live-Spielbericht muss gestartet sein. Web4Sport liefert hier Satzstände, keine verifizierten Live-Ballpunkte. Änderungen werden nach dem nächsten Abruf sichtbar; der Web4Sport-Abruf erfolgt ungefähr alle 15 Sekunden.

**Wichtig:** Die Anzeigetafel zeigt die Daten der gewählten Quelle. Sie startet keinen Spielbericht und ersetzt weder die Janova-Zählgeräte noch die Eingabe des Live-Spielberichts.

---

# 3. Raspi / NUC: neue Linux-Installation

### Geeigneter Ausgangspunkt

Empfohlen sind ein Raspberry Pi ab Modell 4 oder ein NUC / Mini-PC mit Linux. Auf dem Raspi eine aktuelle 64-Bit-Desktop-Ausgabe von Raspberry Pi OS verwenden; auf dem Mini-PC ein aktuelles Debian-basiertes Desktop-Linux. Bildschirm, Stromversorgung, Netzwerk und grafische Anmeldung müssen funktionieren. Der Pi 3 wurde im Projekt erprobt; für neue Installationen ist Pi 4 oder neuer die Empfehlung.

Die Anwendung wird mit Python 3.13 gebaut und getestet. Vorab `python3 --version` prüfen. Bei älteren Systemen zuerst auf ein passendes Betriebssystem wechseln; System-Python nicht unkontrolliert ersetzen. Die folgenden apt-Befehle gelten für Debian-basierte Systeme und benötigen Administratorrechte.

**Nur für einen neuen Rechner bzw. eine neue Installation:** Bestehende Praxisinstallationen können andere Ordner- und Dienstnamen haben. Dort die Einrichtung nicht nochmals ausführen.

### Voraussetzungen installieren

```sh
sudo apt update
sudo apt install python3 python3-venv python3-pip chromium curl
python3 --version
```

### Linux-Paket laden und entpacken

```sh
mkdir -p "$HOME/Downloads"
curl -fL \
  https://github.com/DiskoKing/tischtennis-anzeigetafel/releases/latest/download/anzeigetafel-linux.tar.gz \
  -o "$HOME/Downloads/anzeigetafel-linux.tar.gz"
tar -xzf "$HOME/Downloads/anzeigetafel-linux.tar.gz" -C "$HOME"
cd "$HOME/tischtennis-anzeigetafel"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py --port 8081
```

Im Browser auf diesem Rechner http://127.0.0.1:8081/spiele.html öffnen. Über das Zahnrad konfigurieren und die Datenquelle prüfen. Danach den Testserver im Terminal mit **Strg + C** beenden, bevor auf der nächsten Seite der Dienst eingerichtet wird.

Falls das Paket schon manuell heruntergeladen wurde, den curl-Schritt überspringen. Der Zielordner muss zum Dienst auf der nächsten Seite passen: ~/tischtennis-anzeigetafel.

---

# 4. Linux: automatischer Hallenbetrieb

### Dienst einrichten

Die folgenden Befehle als normaler Desktop-Benutzer ausführen, nicht mit sudo. Der Dienst startet den Python-Server und wird vom Updater erkannt.

```sh
mkdir -p ~/.config/systemd/user
cp ~/tischtennis-anzeigetafel/platform/linux/anzeigetafel.service \
  ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now anzeigetafel.service
systemctl --user status anzeigetafel.service --no-pager
```

### Browser nach der grafischen Anmeldung starten

Die folgenden Blöcke vollständig ins Terminal kopieren. Der Starter wartet auf den Server und öffnet Chromium im Kioskmodus. Die automatische Desktop-Anmeldung muss in den Systemeinstellungen eingerichtet sein; beim Raspi beispielsweise über raspi-config. Im Desktop Bildschirmsperre und automatische Bildschirmabschaltung für den Hallenbetrieb passend einstellen.

```sh
mkdir -p ~/.local/bin ~/.config/autostart
cat > ~/.local/bin/tt-anzeigetafel-kiosk <<'EOF'
#!/bin/sh
until curl -fsS http://127.0.0.1:8081/spiele.html >/dev/null; do
  sleep 2
done
exec chromium --kiosk --no-first-run --password-store=basic \
  --user-data-dir="$HOME/.local/share/tt-anzeigetafel-browser" \
  http://127.0.0.1:8081/spiele.html
EOF
chmod +x ~/.local/bin/tt-anzeigetafel-kiosk
cat > ~/.config/autostart/tt-anzeigetafel.desktop <<EOF
[Desktop Entry]
Type=Application
Name=TT-Anzeigetafel
Exec=$HOME/.local/bin/tt-anzeigetafel-kiosk
Terminal=false
EOF
```

Einmal neu starten und prüfen: Desktop meldet sich an, Browser öffnet die Anzeigetafel, Zahnrad öffnet die Einstellungen. Bei mehreren Displays legt diese Linux-Vorlage keinen Zielbildschirm fest; die gewünschte Anordnung im Desktop einstellen. Für einen Hallenrechner mit einem Bildschirm ist das der einfache Standardweg.

**Sauber abschalten:** Den Rechner über das Betriebssystem herunterfahren. Alt + F4 schließt den Kioskbrowser; der Serverdienst läuft weiter. Neustart des Servers bei Bedarf: `systemctl --user restart anzeigetafel.service`.

---

# 5. Ansichten, Sponsoren und Spieltag

### Anzeige nach Wunsch

- **Nur Kompaktansicht:** Großes Mannschaftsergebnis mit Vereinen und Wettbewerb.
- **Nur Detailansicht:** Paarungen und Satzstände; bei Janova zusätzlich Live-Ballpunkte und Spielhinweise, soweit geliefert.
- **Automatisch wechseln:** Kompakt und Detail wechseln bei aktiven Spielen. Das Intervall ist einstellbar; Standard sind 30 Sekunden.
- **Web4Sport-Partien:** 1, 2 oder 3 nächste offene Paarungen in Spielreihenfolge. Standard: 2. Ohne Tischzuordnung ist das keine verifizierte Belegung der realen Tische.
- **Fußleiste:** Höhe zwischen 5 und 15 % der Bildschirmhöhe; Standard: 8,5 %. Logos, Homepage und Uhr skalieren mit.

### Sponsoren einrichten

Unter „Sponsoren“ die Anzeige ein- oder ausschalten, Logos hochladen und die Wechselzeit festlegen. Mehrere Logos rotieren automatisch, ein einzelnes Logo bleibt stehen. Der Einleitungstext ist frei wählbar; Standard ist „unterstützt von:“.

Bis zu 20 Logos; PNG, JPEG, GIF oder WebP, jeweils maximal 10 MB. Transparenz bleibt erhalten. Ein weißer Hintergrund, der bereits Teil der Bilddatei ist, wird nicht automatisch entfernt. Sponsoren werden als Bilder dargestellt, nicht als klickbare Werbelinks.

Nach Änderungen **Einstellungen speichern** wählen. „Alle Bereiche aufklappen“ und „Alle Bereiche zuklappen“ erleichtern den Überblick. Danach über „Zur Anzeigetafel“ zurückkehren.

### Vor dem Spiel: kurze Checkliste

1. Bildschirm, Rechner und Internet eingeschaltet? Anzeige im richtigen Vollbild?
2. Vereinslogo, Gegner und Wettbewerb richtig? Bei Web4Sport das richtige gestartete Spiel gewählt?
3. Janova-Geräte aktiv bzw. Live-Spielbericht gestartet und gepflegt?
4. Ansicht, Anzahl der Partien, Homepage und Sponsoren passend?
5. Uhrzeit und Datum des Rechners korrekt? Die Anzeige übernimmt die Systemzeit.
6. Einen kurzen Datenwechsel prüfen. Größere Updates am besten vor dem Spieltag testen.

Noch kein Spiel? Die neutrale Anzeige mit Vereinslogo und Fußleiste ist vorgesehen. Ein Hinweis unten nennt den Verbindungs- oder Wartezustand.

---

# 6. Updates, Sicherung und Zugriff

### Normale Updates

Unter „Version & Updates“ auf „Nach Updates suchen“ klicken. Versionshinweise lesen und ein angebotenes Update installieren. Vorher ungespeicherte Änderungen speichern. Die Anwendung wird kurz beendet und neu gestartet; Logo, Bilder und Konfiguration sollen erhalten bleiben. Während eines laufenden Mannschaftskampfs möglichst nicht aktualisieren.

Automatische Installation setzt eine unterstützte Umgebung voraus: Windows-Paket mit Plattformstarter oder Linux-Dienst anzeigetafel.service bzw. der bestehende NUC-Dienst ttsv-scoreboard-v2.service. Bei einem manuell gestarteten Entwicklungsserver kann die automatische Installation nicht angeboten werden. Änderungen an Laufzeit oder Starter können ein vollständiges neues Paket erfordern.

### Eigene Daten sichern

Vor einem Rechnerwechsel oder dem Austausch des gesamten Pakets die Anwendung beenden und den Ordner **private** sichern. Windows: app/private; Linux: ~/tischtennis-anzeigetafel/private. Dieser Ordner kann Zugangsdaten enthalten. Bei einer neuen Installation nur den gesicherten private-Ordner an die passende Stelle zurückkopieren; Plattform und Version müssen zusammenpassen.

### Zugriff vom Laptop

127.0.0.1 bezeichnet immer den gerade benutzten Rechner. Die Anwendung ist absichtlich nicht direkt im WLAN veröffentlicht. Auf Linux ist Zugriff über einen SSH-Tunnel möglich; SSH-Zugang muss eingerichtet sein:

```sh
ssh -N -L 8081:127.0.0.1:8081 BENUTZER@RECHNERADRESSE
```

Das Terminal offen lassen; nach der Anmeldung ohne weitere Ausgabe zu warten ist normal. Dann auf dem Laptop http://127.0.0.1:8081/settings.html öffnen. Falls Port 8081 dort belegt ist, links 8082 verwenden und im Browser Port 8082 öffnen. BENUTZER und RECHNERADRESSE durch eure eigenen Werte ersetzen.

---

# 7. Wenn etwas nicht klappt

### Kein Spiel oder falscher Gegner

Gewählte Datenquelle und Zugang prüfen. Bei Web4Sport muss der Live-Spielbericht gestartet und über den Zugang erreichbar sein. Unter „Verbindung & Spielauswahl“ die Begegnung kontrollieren; gegebenenfalls die Auswahl zurücksetzen und erneut wählen. Bei Janova ID und aktive Geräte prüfen. Die Anzeige aktualisiert sich automatisch, sobald passende Daten vorliegen.

### „Nicht erreichbar“ oder keine aktuellen Daten

Internetverbindung, Datum und Uhrzeit des Rechners sowie den Quelldienst prüfen. In den Einstellungen „Reader neu verbinden“ verwenden. Danach den nächsten Abruf abwarten. Eine leere Spielanzeige bedeutet nicht automatisch einen Fehler im eigenen Rechner.

### Windows öffnet am falschen Bildschirm oder ein Zusatzfenster

Mit Beenden.cmd vollständig beenden. Bildschirm anschließen, Win + P > Erweitern und die Windows-Anordnung prüfen, dann erneut starten. Nicht mehrfach auf Starten.cmd klicken. Bei wiederholten kleinen flackernden Fenstern Version und Startpaket prüfen und den Fehler melden.

### Linux: Dienst oder Kiosk startet nicht

```sh
systemctl --user status anzeigetafel.service --no-pager
journalctl --user -u anzeigetafel.service -n 40 --no-pager
```

Installationspfad und virtuelle Umgebung prüfen. Ist die Seite manuell im Browser erreichbar, liegt das Problem eher beim grafischen Autostart, der Desktop-Anmeldung oder Chromium. Bei einem vorhandenen NUC kann der Dienst anders heißen; den tatsächlich eingerichteten Namen verwenden.

### Die Einstellungsseite scheint nichts zu übernehmen

„Einstellungen speichern“ wählen und auf eine Bestätigung achten. Falls ein Pflichtfeld ungültig ist, öffnet sich der betreffende Bereich. Nach einem Update oder beim Zugriff mit einem zweiten Browser bei Bedarf neu laden. Bestehende Logos bleiben erhalten, auch wenn beim Dateifeld „Keine ausgewählt“ steht.

### Unterstützung

Frank Fehrmann - frank.fehrmann@gmail.com - +49 174 6390530

Für eine Fehlermeldung hilfreich: Betriebssystem, angezeigte Version, Datenquelle und Screenshot ohne Zugangsdaten. Keine Passwörter oder privaten Konfigurationsdateien öffentlich auf GitHub einstellen.

Projekt und Downloads: https://github.com/DiskoKing/tischtennis-anzeigetafel

Die Windows-Version ist derzeit nicht mit einem öffentlich vertrauenswürdigen Herausgeberzertifikat signiert. macOS, Android und iOS sind keine zugesicherten Betriebsplattformen dieses Pakets.
