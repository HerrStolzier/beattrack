# Roadmap und Umsetzungsplan

Stand: 2026-09-16 · **Umsetzung bis zum Endziel beauftragt; Ausbau bleibt an die Nachweise der vorherigen Etappen gebunden.**

Grundlage: [Bestandsaufnahme](status-2026-09-15.md). Die bisherigen PLAN-Dateien sind historische Entwürfe. Reihenfolge nach Nutzerwirkung, Datenintegrität und Betriebsrisiko; keine verbindlichen Termine ohne Diagnose und Umfangsschätzung.

## Bestätigtes langfristiges Endziel

Am 16.09.2026 bestätigt: **Beattrack findet zu einem Lieblingssong zuverlässig unbekannte, hörbar ähnliche Musik – mit geprüftem Nutzen und bezahlbarem Betrieb.** Das ist das Produktziel, keine Zusage universeller Treffer für jeden Song. Unterstützter Katalog, Audiozugang und nachgewiesene musikalische Bereiche bestimmen die erreichbare Abdeckung. Fehlende passende Musik darf als solche sichtbar werden.

## Weg vom Machbarkeitstest zum nutzbaren Produkt

Die Umsetzung ist seit 16.09. beauftragt. Keine Etappe ist bereits als erreicht markiert. Der detaillierte Versuch P0–P4 bleibt Voraussetzung; Quellenprüfung und technische Vorbereitung laufen. Siehe [Umsetzungsnachweis](retrieval-progress-2026-09-16.md).

| Etappe | Ergebnis | Voraussetzung und Abnahme |
|---|---|---|
| E1 · Grundlage | Zulässig nutzbarer Audiobestand, positive und schwierige negative Beispiele | P0/P1: Quellen und Verarbeitung geklärt; Entwicklung und Gegenprobe getrennt |
| E2 · Klangähnlichkeit | Ein Verfahren findet hörbar passende Musik auf unbenutzten Referenzen | P2/P3: unabhängige Suche, verdeckte Hörurteile, vorher festgelegte Nutzenschwelle; bei Scheitern begrenzte Diagnose statt automatischem Training |
| E3 · Katalogtauglichkeit | Vorteil bleibt in einem größeren, repräsentativeren Bestand erhalten | Nicht nur eingestreute Positive; Abdeckung, Fehlertypen und unbekannte Entdeckungen je musikalischem Bereich messen; Modell-/Datenversionen und zulässige Quellen dokumentieren |
| E4 · Durchgängiges Produkt | Lieblingssong eingeben → Aufnahme wählen → ähnliche Musik anhören → Fund merken | R2/R4/R6: reale Benutzerwege auf Desktop und Mobilgeräten prüfen, Audioausfälle und Bestandslücken verständlich behandeln; Scores nicht als unbewiesene Gewissheit darstellen |
| E5 · Bezahlbarer, stabiler Betrieb | Nachvollziehbar aktualisierter Katalog und zuverlässige Suche | R1/R7/R8: Analysezeit, Antwortzeit, Last, Speicher und laufende Kosten messen; Budget und Betriebsgrenzen vor Ausbau festlegen; Wiederherstellung und Rückweg testen; Live-Freigabe einholen |
| E6 · Dauerhafter Nutzen | Wiederholbar unbekannte, passende und merkenswerte Funde im Alltag | Über mehrere Sitzungen und frische Referenzen bewerten; bekannte Titel getrennt erfassen; Rückschritte vor Modellwechsel erkennen; zusätzliche Hörende nötig, bevor allgemeine Nutzerqualität behauptet wird |

**Endabnahme:** E3–E6 gemeinsam belegt: musikalischer Nutzen in dokumentiertem Umfang, funktionierender realer Such-/Hörweg, wiederholte Entdeckungen und gemessener Betrieb innerhalb des vereinbarten Budgets. Konkrete Qualitäts-, Latenz- und Kostengrenzen werden vor den jeweiligen Versuchen festgelegt; derzeit keine erfundenen Zahlen oder Termine.

**Wenn Grenzen bleiben:** Quellen oder Katalog gezielt erweitern, sofern erlaubt und sinnvoll; andernfalls den belegten Umfang offen begrenzen. Kein erzwungenes Auffüllen mit unpassenden Treffern. Training bleibt ein optionaler, evidenzabhängiger Zweig. Konten, Bezahlung, Genre-Vollständigkeit und ein selbst trainiertes Grundmodell sind keine Voraussetzung dieses Endziels.

## Aktueller Schwerpunkt: musikalische Machbarkeit

Die bestätigte Vision und der nach unabhängigem Review korrigierte Plan stehen im [Hörvergleichsplan](listening-feasibility.md). Nächste Stufen: **P0 Audioquellen → P1 positive Beispiele und getrennte Bestände → P2 eigenständige Modellsuche → P3 verdeckte Hörprüfung → P4 nur begründete Erweiterungen**. Der bisherige feste MusiCNN-Pool prüft ausschließlich Nachsortierung. Neue Modelle, Training, katalogweite Normalisierung und Backfills sind keine Voraussetzung für die erste unabhängige Messung und werden durch die Planpflege nicht gestartet.

