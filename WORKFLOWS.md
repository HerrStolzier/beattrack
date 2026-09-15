# Arbeitsabläufe

> **Zweck:** Wiederkehrende Abläufe für Änderungen, Daten und Betrieb.
> **Scope:** Entwicklung, Git, Deploy, Migration, Backfill. Keine automatische Ausführung.
> **Suchbegriffe:** deploy, docker, git, migration, backfill, roadmap
> **Stand:** 2026-09-15

## Änderung vorbereiten und abschließen

1. Auftrag und gegebenenfalls Roadmap-ID festhalten. Branch und vorhandene Nutzeränderungen prüfen.
2. Aktuellen Remote-Stand lesen; keine alten Pläne als heutigen Auftrag behandeln.
3. Auf einem benannten Branch, standardmäßig mit Präfix codex/, atomar arbeiten.
4. Passende Prüfungen aus [CHECKS.md](CHECKS.md) durchführen; betroffene Dokumente aktualisieren.
5. Diff prüfen und gezielt eigene Dateien committen. Unbekannte Artefakte nicht mit git add -A übernehmen.
6. Vor Push und Merge tatsächliche Hosting-Nebenwirkungen prüfen. GitHub zeigte am 15.09. weiterhin Vercel-Preview-Deployments; ein altes Hosting-Dokument widerlegt das nicht.
7. Bei konkreter Veröffentlichungsfreigabe Push/PR, erforderliche Checks und geprüften Merge durchführen. Fehlt sie, mit lokalem Commit und konkreter Beschreibung der externen Wirkung zur Freigabe vorlegen.
8. Ergebnis, Prüfungen, Commit/PR und Veröffentlichungsstand nennen.

Die Vorlage in [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) hält Ergebnis, Prüfung und externe Wirkung zusammen. Der Pre-Commit-Hook lintet nur bei Änderungen unter apps/web. Kein pauschales --no-verify aus alten Anleitungen übernehmen.

## Lokal entwickeln

Voraussetzungen, Variablen und Startbefehle: [docs/development.md](docs/development.md). Nur isolierte Testdatenbanken verwenden. Eine .env-Datei allein ist keine Garantie, dass der Prozess die Werte lädt. Ein Frontendstart ist keine Aufforderung, Produktion oder alle Schichten zu testen.

## Hetzner-Deployment – nur nach konkreter Freigabe

Voraussetzungen: Zielcommit geprüft, bisherige Images und Rückweg dokumentiert, passende Backup-/Schema-Voraussetzungen erfüllt. Das aktuelle Compose stammt aus infra-migration, nicht aus diesem Repository.

Der bestehende Ablauf auf dem Server lautet:

```sh
cd /opt/apps/beattrack
git pull --ff-only origin main
cd /opt/stack
docker compose build beattrack-api beattrack-web beattrack-worker
docker compose up -d beattrack-api beattrack-web beattrack-worker
```

Vor dem Build bestätigen, dass HEAD dem freigegebenen Commit entspricht. Wenn main inzwischen weitergelaufen ist, den neuen Stand nicht still mitveröffentlichen. Git pull allein deployt nichts. Keine anderen Dienste durch ein unbeschränktes compose up mitverändern.

Danach geänderte Image-IDs und wesentlichen Image-Inhalt mit dem Zielstand vergleichen, Logs prüfen sowie Health und betroffenen echten Benutzerweg von außen testen. Vorherige Images bis nach Abnahme behalten. Code-Rollback ist kein Datenbank-Rollback.

## Datenbankmigration

1. Nur lesend: vorhandenes Schema, Migrationshistorie und effektive Rechte vergleichen.
2. Migration auf isolierter Kopie testen, einschließlich Rückweg. Procrastinate-Schema wird separat initialisiert.
3. Backup und Restore-Voraussetzungen bestätigen; konkrete produktive Änderung freigeben lassen.
4. Nur freigegebene SQL-Datei gegen die richtige Datenbank anwenden; keine pauschale Ausführung aller historischen SQL-Dateien.
5. Schema, Rechte und abhängige Benutzerwege prüfen. Erfolg im datierten Bericht festhalten.

Der Ordner supabase/migrations enthält historisch manuell angeglichene Stände. Ein vollständiger Neuaufbau daraus ist noch nicht als reproduzierbar abgenommen.

## Katalog-Normalisierung und Backfill

Vorbereitung nach [R3/R7](docs/roadmap.md): Daten-/Statistikversion, Zielmenge, Laufzeit, Sperren, Wiederaufnahme und Abbruchkriterium festlegen. Normalisierte Bestände nicht mit unterschiedlichen Statistiken mischen. compute_stats.py erzeugt SQL; das ist keine Freigabe zur Anwendung.

Batch-Scripts können andere Variablennamen/Key-Annahmen als der reguläre API-Client besitzen. Vor jedem Lauf Quellcode und Zielsystem prüfen; niemals Tokens als Kommandozeilenargumente in Logs übernehmen. Große Jobs erst nach passender Freigabe starten, nicht aufgrund einer alten Checkpoint-Datei.

## Dokumentation pflegen

Roadmap-ID und Status bei echten Fortschritten aktualisieren. Messungen in einem datierten Bericht mit Methode, Stand und Grenze sichern. Historische Pläne nicht als erledigte aktuelle Aufgaben umetikettieren. Zusammenhänge in architecture/infrastructure pflegen; CLAUDE bleibt ein kurzer Verweis auf AGENTS und project.
