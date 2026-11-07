# Version 2.2.13 – neue GitHub-Adresse

- Projekt und Update-Kanal verwenden jetzt DiskoKing/tischtennis-anzeigetafel.
- Vorhandene Versionen bis 2.2.12 benötigen einmalig die Umstellung der Update-Adresse, weil der bisherige Updater Downloads auf den alten Repository-Pfad beschränkt.
- Konfiguration, Zugangsdaten und Uploads bleiben unverändert.

# Version 2.2.12 – Anzahl der Web4Sport-Partien wählen

- Unter Ansicht & Wechsel lassen sich für die Web4Sport-Detailansicht 1, 2 oder 3 Partien wählen. Standard: 2.
- Angezeigt werden die nächsten offenen Paarungen in Spielreihenfolge. Sind weniger offen, werden entsprechend weniger angezeigt.
- Janova bleibt dynamisch; der Web4Sport-Regler erscheint nur bei gewählter Web4Sport-Datenquelle.

Über Version & Updates installierbar.

# Version 2.2.11 – Vereinslogo beim Quellenwechsel erhalten

- Die Kompaktansicht blendet die neutrale Logoansicht nicht mehr aus.
- Nach einem Wechsel der Datenquelle bleibt das Vereinslogo auch bei verbundener Quelle ohne gestartetes Spiel sichtbar.

Über Version & Updates installierbar.

# Version 2.2.10 – konfigurierbare Fußleiste

- Unter Ansicht & Wechsel lässt sich die Höhe der Fußleiste von 5 bis 15 % der Bildschirmhöhe einstellen. Standard: 8,5 %.
- Sponsorenlogos, Einleitung, Homepage und Uhr skalieren mit. Der Statushinweis bleibt oberhalb der Fußleiste.
- Vorhandene Konfigurationen übernehmen automatisch die bisherige Standardhöhe.

Über Version & Updates installierbar.

# Version 2.2.9 – alle Einstellungsbereiche gemeinsam schalten

- Neben Einstellungen speichern können alle Bereiche gemeinsam auf- oder zugeklappt werden.
- Einzelne Bereiche bleiben wie gewohnt separat bedienbar; der Zustand bleibt während der Sitzung erhalten.

Über Version & Updates installierbar.

# Version 2.2.8 – einheitlicher Wartehinweis

- Ohne gestartetes Spiel nennt der Hinweis die gewählte Datenquelle: Janova oder TischtennisLive/Web4Sport.
- Bei Janova bleibt der Hinweis ohne Spiel ebenfalls sichtbar.

Über Version & Updates installierbar.

# Version 2.2.7 – aufgeräumte Oberfläche

- Auf der Anzeigetafel öffnet ein einzelnes Zahnrad die Einstellungen; die Version steht weiterhin in den Einstellungen.
- Die Vereinsbibliothek entfällt aus den Einstellungen. Eigene Logos können weiterhin hochgeladen werden; gespeicherte Logos bleiben erhalten.

Über Version & Updates installierbar. Laufzeit und Windows-Starter bleiben unverändert.

# Version 2.2.6 – dezente, lesbare Statusmeldung

- Die große Meldungsbox in der Mitte entfällt. Das Vereinslogo bleibt frei sichtbar.
- Warte- und Fehlermeldungen erscheinen gut lesbar oberhalb der Fußzeile, ohne Uhr oder Sponsoren zu überlagern.
- Bei mehreren Begegnungen verweist der Hinweis auf die Spielauswahl in den Einstellungen.
- Statusmeldungen werden auch nach einer zuvor erfolgreichen Verbindung wieder sichtbar.

Über Version & Updates installierbar. Laufzeit und Windows-Starter bleiben unverändert.

# Version 2.2.5 – transparente Sponsorenlogos

- Die feste weiße Hintergrundfläche hinter Sponsorenlogos entfällt auf der Anzeigetafel und in der Logoübersicht der Einstellungen.
- Transparente PNG-, GIF- und WebP-Bereiche zeigen den jeweiligen Hintergrund. Die hochgeladenen Originaldateien bleiben unverändert; ein erneuter Upload ist nicht nötig.

