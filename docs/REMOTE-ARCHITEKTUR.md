# Remote Control v1.0 – Implementierung ab Version 2.4.0

## Analyse und Entscheidungen

- Ein `ThreadingHTTPServer` aus `server.py` bleibt der einzige Server. Linux/NUC/Raspi starten ihn über den vorhandenen systemd-Benutzerdienst. Der Windows-Starter verwendet dieselbe Serverfabrik und weiterhin seinen bisherigen Browser-/Monitorstart.
- `App.manual_action`, `validate_update`, `atomic_json` und die bestehende RLock bleiben die einzige Geschäftslogik. Der Spielstand einschließlich Retry-IDs ist in `private/manual-state.json` gespeichert. Reset-Retries mit der alten Spiel-ID werden zusätzlich wiedererkannt. Ältere normale Eingaben werden weiterhin über das begrenzte Fenster der letzten 256 Ereignisse dedupliziert.
- `/remote` verwendet die vorhandenen manuellen Bedienelemente und bettet die vorhandene responsive Einstellungsseite ein. Keine zweite Konfigurationsimplementierung; keine CDN-Ressourcen, kein Service Worker und kein Offline-Schreibmodus.
- Live-Synchronisierung: `/api/system` liefert eine Instanz-/Revisionskennung. Browser fragen sie sekündlich ab und aktualisieren Konfiguration und Anzeige nur bei Änderungen. Manuelle Bedienelemente fragen den aktuellen Stand weiterhin sekündlich ab. SSE wurde für v1 bewusst nicht verwendet: offene Verbindungen würden in dieser Architektur pro Client dauerhaft einen Thread und zusätzliche Sitzungs-/Abbruchverwaltung benötigen. Typische Übernahmezeit: etwa eine Sekunde; kein Echtzeit-/Latenzversprechen bei Netzproblemen.
- Netzwerkstatus wird separat und im Hintergrund ermittelt, zehn Sekunden zwischengespeichert und nie als Ersatz für den Datenquellenstatus verwendet. Linux: `ip -j`, optional NetworkManager ohne Rescan. Windows: strukturierte PowerShell-Ausgabe und Native WLAN API. Unbekannte/gesperrte Funktionen liefern `unknown`, `unsupported` oder `null`, keinen erfundenen Wert. Kein Internetprobe-Request.

## Zugriff und Sicherheitsgrenzen

Standardbindung bleibt `127.0.0.1`. Die lokale Einstellungsseite kann in `private/remote-access.json` eine ausdrückliche Freigabe und eine Bind-Adresse speichern. Die PIN wird mit PBKDF2-HMAC-SHA256, 600.000 Iterationen und zufälligem 128-Bit-Salt abgelegt. Keine eigenen kryptographischen Primitive. PIN-Einrichtung und Freigabe sind nur von diesem Rechner / per SSH-Tunnel möglich. Keine automatische Firewalländerung.

LAN-Clients benötigen eine zufällige Sitzung mit eigener CSRF-Kennung. Cookie: HttpOnly, SameSite=Strict, Pfad `/`, acht Stunden absolute Gültigkeit. Login rotiert die Sitzung; Logout, PIN-Änderung, Änderung der Freigabe und Server-Neustart widerrufen sie. Sitzungen existieren nur im Arbeitsspeicher; Token werden serverseitig gehasht gehalten. Fehlversuche sind pro Quelladresse auf fünf pro Minute und insgesamt auf 30 pro Minute begrenzt. Es gibt maximal 64 Sitzungen und 256 Rate-Limit-Adresseneinträge. Die PIN-Prüfung ist synchronisiert und die Größe der Eingabe begrenzt.

Vertrauen in den lokalen Zugang basiert auf der tatsächlichen Peer-Adresse, nicht allein auf dem manipulierbaren Host-Header. LAN-Hosts müssen zu den lokal ermittelten IPv4-Adressen gehören. Origin muss bei LAN-Schreibzugriffen exakt passen; eine CSRF-Kennung allein genügt nicht. Alle LAN-Lese-APIs außer dem Sitzungsaufbau sind ebenfalls geschützt. Browser-/Status-APIs liefern keine Passwörter, PIN-Hashes oder Sitzungstoken. LAN-Konfigurationen maskieren zusätzlich Benutzername und Janova-ID. Leere maskierte Felder behalten gespeicherte Werte.

**HTTP bleibt unverschlüsselt.** Die PIN und Daten können im lokalen Netz mitgelesen werden. Das Cookie kann über HTTP nicht mit `Secure` abgesichert werden. Deshalb nur vertrauenswürdiges LAN/WLAN, keine Router-Portfreigabe, keine öffentliche Bereitstellung und keine Verwendung wichtiger Konto-PINs. Dies ist keine gehärtete Internet-Hosting-Lösung. Lokale Prozesse und angemeldete Benutzer am Gerät bleiben wie bisher vertrauenswürdig und können die lokale Bedienung ohne PIN nutzen. Bei Bedarf ist statt LAN-HTTP ein SSH-Tunnel die bisherige Alternative.

