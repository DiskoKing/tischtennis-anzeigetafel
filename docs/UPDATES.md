# Ein gemeinsamer Updatekanal

GitHub ist die gemeinsame Quelle. main ist der Entwicklungsstand. Nur bewusst freigegebene v-Tags erzeugen Releases für die Praxis. Es gibt genau einen Updatekanal.

Die Pakete für Linux und Windows werden aus demselben Commit gebaut und enthalten dieselbe Anzeigelogik. Plattformstarter und Laufzeitpakete unterscheiden sich. Zugangsdaten und eigene Uploads bleiben lokal außerhalb der austauschbaren Programmdateien.

Geplant für den Aktualisieren-Knopf: Release-Metadaten laden, passende Plattform auswählen, Herkunftssignatur und Hash prüfen, Release Notes zeigen, alte Version sichern, kontrolliert stoppen und umschalten. Bei fehlgeschlagenem Start zur vorherigen Version zurückkehren. Windows darf die gerade laufende Python-Laufzeit nicht überschreiben; dafür wird ein separater Updatehelfer benötigt.

Noch offen: Herausgeberschlüssel und Signaturprozess, Updatehelfer, Rückrollprüfung und Migration der vorhandenen Praxisinstallation. Der Aktualisieren-Knopf ist noch nicht enthalten. Prüfsummen allein ersetzen keinen Herkunftsnachweis. Ein Git-Push aktualisiert keine ausgerollte Instanz.
