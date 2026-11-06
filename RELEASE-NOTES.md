# Version 2.1.1 – Windows-Fensterstart korrigiert

- Starten öffnet genau die Anzeigetafel; Einstellungen werden bei Bedarf über Einstellungen.cmd oder das Overlay geöffnet.
- Browser und Janova-Reader werden unter Windows ausdrücklich ohne Konsolenfenster gestartet.
- Ein neues Browserprofil pro Sitzung verhindert die Wiederherstellung zusätzlicher alter Fenster. Die Vereinskonfiguration bleibt in app/private erhalten.
- Bereits geöffnete Einstellungsfenster werden wieder in den Vordergrund geholt, statt weitere zu öffnen.
- Tests für den ersten Fensterstart, unsichtbare Hintergrundprozesse und die Wiederverwendung des Einstellungsfensters ergänzt.

Hinweis: Der integrierte Aktualisieren-Knopf ist weiterhin noch nicht enthalten. Vor einem manuellen Wechsel die bisherige Instanz mit Beenden.cmd schließen und app/private in das neue Paket übernehmen.

# Version 2.1.0 – gemeinsamer öffentlicher Projektstand

- Gemeinsamer Anwendungscode für Linux/NUC und Windows-USB.
- Konfigurierbares Vereinsdesign, Datenquellen, Ansichtswechsel und Sponsoren.
- Optionale Janova-Anmeldung zur Ermittlung der Konto-ID.
- Windows-Starter mit Zweitbildschirm-Auswahl und Beenden-Funktion.
- Vereinslogo-Auswahl mit Suche; öffentlich mit leerem Katalog.
- Neutrale SVG-Standardgrafiken statt Vereinslogos und früherem Hintergrundfoto.
- Windows-/Linux-Tests und plattformspezifische Build-Skripte.

Bekannte Einschränkungen: Der integrierte Aktualisieren-Knopf fehlt noch. Die Vollbildplatzierung der Windows-Ausgabe muss auf dem jeweiligen Zielrechner praktisch bestätigt werden. Die Janova-Anmeldung hängt von deren öffentlicher Web-App-Konfiguration ab. Eine allgemeine Freigabe durch Virenscanner ist nicht gewährleistet.

Die vorhandene NUC-Version 2.0 bleibt als gesichertes Archiv erhalten. Diese Quellcode-Veröffentlichung stellt keine bestehende Installation automatisch um.
