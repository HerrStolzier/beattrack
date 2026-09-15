# Beattrack

Projektregeln stehen in [AGENTS.md](AGENTS.md). Einstieg und Dokumentenregister: [project.md](project.md). Diese Datei hält keine zweite Architektur- oder Roadmapkopie vor.

## Technische Einstiegspunkte

- Web: `apps/web/app`, API-Client: `apps/web/lib/api.ts`.
- API: `apps/api/app/main.py`, Fachrouten: `apps/api/app/routes`.
- Audio und Jobs: `apps/api/app/workers`, `apps/api/app/services/jobs.py`.
- Datenbank: `supabase/migrations` (historischer Name; Produktion nutzt eigene PostgreSQL/PostgREST).
- Architektur: [docs/architecture.md](docs/architecture.md).
- Produktion und Integrationen: [docs/infrastructure.md](docs/infrastructure.md).

## Abschluss

Auftragsbezogene Prüfungen aus [CHECKS.md](CHECKS.md) durchführen. Kein pauschaler Hook-Bypass und keine zusätzliche Modellprüfung. Der vorhandene Pre-Commit-Hook prüft Änderungen unter apps/web; für reine Root-/docs-Dokumentation ist kein Frontend-Lint vorgesehen.

## Belegpflicht

Lokale Änderung, bestandener Test, GitHub-Merge und Live-Veröffentlichung sind unterschiedliche Zustände. Ein laufender Container oder Healthcheck beweist weder vollständigen Commit-Inhalt noch alle Benutzerwege.

Die früheren Guard-Scripts bleiben als historische Werkzeuge vorhanden. Ihre Existenz aktiviert keine Abschluss- oder Modellpflicht; Einzelheiten stehen in CHECKS.md.