Über Version & Updates installierbar. Laufzeit und Windows-Starter bleiben unverändert.

# Version 2.2.4 – Loginbereich passend zur Datenquelle

- Die Einstellungen zeigen nur Janova oder TischtennisLive/Web4Sport entsprechend der gewählten Datenquelle.
- Beim Umschalten bleiben eingegebene und gespeicherte Werte erhalten.
- Inaktive Loginfelder werden ausgeblendet und von der Browservalidierung ausgenommen. Die Auswahl wird wie bisher mit Einstellungen speichern übernommen.

Über Version & Updates installierbar. Laufzeit und Windows-Starter bleiben unverändert.

# Version 2.2.3 – kompakte, aufklappbare Einstellungen

- Flacher Kopfbereich statt großer Werbeüberschrift; im Overlay entfällt die doppelte Überschrift.
- Alle sieben Bereiche lassen sich mit Maus und Tastatur auf- und zuklappen. Verein & Design und Designvorschau sind zunächst geöffnet.
- Geöffnete Bereiche bleiben innerhalb der Browsersitzung erhalten.
- Einstellungen speichern bleibt am unteren Fensterrand erreichbar, auch bei geschlossenen Kategorien.
- Bei ungültigen Pflichtfeldern öffnet sich der betreffende Bereich automatisch.
- Die mitgelieferten SVG-Standardgrafiken und der Logo-Katalog werden jetzt korrekt vom lokalen Webserver ausgeliefert.

Über Version & Updates installierbar. Laufzeit und Windows-Starter bleiben unverändert.

# Version 2.2.2 – flackerndes Konsolenfenster bei Janova behoben

- Der Janova-Reader startete für seine alte Konsolenanzeige einmal pro Sekunde eine Shell zum Ausführen von cls. Dieser Aufruf ist vollständig entfernt.
- Ohne interaktives Terminal wird keine Konsolen-Statusanzeige erzeugt; auch pythonw ohne stdout wird unterstützt.
- Interaktive Statusausgabe nutzt Terminalsequenzen statt eines Shellprozesses.
- Regressionstests decken Hintergrundbetrieb, pythonw und interaktiven Betrieb ab.

Über Version & Updates aus 2.2.0 oder 2.2.1 installierbar. Windows-Starter und Laufzeit bleiben unverändert.

# Version 2.2.1 – Original-Hintergrundbild offiziell enthalten

- Das vom Ersteller generierte und zur Auslieferung freigegebene Originalbild aus Version 1 wird unverändert mitgeliefert.
- Einstellungen → Hintergrund → Originalbild aus Version 1. Abdunklung bleibt einstellbar.
- CSS-Design, neutraler Hintergrund und eigene Uploads bleiben als Optionen erhalten. Bestehende Einstellungen werden nicht umgestellt.
- Herkunft und Dateiprüfsumme sind unter public/assets/CREDITS.md dokumentiert.

Dieses Update ist über Version & Updates aus 2.2.0 installierbar; Laufzeit und Windows-Starter bleiben unverändert.

# Version 2.2.0 – Versionsanzeige und Updates in der Oberfläche

- Angezeigte Versionsnummer stammt aus der installierten VERSION-Datei.
- Einstellungen: Nach Updates suchen, Release Notes und Jetzt aktualisieren.
- Ein gemeinsames Anwendungspaket für Windows und NUC/Linux. Downloads ausschließlich aus diesem GitHub-Repository, mit SHA-256-Prüfung.
- Programm- und Konfigurationssicherung vor Austausch; eigene Uploads bleiben unangetastet. Neustartprüfung mit Rücksicherung bei Fehlern.
- Neue Laufzeit-Abhängigkeiten oder Änderungen am Windows-Starter erfordern weiterhin das vollständige Paket.

Für bestehende Versionen 2.1.x ist einmalig ein manueller Wechsel auf 2.2.0 nötig. Erst diese Version enthält den Updatehelfer. Die Updatequelle wird über GitHub und HTTPS vertraut; eine zusätzliche unabhängige Herausgebersignatur ist noch nicht eingerichtet.

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
