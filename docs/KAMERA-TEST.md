# Kameraansicht – laufender NUC-Test

Historischer Aufbau der Kamerademo. Die integrierte, konfigurierbare Fassung ist jetzt in [VIP-ANSICHT.md](VIP-ANSICHT.md) beschrieben; sie ist weiterhin unveröffentlicht.

Die zusätzliche Seite `/kamera-layout.html` zeigt vorhandene Spieldaten und zwei stumme Kamerabilder. Sie ist eine noch unveröffentlichte Erweiterung; die normale Ansicht und ihr Kiosk-Autostart bleiben unverändert.

## Datenfluss

RTSP-Kamera → optionaler lokaler go2rtc-Dienst → PIN-geschützter WebSocket-Tunnel der Anzeigetafel → VideoRTC/MSE im Browser.

go2rtc v1.9.15 wird separat unter `private/cameras` installiert. Die freigegebene Linux-amd64-Datei hat SHA-256 `20b46c6910734cb05ecefb234066f36868ff19b42ba1418a7a32e13a3e035712`. Browserplayer und MIT-Lizenz liegen unter `public/vendor/go2rtc`.

Der systemd-Benutzerdienst heißt `tt-anzeigetafel-cameras.service`. HTTP-Verwaltung (1984) und RTSP-Vermittlung (8554) sind ausschließlich an 127.0.0.1 gebunden. WebRTC-Ports sind deaktiviert. Für diesen Test hält der Dienst beide Videoströme per Preload offen, damit das Neuladen einer Seite nicht erneut die langsam startende RTSP-Verbindung aufbauen muss. Daher verbrauchen die beiden FFmpeg-Prozesse auch ohne geöffneten Player Rechenleistung. Zum Beenden: `systemctl --user stop tt-anzeigetafel-cameras.service`.

Die beiden festen Gatewaynamen heißen `table1` und `table2`. Browser erhalten keine RTSP-Adresse und keine Gateway-Verwaltungsrechte. URLs stehen nur in `private/cameras/go2rtc.json`; diese Datei gehört nicht ins Repository. Die Anzeigetafel erlaubt nur `/api/cameras/1/ws` und `/api/cameras/2/ws`. Es gibt keine frei wählbare Proxy-Zieladresse.

## Aktuelle Testprofile

- Kamera 1: H.264, 3840×2160 am Eingang, für den Test auf H.264, 1280×720, 15 Bilder/s reduziert. Die unveränderte 4K-Weitergabe stockte in der Browserprüfung nach einer Wiederverbindung.
- Kamera 2: H.265-Eingang, für die Browserwiedergabe mit FFmpeg nach H.264, 1280×720, 15 Bildern/s umgewandelt. Zwei Encoderthreads; keine bestätigte Hardwarekodierung.
- Beide Videos werden stumm und ohne Aufnahme abgespielt. Dasselbe Kameragerät kann zwei verschiedene Streamprofile liefern; die Beschriftung ist keine automatische Erkennung zweier physischer Kameras.

## Zugriff und Ausfall

Am Gerät ist der lokale Zugriff verfügbar. Über LAN gelten dieselbe Freigabe und PIN-Sitzung wie für die Spieldaten. Ein Dienstneustart widerruft bestehende PIN-Sitzungen; gegebenenfalls neu anmelden. Der WebSocket-Handshake prüft Origin, Upgrade, Version und Schlüssel. Maximal acht Videotunnel gleichzeitig. LAN-Sitzungen werden während der Verbindung regelmäßig erneut geprüft.

Die Anzeige setzt LIVE erst nach voranschreitender Videowiedergabe. Nach einem Ausfall verschwindet die LIVE-Markierung und der Player verbindet automatisch neu. Ein Videoausfall ändert weder die Spieldaten noch den Spielstand. Quellen- und Videoverzögerung sind unabhängig; es gibt keine zugesicherte Synchronisierung von Ballwechsel und Punktestand.

## Prüfergebnis

Im Browser über den bestehenden SSH-Tunnel wurden beide H.264-Bilder gleichzeitig mit voranschreitender Wiedergabe bestätigt. Ein Stop/Start des Kameradienstes wurde getestet; die Spieldaten blieben verfügbar. Die endgültige Wiedergabe und Hardwarebeschleunigung des am TV laufenden Firefox sind noch am TV zu kontrollieren.

Die anschließende VIP-Integration ergänzt Kameraeinstellungen und einen Installer für Linux/NUC x86_64. Ein plattformübergreifender Kamera-Installer für Windows und Raspberry Pi ist noch offen. Der Linux-Aufbau nutzt zusätzlich imageio-ffmpeg 0.6.0 als separat installierte FFmpeg-Laufzeit; deren Lizenzinformationen bleiben im privaten Werkzeugverzeichnis erhalten.

Referenzen: https://go2rtc.org/internal/api/ · https://go2rtc.org/internal/mp4/ · https://go2rtc.org/internal/ffmpeg/
