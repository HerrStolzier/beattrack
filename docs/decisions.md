# Architektur- und Projektentscheidungen

Stand: 2026-09-15. Kompaktes Entscheidungsregister; eine eigene ADR-Datei ist erst bei komplexen neuen Entscheidungen nötig. „Übernommen“ bedeutet aus Quellen rekonstruiert, nicht heute erneut von Basti entschieden.

| ID | Entscheidung | Status und Herkunft | Konsequenz / Neubewertung |
|---|---|---|---|
| D1 | Beattrack bleibt unmonetarisiert | Übernommene Produktentscheidung, [29.07.2026](https://github.com/HerrStolzier/infra-migration/blob/4b2b8dee6e673afba6f5745d4fb967acede8c7f9/docs/naechste-schritte.md) | Kein Zahlungs-/Kundenprojekt ohne neue Entscheidung |
| D2 | Produktion als Docker-Stack auf Hetzner | Implementiert; [Betriebsquelle](infrastructure.md) und Live-Prüfung | Eigene Verantwortung für Patches, Backups, Restore und Monitoring |
| D3 | PostgreSQL/pgvector und PostgREST weiterverwenden | Implementiert; Code und Live-DB | Kein Wechsel zu FAISS/Qdrant ohne gemessenen Bedarf |
| D4 | Procrastinate mit separatem Worker und gemeinsamem Upload-Volume | Implementiert; [Reparaturhistorie](https://github.com/HerrStolzier/infra-migration/blob/4b2b8dee6e673afba6f5745d4fb967acede8c7f9/docs/plan-audio-analyse.md) | Jobstatus persistent; Neustart-/Cleanup-Abnahme weiter nötig |
| D5 | Deezer-basierter Katalog mit 30-Sekunden-Previews | Implementiert; alle gezählten Datensätze source=deezer | Klangmerkmale repräsentieren Ausschnitte, nicht automatisch vollständige Songs |
| D6 | Bestehende Datenqualität vor weiterer Expansion | Empfehlung aus der Bestandsaufnahme | R2/R3 vor neuen Katalogquellen; keine bereits genehmigte Produktentscheidung |
| D7 | Eine zentrale Roadmap, getrennte Statusnachweise | In dieser Dokumentationsrunde eingerichtet | Alte PLAN-Dateien historisch; neue Messungen datieren |

## Neue Entscheidungen

Jeweils Problem, Optionen, gewählte Lösung, Verantwortlichen/Bestätigung, Datum, Folgen und Anlass zur Neubewertung festhalten. Keine implizite Freigabe für Installation, Veröffentlichung oder Datenmigration aus einer technischen Empfehlung ableiten.
