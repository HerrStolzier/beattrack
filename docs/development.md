# Entwicklungsumgebung

Stand: 2026-09-15. Diese Anleitung beschreibt die vorhandenen Werkzeuge; sie installiert nichts automatisch. Ein vollständig frischer macOS-/Linux-Setup wurde in der Dokumentationsrunde nicht ausgeführt.

## Voraussetzungen

- Git, Bun und uv; Versionen der CI in [.github/workflows/ci.yml](../.github/workflows/ci.yml) beachten.
- Python 3.12 für Übereinstimmung mit Container/CI; Node für Next.js-Tooling.
- ffmpeg/ffprobe, libmagic und libpq für die native API-Laufzeit.
- Essentia/essentia-tensorflow sind plattformabhängig. Bei fehlenden macOS-Wheels eine passende Linux-Entwicklungsumgebung vorsehen; keine ungeprüften Ersatzpakete installieren.
- Ein isoliertes PostgreSQL-/PostgREST-Testsystem mit passendem Schema und Testdaten; nicht automatisch die Produktionsdatenbank verwenden.

## Arbeitsstand zuerst prüfen

```sh
git status --short --branch
git remote -v
git fetch origin main
git log --oneline HEAD..origin/main
```

Erst nach Prüfung lokaler Änderungen vorwärts aktualisieren. Checkpoints und unversionierte Artefakte nicht pauschal löschen. Bun ist der Projekt-Paketmanager; kein zusätzliches npm-Lockfile erzeugen.

## Frontend

Nach autorisiertem Setup:

```sh
bun install --frozen-lockfile
cd apps/web
bun run dev
```

Umgebung für den Dev-Prozess: NEXT_PUBLIC_API_URL=http://localhost:8000. Der Wert ist öffentlich und darf kein Secret enthalten. Next.js liest ihn auch beim Build ein. Die aktuelle CSP leitet die erlaubte API-Origin aus dieser Variable ab. Nach einer Änderung Dev-Server neu starten bzw. Produktionsfrontend neu bauen; Header und Verbindung im Browser prüfen. Sicherheitsheader nicht global abschalten.

Die häufig zitierte Anweisung „bun run dev im Root“ ist falsch: Das Root-package.json besitzt keine entsprechenden Scripts.

## Backend und Worker

```sh
cd apps/api
uv sync --frozen --extra dev
uv run uvicorn app.main:app --reload
```

Variablen vorher über eine lokale, geschützte Shell-/Secret-Konfiguration bereitstellen. Eine Datei namens .env wird durch die gezeigten Befehle nicht automatisch geladen. Niemals Produktions-Secrets in Shell-History oder Beispieltexte kopieren.

Ein API-Prozess allein verarbeitet keine Queue-Aufträge. Für Integrationstests separaten Worker gegen dieselbe isolierte DB starten, ROLE=worker setzen und denselben Upload-Pfad bereitstellen. Queue-Schema gemäß installierter Procrastinate-Version initialisieren. Das API-Dockerfile enthält den bestehenden Rollenstart; kein neuer lokaler Vollstack wird hier behauptet.

## Variablenvertrag

| Variable | Zweck | Hinweise |
|---|---|---|
| NEXT_PUBLIC_API_URL | Browser-API-Basis | öffentlich; lokal typischerweise Port 8000, Produktion /api |
| SUPABASE_URL | PostgREST-/Supabase-Basis | bei eigener Instanz Basis-URL mit REST-Routing |
| SUPABASE_ANON_KEY | Fallback im DB-Client | Zugriff hängt von effektiven DB-Rechten ab |
| SUPABASE_SERVICE_ROLE_KEY | Backendzugriff | in Produktion erforderlich; nie im Frontend |
| DATABASE_URL | Direkter PostgreSQL-Zugang | Queue; eigenes Testsystem verwenden |
| SUPABASE_DB_URL | Optionaler Queue-Override | fällt auf DATABASE_URL zurück |
| ROLE | api oder worker | bestimmt Connector und Containerstart |
| BEATTRACK_TEMP_DIR | Upload-Pfad | für API/Worker identisch und schreibbar |
| ACOUSTID_API_KEY | Metadatenidentifikation | im Worker benötigt, nicht nur in der API |
| CORS_ORIGINS | Erlaubte Browser-Origin(s) | vollständige Origins inklusive Schema, kommasepariert; Implementierung prüft www-Ergänzung nur für exakte HTTPS-Origin |
| ADMIN_SECRET | Admin-Endpunkte | ohne Konfiguration absichtlich nicht verfügbar |
| CRON_SECRET | Next.js-Cronroute | kein Nachweis, dass ein Scheduler eingerichtet ist |

SENTRY_DSN wird in älteren Dokumenten genannt; im geprüften Anwendungscode ist keine Sentry-Initialisierung vorhanden. Das Setzen allein aktiviert kein Error-Tracking.

## Modelle und Daten

MusiCNN-Datei liegt unter [apps/api/models](../apps/api/models). MERT benötigt zusätzliche torch-/transformers-Abhängigkeiten und Modelldateien; nicht für einen normalen Dokumentations- oder Frontendtest installieren. Große Audio-/Feature-Daten sind teilweise absichtlich nicht versioniert. Keine Wiederbeschaffung oder Batch-Jobs ohne Auftrag starten.

## Prüfungen und Konventionen

Siehe [CHECKS.md](../CHECKS.md). Editor-Grundwerte stehen in [.editorconfig](../.editorconfig), Python-Lint/Typkonfiguration in [pyproject.toml](../apps/api/pyproject.toml), Web-Konfiguration im jeweiligen Paket. Die EditorConfig formatiert bestehende Dateien nicht rückwirkend.