## Übersicht

| Reihenfolge | ID | Ergebnis | Abhängigkeit | Status |
|---|---|---|---|---|
| 1 | R1 | Versionen, Updates und Veröffentlichungspfade geklärt | keine | offen |
| 2 | R2 | Radar und kombinierte Klangbewertung zuverlässig | reproduzierbarer Stand aus R1 | teilweise geprüft und in PR #48 gemergt; Radar-Skalierung offen |
| 3 | R3 | Konsistente Merkmale für den vorhandenen Katalog | R2, Sicherung und Umstellungsplan | offen |
| 4 | R4 | Upload und Identifikation vollständig geprüft | R1, R2 | offen |
| parallel ab jetzt | R5 | Gemessene Empfehlungsqualität | P0/P1; vergleichbare Audiodaten | Unabhängiger Vergleich auf 18 realen Pilotaufnahmen ausgeführt; Hörqualität offen |
| 6 | R6 | Verständlicher Einstieg und konsistente Ergebnisaktionen | R2; R5 für Score-Kommunikation | Titelsuche geprüft und in PR #48 gemergt; weitere Aktionen offen |
| 7 | R7 | Geeigneten Audiomotor nach belegtem Nutzen ausbauen | R5 | offen |
| begleitend | R8 | Wiederherstellung, Rechte und Überwachung belegt | R1 für Veröffentlichungen | offen |

## R1 – Versionsstände und Wartung

**Problem:** GitHub und laufende Images unterscheiden sich. Gemergte Abhängigkeitsupdates fehlen in Produktion; Beim autorisierten Dokumentations-Push für PR #47 reagierte die Vercel-Anbindung erneut mit einem erfolgreichen Deployment-Status. Vertragsstatus und gewünschter Umgang mit der Integration sind getrennt zu klären.

1. Sauberen Arbeitsstand auf aktuellem main herstellen; fremde Änderungen erhalten.
2. Server-Checkout, Image-IDs, installierte Pakete und Image-Inhalt gegen Zielcommit vergleichen.
3. Gemergte Updates, offene Dependabot-PRs und aktuelle Containerbefunde getrennt bewerten.
4. Vercel-/Railway-Integration einschließlich Preview und Production inventarisieren; kein Abschalten ohne Freigabe.
5. Geprüftes Update mit expliziter Live-Freigabe ausrollen und von außen verifizieren.

**Abnahme:** Zielcommit, Prüfungen, laufende Images und relevante Paketversionen dokumentiert. Alle Veröffentlichungswege bekannt; verbleibende Abweichungen begründet. Die lokale Synchronisierung allein erfüllt R1 nicht.

## R2 – Radar und Ranking reparieren

**Problem:** PostgREST liefert Vektoren als JSON-Text. Radar schlägt bei vorhandenen Merkmalen fehl; Einzelähnlichkeit fällt im geprüften Fall still auf MusiCNN zurück.

1. Gemeinsamen Vertrag für Zahlenlisten, JSON-Text, fehlende/ungültige Vektoren und Dimensionen festlegen.
2. Einzel-/Batch-Radar und alle Suchmodi dagegen prüfen.
3. Mathematische Radar-Skalierung prüfen: Z-normalisierte Werte nicht wie rohe BPM oder bereits auf 0–1 skalierte Werte behandeln.
4. Fehlendes MERT pro Kandidat und fehlende Handcrafted-Merkmale konsistent gewichten; Fallbacks diagnostizierbar machen.

**Abnahme:** Reproduktion aus KNOWN_ERRORS liefert bei gültigen Merkmalen gültige Radarwerte. Unvollständige Daten erzeugen definierte Antworten, keinen 500er. Tests mit realistischen PostgREST-Formaten und Browsernachweise belegen aktive Fusion und Fokuswirkung. Logs enthalten keine kompletten Vektoren.

## R3 – Vorhandene Rohdaten normalisieren

**Problem:** 588.707 Rohvektoren, aber 121.773 normalisierte Vektoren; Statistik ebenfalls auf 121.773 Songs basiert.

1. Rohvektoren auf Dimensionen, endliche Werte und konsistente Extraktion prüfen.
2. Entscheiden: mit bestehender Statistik ergänzen oder den gesamten Bestand mit neuer Statistik umstellen. Keine inkompatiblen Skalen im laufenden Ranking mischen.
3. Vorhandenes compute_stats-Script auf einer Kopie prüfen; Stichprobe vergleichen, Laufzeit und Sperren messen.
4. Wiederaufnahme, Fortschritt und Rückweg planen. Produktive Massenschreiboperation separat freigeben lassen.
5. Einheitlichen Abschluss prüfen; vollständige Normalisierung beim künftigen Ingest absichern.

**Abnahme:** Jeder geeignete Rohvektor besitzt einen gültigen normalisierten Vektor aus derselben dokumentierten Statistikversion. Ausnahmen gezählt und begründet; Radar/Ranking für alte und ergänzte Songs geprüft. Rohdaten sind vorhanden, vollständige Audio-Neuerfassung ist nicht automatisch erforderlich.

