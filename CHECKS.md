# Prüfungen und Nachweise

> **Zweck:** Passende Verifikation ohne unnötige Testläufe.
> **Scope:** Dokumentation, Anwendung, Daten, CI und Live-Abnahme.
> **Suchbegriffe:** test, pytest, vitest, build, lint, e2e, deploy
> **Stand:** 2026-09-15

## Standardabschluss

Prüfungen nach Änderungswirkung auswählen. Keine automatische Komplettserie nur wegen einer Dokumentationsänderung. Nach ausreichenden bestandenen Prüfungen abschließen; erneut prüfen bei neuen Änderungen, Fehlern oder konkreten offenen Fragen.

| Änderung | Erforderlicher Nachweis |
|---|---|
| Dokumentation | Fakten/Quellen, lokale Links und Pfade, widerspruchsfreie Zustände, git diff --check |
| Frontend-Verhalten | Betroffene Vitest-Tests, Typprüfung/Build nach Wirkung, echter Browserweg |
| API-/Rankinglogik | Gezielte pytest-Tests, realistische DB-Datentypen, betroffener API-/Benutzerweg |
| Upload/Worker | Verarbeitung bis zum sichtbaren Ergebnis, Persistenz und Cleanup; isolierte Fehler-/Neustarttests |
| Datenmigration/Normalisierung | Kopie, Vorher-/Nachher-Zählung, Vektorgültigkeit, Skalenkonsistenz, Rückweg |
| Deployment | Zielcommit/Images, passende Logs, externe Abfrage und betroffene Funktion |

## Vorhandene lokale Befehle

Aus dem jeweiligen Paket, nach eingerichteter Testumgebung:

```sh
# apps/web
bun run test --run
bunx --no-install tsc --noEmit
bun run build
bun run lint

# apps/api
uv run --frozen pytest tests/ -q
```

Raw bun test umgeht Vitest/jsdom. bun run test ohne --run kann im Watch-Modus bleiben. Der Frontend-Lint nutzt derzeit next lint; lokale Probleme mit Workspace-Hoisting sind historisch dokumentiert, nicht für jede Maschine bewiesen. Bei Problemen tatsächlichen Fehler berichten, keine pauschale Erfolgsbehauptung oder Abschaltung.

Die bestehenden Struktur-/Pfadprüfer können für Dokumentation gezielt verwendet werden:

```sh
python3 scripts/workflow_check.py
python3 scripts/doc_drift_check.py
git diff --check
```

Der Pfadprüfer erfasst nur WORKFLOWS, CHECKS und KNOWN_ERRORS. Neue Markdown-Dateien und relative Links zusätzlich prüfen; sein Erfolg ist kein vollständiger Linkcheck.

## CI

| Workflow | Tatsächlicher Scope |
|---|---|
| .github/workflows/ci.yml | Push auf main und PR gegen main: Backend pytest/pip-audit, Frontend Lint/Typprüfung/Build/Vitest |
| .github/workflows/codeql.yml | Statische Codeanalyse; kein Beleg einer vollständigen Sicherheitsabnahme |
| .github/workflows/secret-scan.yml | gitleaks über Git-Historie |
| .github/workflows/container-scan.yml | Dockerfile-bezogene PRs, Wochenplan/manuell; Basisimages und Konfiguration |

CI-Ergebnisse immer einem Commit und Datum zuordnen. Die 164 Backend- und 67 Frontendtests vom 17.08.2026 sind historische Belege; sie ersetzen keine Prüfung neuer Änderungen. Containerbefunde betreffen im vorhandenen Workflow Original-Basisimages, nicht automatisch fertige laufende App-Images.

## End-to-End-Grenze

Eine vollständige versionierte Playwright-Suite wurde nicht gefunden. Manueller Browsernachweis, API-Test, Unit-Test und historische Upload-Prüfung getrennt berichten. Keine neue Live-Datei hochladen, Metadaten ingesten oder Testbewertungen absenden, wenn der Auftrag nur lesend ist.

## Historische Guard-Werkzeuge

scripts/agent_finish.py und weitere Guard-Scripts sind vorhandene Kopien, siehe scripts/README.md. Das Review-Gate wurde auf main deaktiviert; die Aktivierungsdatei fehlt. Keine Pflicht zur Reaktivierung oder zusätzlichen Modellprüfung.

Der Sammelbefehl führt weiterhin den Inhalt von .agents/project_check aus und kann umfangreiche Tests bzw. Watch-Modus starten. Er ist kein sinnvoller Standard für reine Dokumentation. Die Dokumentationsrunde ändert diese historischen Scripts und Hooks nicht.

## Wartung im Dokumentations-PR #47

Der erforderliche Backend-Check scheiterte am 15.09. vor pytest am Audit der Entwicklungsabhängigkeit pip 26.1.2 (PYSEC-2026-3721). Das Lockfile aktualisiert gezielt pip auf die im Audit genannte korrigierte Version 26.2. Keine Audit-Ausnahme und keine Abschaltung des Checks; erneute CI ist vor Merge erforderlich.
