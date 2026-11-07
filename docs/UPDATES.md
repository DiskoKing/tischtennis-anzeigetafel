# Ein gemeinsamer Updatekanal

GitHub ist die gemeinsame Quelle. Eine bewusste Änderung von VERSION auf main erzeugt nach erfolgreichen Tests ein Release mit passendem v-Tag. Andere Änderungen auf main veröffentlichen kein Release. Es gibt genau einen Updatekanal.

## Oberfläche ab 2.2.0

Einstellungen → Version & Updates → Nach Updates suchen. Die Anwendung zeigt installierte und verfügbare Version sowie Release Notes an. Jetzt aktualisieren verlangt eine ausdrückliche Bestätigung, prüft das gemeinsame Anwendungspaket, sichert Programm und Konfiguration und startet neu. Eine fehlgeschlagene Startprüfung stellt den vorherigen Code und die Konfiguration wieder her. Eigene Uploads unter private/ werden nicht ersetzt. Sicherungen liegen unter private/updates.

Windows: unterstützt der portable Starter mit app/private. Linux: unterstützt die Benutzer-Dienste ttsv-scoreboard-v2.service und anzeigetafel.service, wenn sie genau den laufenden Serverprozess verwalten. Andere Startarten bekommen einen Link zum vollständigen Release. Einmalig muss eine ältere Installation manuell auf 2.2.0 umgestellt werden, da ihr der Updatehelfer fehlt.

## Grenzen und Vertrauensmodell

Downloads beginnen ausschließlich unter github.com/DiskoKing/tischtennis-anzeigetafel/releases/download. Release-Metadaten kommen von der GitHub-API über HTTPS. SHA-256 muss mit SHA256SUMS und, sofern vorhanden, dem GitHub-Asset-Digest übereinstimmen. Vertrauen besteht damit in das GitHub-Konto, dessen Berechtigungen und HTTPS. Eine zusätzliche unabhängige Herausgebersignatur ist noch nicht eingerichtet; Prüfsummen allein wären kein Herkunftsnachweis.

Zip-Pfade, Dateibereiche, Symlinks und Größen werden geprüft. private/, runtime/ und Browserdaten gehören nicht zum Updatepaket. Änderungen an den installierten Python-Abhängigkeiten oder am Windows-Starter erfordern das vollständige neue Plattformpaket; der Updatehelfer lehnt solche Updates ab.

Windows nutzt einen separaten, unsichtbaren Helfer. Linux startet den Helfer in einer eigenen systemd-Benutzerunit, damit er das Stoppen der App überlebt. Updatefunktion und Rückrollen wurden mit einem isolierten echten Linux-Dienst getestet; Windows besitzt zusätzlich Tests für Paketprüfung und Starterlogik. Ein Versionswechsel ist kein Hot-Update: die Anzeige wird kurz unterbrochen.


## Kontoumbenennung zu DiskoKing

Versionen bis 2.2.12 beschränken Download-Adressen noch auf den alten Kontonamen. Für diese Installationen einmalig `python tools/migrate_github_owner.py --root APP-ORDNER` ausführen und die Anwendung neu starten. Das Hilfsskript ändert ausschließlich die Repository-Konstante in updater.py und sichert die bisherige Datei. Konfiguration und Uploads bleiben unangetastet. Danach regulär über Version & Updates aktualisieren. Bei Windows-USB ist APP-ORDNER der Paketordner mit dem Unterordner app.