## R4 – Upload, Identifikation und Auto-Ingest

1. Kontrollierte Audio-Testdatei und erwartete Ergebnisse festlegen.
2. Upload → Warteschlange → Worker → DB-Ergebnis → Oberfläche → Dateibereinigung prüfen.
3. AcoustID-Konfiguration im Worker und Modellvoraussetzungen prüfen; Secrets ausschließlich außerhalb des Repos.
4. Ungültige Dateien, Analysefehler, Wartezeiten und Neustarts isoliert testen.
5. URL-Treffer, Miss und Deezer-Ingest einschließlich Wiederholungen/Duplikaten prüfen. Live-Ingest schreibt Daten und kann Künstlernachbarschaften erweitern.

**Abnahme:** Benannte echte Benutzerwege mit erwarteten Metadaten und Ergebnissen bestanden; Fehler verständlich; Testdaten kontrolliert aufgeräumt. Eine abgeschlossene Job-Zeile ohne gespeicherten Song genügt nicht.

## R5 – Empfehlungsqualität messen

Den [Plan P0–P4](listening-feasibility.md) verwenden: zuerst zulässige Audioquellen und positive Beispiele, dann MusiCNN, MERT und CLAP auf demselben Bestand unabhängig suchen lassen. Exakter Vergleich ohne Fusion/MMR; Modellstände und Vorverarbeitung einfrieren. Entwicklungs- und Testsätze nach Aufnahmefamilien und möglichst Künstlern trennen.

**Abnahme:** Reproduzierbarer Bericht über passende und unbekannte merkenswerte Top-5-Funde, Rang bestätigter Positiver, Ausfälle und Wiederholungsstabilität. Nutzenschwelle und Aufwand vor dem Versuch festlegen; Review-Zahlen bleiben Vorschläge. Ein Vorteil muss auf unbenutzten Referenzen bestehen. Keine Standardgewichtung aus fünf negativen Urteilen ableiten. Bei ausbleibendem Vorteil einen begrenzten Diagnosezweig prüfen, danach Abbruch oder belegte Einschränkung statt endlosem Training.

## R6 – Benutzerführung und Ergebnisaktionen

Titelsuche im Einstieg zugänglich machen; Datenlücken verständlich anzeigen. Fokus, Journey und Feedback nach Blend/Vibe prüfen: Mehrfachabfragen verwenden einen synthetischen Song-Identifier, der nicht wie ein gespeicherter Song behandelt werden darf. Prozentwerte als Scores erklären. Playlist und Verlauf als lokal kennzeichnen.

**Abnahme:** Suche und wesentliche Ergebnisaktionen auf Desktop und Mobilgröße per Maus und Tastatur geprüft; sinnvolle Labels, Fokusführung und Fehlerzustände. Bestehende Playlistdaten bleiben erhalten.

## R7 – Bewährten Audiomotor gezielt ausbauen

Erst nach R5 entscheiden, welches Modell beziehungsweise welche begründete Anpassung Nutzen bringt. Kein MERT-Vorrang. Audio- und Modellrechte, Versionen, Abhängigkeiten, gemessenen Gerätebedarf, Wiederaufnahme und Betriebsbudget vor einer Kataloganalyse festlegen. Eine kleine Trainingsprojektion ist nur bei stabilen positiven/negativen Urteilen und systematischen Rangfehlern vorgesehen.

**Abnahme:** Vorteil gegenüber dem unveränderten Encoder auf unbenutzten Songs; Analyseaufwand und Suchlatenz gemessen; Daten und Modellversionen konsistent; Rückweg vorhanden. Ohne belegten Nutzen kein Backfill. Veröffentlichung separat konkret freigeben.

## R8 – Betrieb und Wiederherstellung

- Aktuellen Dump isoliert wiederherstellen; Indizes und Funktionen prüfen.
- Live-Rechte mit Migrationen vergleichen, insbesondere feedback_stats; keine pauschalen Revoke-Befehle ohne Abhängigkeitsprüfung.
- Externe Alarmzustellung und interne Healthchecks unterscheiden.
- Schema von Grund auf reproduzieren; manuelle historische Migrationen berücksichtigen.

**Abnahme:** Wiederherstellungsdauer und tolerierter Datenverlust festgelegt und getestet; Alarmprobe bestätigt; effektive Rechte und Schema dokumentiert. Vor riskanten Datenänderungen muss R8 die nötige Absicherung liefern.

## Zurückgestellt

Großflächiges Katalogwachstum, zusätzliche Genres, andere Vektordatenbanken, Konten/Bezahlung und neue Orchestrierung sind keine aktuelle Umsetzung. Dafür sind belegter Bedarf und neue Entscheidung nötig.

## Pflege

Bei Bearbeitung ID, Status, PR/Commit, Testnachweis und gegebenenfalls Live-Nachweis ergänzen. Ungetestete Pakete bleiben offen. Historische Messungen durch neue datierte Berichte ergänzen, nicht still überschreiben.
