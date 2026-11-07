# Linux / NUC

Die ausführliche Neueinrichtung inklusive Dienst und Chromium-Kiosk steht in docs/ANLEITUNG.md, docs/ANLEITUNG.html und docs/TT-Anzeigetafel-Anleitung.pdf im Projektordner. Bestehende Praxisinstallationen nicht nochmals mit einem zweiten Dienst einrichten.

Repository bzw. Linux-Paket unter ~/tischtennis-anzeigetafel ablegen. Virtuelle Umgebung und Abhängigkeiten wie im Haupt-README einrichten. Die Beispiel-Unit anzeigetafel.service kann unter ~/.config/systemd/user/ installiert und mit systemctl --user daemon-reload und systemctl --user enable --now anzeigetafel gestartet werden. Pfade bei abweichendem Installationsordner anpassen.

Für einen Kioskbrowser Firefox mit http://127.0.0.1:8081/spiele.html starten. Die vorhandene NUC-Installation hat eigene Dienst- und Autostartnamen; diese Vorlage nicht zusätzlich zum laufenden Dienst installieren. Eine spätere Migration muss diese Unterschiede berücksichtigen.
