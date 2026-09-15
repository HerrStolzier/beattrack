# Bekannte Fehler und offene Grenzen

> **Zweck:** Nachvollziehbare offene Probleme statt pauschaler Projektbewertung.
> **Scope:** Funktion, Daten, Entwicklung und Betrieb; kein vollständiges Sicherheitsaudit.
> **Suchbegriffe:** radar, fusion, normalization, mert, deploy, backup, vitest
> **Stand:** 2026-09-15

Messungen und Grenzen: [Statusbericht](docs/status-2026-09-15.md). IDs beziehen sich auf die [Roadmap](docs/roadmap.md). Ein Dokumentationsupdate behebt keinen dieser Fehler.

## K1 – Radar scheitert bei vorhandenen Merkmalen (R2)

**Live reproduziert:** GET /api/songs/06e7e1b4-73a7-45d4-9f22-02574c9ee964/features lieferte HTTP 500. Für diesen Song existiert handcrafted_norm; der laufende DB-Client liefert ihn als str. Serverlog: TypeError bei Multiplikation von Zeichenketten.

**Ursache im Code:** apps/api/app/routes/songs.py gibt den ungeparsten Wert an die numerische Radarberechnung weiter. Einzel- und Batchpfad prüfen. Eine bloße Konvertierung reicht als Qualitätsabnahme nicht: Einheiten und Skalierung der Radarwerte müssen ebenfalls stimmen.

## K2 – Einzelähnlichkeit fällt still auf MusiCNN zurück (R2)

**Live reproduziert:** POST /api/similar mit dem Song aus K1 lieferte HTTP 200; das passende Log meldete „Late fusion failed, returning learned-only results“. Im Einzelpfad wird der Query-Handcrafted-Vektor nicht wie die Kandidaten geparst.

**Folge:** HTTP-Erfolg belegt keine aktive Fusion, MERT- oder Fokuswirkung. Gesamthäufigkeit nicht gemessen. Fehlende MERT-Daten pro Kandidat sind zusätzlich ein Code-Prüfpunkt, kein bereits katalogweit vermessener Fehler.

## K3 – Normalisierung unvollständig (R3)

588.707 Rohvektoren, 121.773 normalisierte Vektoren; Normalisierungsstatistik basiert ebenfalls auf 121.773 Songs. Für den geprüften Song 244d1d5a-5ec5-41da-86af-3188d12baf00 liefert Radar HTTP 422 „Song has no features“. Das ist ein anderer Fall als K1.

Fehlende Merkmale nicht mit Nullwerten als echte Analyse ausgeben. Die vorhandenen Rohmerkmale erlauben Nachverarbeitung; Gültigkeit und einheitliche Statistik zuerst prüfen.

## K4 – Produktionsstand und GitHub unterscheiden sich (R1)

Server-Checkout vom 31.07. lag bei der Prüfung 13 Commits hinter main. Im laufenden API-Container: cryptography 49.0.0 und h2 4.3.0; entsprechende Updates sind auf GitHub bereits gemergt. Vollständiger Image-zu-Commit-Abgleich offen.

GitHub enthält historische Vercel-Erfolgseinträge. Basti bestätigt die Kündigung; die Produktion auf Hetzner ist geprüft. Nachtrag zum autorisierten Push für PR #47: Vercel startete erneut und meldete success für 9dd2ea3. Der Trigger ist damit aktuell belegt, ein kostenpflichtiger Vertrag oder Wechsel des Hetzner-Hostings dagegen nicht.

## K5 – Upload-Identifikation nicht vollständig konfiguriert (R4)

Im laufenden Worker war ACOUSTID_API_KEY nicht gesetzt. Die Metadatenanreicherung verwendet diesen Schlüssel im Worker. Extraktion kann trotzdem laufen; ein vollständiger aktueller Upload-/Identifikations-E2E fehlt. Konfigurationskorrektur und Live-Test sind eigene Umsetzung.

## K6 – Rechte und Migrationsstand weichen ab (R8)

Live: anon besitzt kein SELECT auf songs, aber SELECT auf feedback_stats. Die jüngste entsprechende Migration entzieht letzteres. Ein externer anonym nutzbarer Datenzugriff wurde nicht getestet; Tabellenrecht und tatsächliche Erreichbarkeit getrennt behandeln.

Migrationen wurden historisch manuell angeglichen. Vor einem Neuaufbau oder weiteren SQL-Änderungen reale Objekte, Grants und Historie vergleichen. vector/pg_trgm nicht pauschal in ein anderes Schema verschieben: Funktionen, Typen und Indizes hängen daran.

## K7 – Benutzerführung und Mehrfachabfragen (R6)

Startfeld akzeptiert URLs; Titelsuche ist erst in Blend/Vibe zugänglich. Im Browser bestätigt. Mehrfachergebnisse verwenden im Frontend song_id=multi; Folgeaktionen für gespeicherte Songs müssen gesondert geprüft werden. Dieser zweite Punkt ist ein Codebefund, keine vollständige Live-Reproduktion aller Folgeaktionen.

## K8 – Container-Scan rot, Runtime-Betroffenheit gesondert prüfen (R1)

Der Basisimage-Scan vom 14.09. scheiterte für Python, Node und Bun mit kritischen Befunden. Der Node-Fall betrifft unter anderem npm-Abhängigkeiten; npm wird aus dem Web-Runtime-Image entfernt. Das erklärt nicht automatisch die übrigen Befunde. Alte Hinweise „nur Node ist rot“ oder „kein Fix verfügbar“ nicht ungeprüft weiterverwenden. Aktuelle Logs und tatsächliche Runtime prüfen.

## Entwicklungsfallen

- **Raw bun test:** falscher Runner für Vitest/jsdom. Im Web-Paket bun run test --run verwenden.
- **Root-Dev-Script:** existiert nicht; Befehle im Web-Paket ausführen.
- **Native API-Abhängigkeiten:** libmagic/libpq und Essentia-Wheels können fehlen. Kein Erfolg ohne tatsächlichen Import-/Laufnachweis.
- **Lokales Lint:** Workspace-Hoisting-Probleme sind historisch bekannt. CI und lokale Maschine getrennt betrachten; Hook nicht pauschal umgehen.
- **MERT:** zusätzliche Modellabhängigkeiten außerhalb des normalen API-Pakets. Vor Installation und Lauf Umfang klären.
- **Supabase CLI:** lokaler Status benötigt lokalen Docker-Stack; ist kein Produktionscheck für Hetzner.
- **Audit-Historie:** frühere PostCSS-/torch-/transformers-Hinweise sind keine aktuellen Auditresultate. Gegen das betroffene Lockfile bzw. Image prüfen, keine Canary-Umstellung nur für einen grünen Scan.

## Offene Nachweise

Restore des aktuellen Dumps, externe Alarmzustellung, repräsentative Hörqualität, vollständige Upload-/Journey-/Playlist-/DJ-Abnahme und komplette effektive Produktionsrechte. Weder „alles kaputt“ noch „alles bestanden“ ist aus Teiltests ableitbar.
