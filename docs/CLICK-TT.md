# myTischtennis / click-TT als Datenquelle

In **Einstellungen → Datenquelle** den Eintrag **myTischtennis / click-TT (Live-Ticker)** wählen. Den vollständigen öffentlichen Spielbericht-Link einfügen und speichern. Kein myTischtennis-Konto und keine Zugangsdaten erforderlich. Der Link wählt genau diese Begegnung; es gibt keine automatische Suche nach einem Vereinsnamen.

Beispiel: [TTC SR Hohenstein-Ernstthal – 1. FC Köln, 15.11.2026](https://www.mytischtennis.de/click-tt/DTTB/26--27/ligen/2._Bundesliga/gruppe/518220/spielbericht/15876082/TTC_SR_Hohenstein-Ernstthal-vs-1._FC_K%C3%B6ln).

Gesamtstand, Mannschafts- und Spielernamen, Wettbewerb, Sätze und verfügbare Zwischenpunkte werden übernommen. Die Detailansicht zeigt bis zu 1, 2 oder 3 bereits anhand von Zwischenständen erkennbare laufende Paarungen. Nach dem Ende zeigt die Detailansicht die letzten 1, 2 oder 3 abgeschlossenen Paarungen in Spielreihenfolge mit Satzständen und der Kennzeichnung „Beendet“. Die Kompaktansicht behält den Endstand. Vor dem ersten Punkt erscheint der Gesamtstand; ungespielte 0:0-Paarungen werden nicht als laufende Tische erfunden. Die Überschrift nennt die Spielpaarung, keine vermutete Tischzuordnung. Ohne Aufschlaginformation wird keine Aufschlagmarkierung angezeigt. Ein beendeter Satz wird nicht als laufender Punktestand des Folgesatzes verwendet.

Der Anbieter aktualisiert seinen öffentlichen Live-Endpunkt im Browser ungefähr alle **30 Sekunden**. Die Anzeigetafel verwendet denselben Abrufrhythmus, keine Punkt-für-Punkt-Echtzeitverbindung. Zur Darstellung kommt der jeweils veröffentlichte Stand. Ohne aktuelle Daten erscheint ein Quellenfehler; Netzwerkstatus und Quellenstatus bleiben getrennt. Bei einem Link-/Quellenwechsel werden alte Daten sofort verworfen, und verspätete Antworten des alten Readers werden nicht veröffentlicht.

## Technische Hinweise

Adapter: `public/support/clicktt.py`. Öffentlicher Lesepfad: `https://www.mytischtennis.de/api/meeting/{meetingId}/live`, wie vom öffentlichen Spielbericht eingebunden. Falls hierfür kein Datensatz vorliegt, wird der zugehörige öffentliche HTML-Spielbericht ausgewertet. Keine Ausführung von Website-JavaScript, kein Login, keine Cookies aus der Web4Sport-Sitzung, keine Werbung oder Tracker. Der Adapter akzeptiert ausschließlich passende HTTPS-Spielbericht-Links auf mytischtennis.de, baut API-Adressen auf einem festen Origin, folgt keinen Redirects und begrenzt die Antwortgröße. Personen-IDs und Vereinslogos werden nicht übernommen.

Dies ist eine unabhängige Anbindung an ein öffentliches, nicht versioniertes Webseitenformat. Änderungen beim Anbieter können Anpassungen erfordern. Es besteht keine Verbindung oder offizielle Partnerschaft zu myTischtennis, click-TT oder dem DTTB. Die Unterstützung gilt für öffentlich verfügbare Berichte in diesem Format, nicht pauschal für jedes Angebot jeder Bundesliga.

Tests verwenden einen auf notwendige öffentliche Spielinformationen reduzierten Datenstand des Beispielspiels vom 15.11.2026. Der Testbestand enthält keine Website-Sitzungsdaten und keine Personen-IDs. Geprüft werden Namen und Gesamtstand, aktive/ausstehende/beendete Einzel und Doppel, Satzwechsel, URL-/Redirect-Schutz, HTML-Fallback, Konfigurationspersistenz sowie die Abweisung alter Reader-Antworten.
