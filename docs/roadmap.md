# Roadmap und Umsetzungsplan

Stand: 2026-09-15 · **Vorgeschlagen; Umsetzung nicht gestartet.**

Grundlage: [Bestandsaufnahme](status-2026-09-15.md). Die bisherigen PLAN-Dateien sind historische Entwürfe. Reihenfolge nach Nutzerwirkung, Datenintegrität und Betriebsrisiko; keine verbindlichen Termine ohne Diagnose und Umfangsschätzung.

## Übersicht

| Reihenfolge | ID | Ergebnis | Abhängigkeit | Status |
|---|---|---|---|---|
| 1 | R1 | Versionen, Updates und Veröffentlichungspfade geklärt | keine | offen |
| 2 | R2 | Radar und kombinierte Klangbewertung zuverlässig | reproduzierbarer Stand aus R1 | offen |
| 3 | R3 | Konsistente Merkmale für den vorhandenen Katalog | R2, Sicherung und Umstellungsplan | offen |
| 4 | R4 | Upload und Identifikation vollständig geprüft | R1, R2 | offen |
| 5 | R5 | Gemessene Empfehlungsqualität | R2, R3 | offen |
| 6 | R6 | Verständlicher Einstieg und konsistente Ergebnisaktionen | R2; R5 für Score-Kommunikation | offen |
| 7 | R7 | MERT nach belegtem Nutzen ausgebaut | R5 | offen |
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

Ein festes Testset aus Electronic-Untergenres und unterschiedlichen Feature-Abdeckungen definieren. MusiCNN, Fusion und MERT mit identischen Seeds vergleichen. Menschliche Hörurteile von Genre-Precision trennen; beide messen unterschiedliche Dinge.

**Abnahme:** Reproduzierbarer Bericht mit Daten-/Modellstand, Stichprobenauswahl, Qualitätsmaß, Latenzen und Grenzen. Standardgewichtung anhand der Ergebnisse begründet. Die dokumentierten 31 Feedbacks und 15 Klicks belegen kein wirksames Lernen. Ein A/B-Versuch braucht unterschiedliche Rankingvarianten, ausreichende Daten und eine vorher festgelegte Auswertung.

## R6 – Benutzerführung und Ergebnisaktionen

Titelsuche im Einstieg zugänglich machen; Datenlücken verständlich anzeigen. Fokus, Journey und Feedback nach Blend/Vibe prüfen: Mehrfachabfragen verwenden einen synthetischen Song-Identifier, der nicht wie ein gespeicherter Song behandelt werden darf. Prozentwerte als Scores erklären. Playlist und Verlauf als lokal kennzeichnen.

**Abnahme:** Suche und wesentliche Ergebnisaktionen auf Desktop und Mobilgröße per Maus und Tastatur geprüft; sinnvolle Labels, Fokusführung und Fehlerzustände. Bestehende Playlistdaten bleiben erhalten.

## R7 – MERT gezielt erweitern

Erst nach R5 entscheiden, für welche Katalogteile der Rechenaufwand gerechtfertigt ist. Modellversion, Abhängigkeiten, Gerätebedarf, Quelle, Wiederaufnahme und Betriebsbudget vor dem Lauf festlegen. Standardinstallation der API stellt MERT nicht vollständig bereit.

**Abnahme:** Abdeckung und Zusatznutzen gemessen; Backfill reproduzierbar; Suchlatenz akzeptabel. Kein pauschales Ziel „100 % um jeden Preis“.

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
