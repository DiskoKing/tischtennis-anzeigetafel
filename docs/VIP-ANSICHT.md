# VIP-Ansicht

Die VIP-Ansicht unter `/vip.html` zeigt den Mannschaftsstand, Spielfolge, zwei Paarungen und zwei optionale Kamerabilder. Die bisherige Demo-Adresse `/kamera-layout.html` bleibt ein Alias. Hallenanzeige und VIP-Ansicht können gleichzeitig mit derselben Datenquelle laufen.

## Kameraorientiertes Layout

Zwei große Kamerabilder stehen nebeneinander über den Spieldaten. Darunter liegen die Tischdetails außen, Gesamtstand und Spielfolge mittig. Satzergebnisse bleiben sichtbar; Ballpunkte erscheinen nur, wenn die Quelle sie liefert. Die Fußleiste zeigt bis zu fünf Sponsorenlogos gleichzeitig. Bei mehr Logos wechselt sie gruppenweise nach dem eingestellten Intervall. Deaktivierte Kameras und fehlende Daten werden ausdrücklich gekennzeichnet.

## Einstellungen

Unter **Einstellungen → VIP-Ansicht** die eigenen Farben, Kameras, Tischzuordnung und Fußleiste bearbeiten. **VIP-Einstellungen speichern** speichert nur diesen Bereich. Die normale Hallenkonfiguration wird dabei nicht geändert. Logo und Datenquelle werden gemeinsam verwendet.

- 21 getrennte Farben: Flächen, Rahmen, Trennlinien, Überschriften, Texte, Akzente, Heim/Gast, Siege/Niederlagen und Status. Bei der ersten Einrichtung dienen die normalen Vereinsfarben als Ausgangspunkt. Der Button „Vereinsfarben übernehmen“ überträgt Akzent-, Heim-/Sieg- und Hintergrundfarbe erneut in das Formular; anschließend speichern.
- Automatischer Titel aus dem Heimteam: ohne Endnummer oder mit I/1 „1. Mannschaft“, mit II/2 „2. Mannschaft“ usw. Keine Speicherung im einzelnen Browser mehr.
- Tischzuordnung: abwechselnd auf T1/T2, Starttisch wählbar; alternativ native Tischangaben der Quelle oder keine Tischangaben. click-TT und Web4Sport liefern keine sichere Tischzuordnung. Eine Regel ordnet die Partien zu, erkennt aber nicht automatisch, wo tatsächlich gespielt wird.
- Kamera 1 und 2 jeweils ein/aus, eigene Beschriftung, RTSP-/RTSPS-Adresse, Benutzername und Passwort. Zugangsdaten separat eintragen. Leeres Passwort behält das gespeicherte bei; Entfernen nur über das entsprechende Kontrollfeld. Passwörter werden nicht an Browser zurückgegeben.
- „Browserkompatibles H.264“ wandelt auf 1280×720 mit 15 Bildern/s um. Ohne diese Option wird das Original weitergereicht; Wiedergabe hängt dann von Codec, Auflösung und Browser ab. Beide Videos sind stumm, keine Aufzeichnung.
- Eigene Fußleiste: Website ein/aus, optional abweichender Website-Text, Uhr ein/aus, Höhe 4–15 %, Sponsoren ein/aus, Einleitung und Rotationszeit. Verwendet denselben Logo-Pool wie die normale Anzeige; deren Sponsoren-Schalter beeinflusst den VIP-Schalter nicht.

Farben und Fußleiste werden ohne Dienstneustart übernommen. Bei Änderungen der Kamerakonfiguration verbindet der separate Kameravermittler die Streams neu. Nach dem Ausschalten beider Kameras wird dieser Dienst gestoppt. Bei aktiviertem Preload bleiben freigegebene Kameras offen, auch wenn gerade keine VIP-Seite angezeigt wird; sie benötigen dann weiterhin Rechenleistung.

## Kameravermittler auf Linux/NUC installieren

Die Oberfläche und Farbanpassung benötigen keinen Kameravermittler. Die automatische Installation für RTSP ist zunächst auf **Linux x86_64 / NUC** beschränkt. Raspberry Pi und Windows benötigen einen gesonderten, noch nicht integrierten Installationsweg.

Im Projektverzeichnis als normaler Benutzer, in der bestehenden Python-Umgebung:

```sh
.venv/bin/python public/support/install_vip_gateway.py
```

Der Installer legt go2rtc v1.9.15 mit fester SHA-256-Prüfung und eine separate FFmpeg-Laufzeit unter `private/cameras` ab. Er verwendet keine globalen Python-Pakete und benötigt kein sudo. Danach Kameras in den VIP-Einstellungen speichern und „Kameras neu verbinden“ wählen. Der Benutzerdienst heißt `tt-anzeigetafel-cameras.service`. Bei der schon vorhandenen NUC-Demo werden die beiden vorhandenen Kamera-Adressen einmalig übernommen.

## Zugang und Datenschutz

Auf dem Hallenrechner funktioniert der lokale Zugang. Auf anderen Geräten zuerst über `/remote` mit der LAN-PIN anmelden, dann `/vip.html` auf demselben Host und Port öffnen. Für Videobilder gelten dieselbe LAN-Freigabe, PIN-Sitzung und Origin-Prüfung wie für die Anzeigetafel. HTTP im lokalen Netz ist unverschlüsselt; keine Router-Portfreigabe verwenden.

RTSP-Adressen und Zugangsdaten liegen in der privaten Instanzkonfiguration. Kamerapasswörter fehlen in sämtlichen Konfigurationsantworten. Konfigurationszugriff zeigt angemeldeten Benutzern die RTSP-Adressen und Benutzernamen zur Bearbeitung. Der lokale Vermittler ist nur über 127.0.0.1 erreichbar; sein Verwaltungszugang wird nicht über die Anzeigetafel weitergeleitet. Der Browser spielt zwei fest zugeordnete Streamnamen über authentifizierte WebSockets ab. Maximal acht gleichzeitige Videotunnel.

## Datenquellen

click-TT zeigt gelieferte Zwischenpunkte und nach dem Ende die letzten beiden abgeschlossenen Paarungen. Web4Sport zeigt Satzstände und die nächsten offenen bzw. letzten abgeschlossenen Paarungen, keine erfundenen Ballpunkte. Janova übernimmt aktive Zählgeräte; eine vollständige historische Spielfolge ist dort nicht zugesichert. Im manuellen Modus ist nur der Mannschaftsstand verfügbar. Die VIP-Auswahl von zwei Partien ist unabhängig von der Anzahl in der normalen Detailansicht.

Video und Ergebnismeldungen haben unterschiedliche Verzögerungen. Kameraausfall unterbricht die Ergebnisanzeige nicht. LIVE erscheint nur bei offener Verbindung und voranschreitender Videowiedergabe; nach Ausfällen versucht der Player eine Wiederverbindung.