## API-Ergänzungen

| Endpoint | Zweck / Zugriff |
| --- | --- |
| `GET /remote` | Mobile Oberfläche, Anmeldung erforderlich für Daten |
| `GET /api/session` | Lokaler CSRF-Token oder isolierte Remote-Sitzung |
| `POST /api/remote/login` | PIN-Prüfung, Origin + vorläufige CSRF-Sitzung |
| `POST /api/remote/logout` | Sitzung widerrufen |
| `GET/POST /api/remote/access` | Freigabe/PIN/Bind-Adresse, nur lokal |
| `GET /api/system` | Netzwerk, Datenquelle, letzte erfolgreiche Aktualisierung, Revision |
| `POST /api/manual`, `/api/config`, Uploads usw. | Bestehende APIs, zusätzlich Remote-Sitzung erforderlich |

Die Python-Adapter liegen unter `public/support`, damit auch bestehende Updatehelfer sie mit ihrem erlaubten `public`-Dateibaum ausliefern können. Python-Dateien werden vom HTTP-Handler nicht als statische Dateien ausgeliefert. Private Daten bleiben außerhalb des öffentlichen Dateibaums.

## QR-Einstieg und Startbildschirm

`GET /api/remote/pairing` liefert für lokale oder angemeldete Clients ausschließlich die aktuell erreichbaren Remote-URLs. `GET /api/remote/qr.svg?ip=…` erzeugt nur für eine aktuell erlaubte IP ein QR-SVG; beliebige URLs oder veraltete Adressen werden abgewiesen. Keine PIN und keine externen QR-Dienste. Der MIT-lizenzierte Encoder qrcodegen 1.8.0 (Project Nayuki) wird unverändert und mit Lizenzheader lokal mitgeliefert. Alle QR-Codes haben eine weiße Ruhezone und mittlere Fehlerkorrektur. Netzwerkcache plus UI-Abfrage ergeben eine Aktualisierung innerhalb ungefähr 15 Sekunden.

Kiosk und lokale Einstellungen verwenden dieselbe QR-Komponente. Zusätzlich erlaubt die Host-Prüfung ausschließlich den eigenen, validierten `.local`-Gerätenamen. Dieser Name wird als netzabhängige Komfortoption angeboten; er ersetzt die aktuelle IP nicht und löst keine automatische Router-, Hostnamen- oder mDNS-Konfiguration aus.

`remote.webmanifest` und lokale PNG-Symbole ergänzen die Startbildschirm-Verknüpfung. Kein Service Worker und keine Offline-Schreibwarteschlange. Auf HTTP wird eine vollständige PWA-Installationsfreigabe nicht versprochen; der Browser kann eine Verknüpfung anbieten. Siehe [MDN: PWA-Installierbarkeit](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable). Bei neuer IP/Port-Adresse erneut scannen bzw. den gespeicherten Link ersetzen.

## Vorbereitung späterer WLAN-Einrichtung

`NetworkStatus` ist die plattformabhängige, ausschließlich lesende Grenze. `wifiSetup.supported=false` und `hotspotActive=false` sind explizit. Spätere Scan-/Connect-/Hotspot-Funktionen benötigen einen getrennten berechtigten Plattformadapter, zusätzliche Authentifizierung/Bestätigung und einen eigenen Sicherheitsentwurf. Diese Version implementiert keine WLAN-Änderungen und keinen automatischen Hotspot.

## Veröffentlichung und praktische Abnahme

Veröffentlicht mit Version 2.4.0. CI und der bestehende Release-Testschritt umfassen die neuen Tests. Linux- und Updatepakete übernehmen die Adapter über `public`; Windows benötigt wegen der geänderten Starterfabrik bei der ersten Auslieferung ein vollständiges neues Paket. Ein alter Windows-Updater lehnt abweichende Starter-Prüfsummen wie bisher ab.

Der LAN-Zugriff und die Dock-Zählung wurden am NUC im Zielnetz praktisch geprüft. Bei anderen Geräten den LAN-Zugriff von einem echten Smartphone erneut testen. Die lokale Browserprüfung und automatisierten Plattformadaptertests ersetzen nicht diesen Gerätetest, insbesondere bei WLAN-Rechten, Firewall und Access-Point-Client-Isolation.

Technische Primärquellen: [Python PBKDF2](https://docs.python.org/3/library/hashlib.html#hashlib.pbkdf2_hmac), [ThreadingHTTPServer](https://docs.python.org/3/library/http.server.html#http.server.ThreadingHTTPServer), [Windows WLAN-Verbindungsdaten](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_connection_attributes), [Windows WLAN-Signalqualität](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_association_attributes).