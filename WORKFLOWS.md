# Workflows

> **Zweck:** Register der wiederkehrenden Abläufe, die über einen einzelnen Befehl hinausgehen.
> **Scope:** Entwicklung, Deploy, Batch-Jobs am Katalog. Nicht: Architektur (steht in CLAUDE.md) und nicht: Server-Runbooks (Repo `infra-migration`).
> **Suchbegriffe:** deploy, docker, compose, infra-01, hetzner, seeding, backfill, mert, essentia, migration, postgres, worker, dev, lokal
> **Stand:** 2026-07-31

## Lokal entwickeln

- Zweck: Frontend oder Backend auf dem eigenen Rechner laufen lassen.
- Start: `cd apps/web && bun dev` bzw. `cd apps/api && uv run uvicorn app.main:app --reload`
- Input: `apps/web/.env.local` (`NEXT_PUBLIC_API_URL`), `apps/api/.env` (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `ACOUSTID_API_KEY`)
- Output: Dev-Server auf Port 3000 bzw. 8000
- Wichtige Dateien: `.claude/launch.json` (Browser-Preview), `apps/api/app/main.py`
- Abhaengigkeiten: `bun install` im Root, `uv sync` in `apps/api`; für das Backend zusätzlich `libmagic` und `libpq` (macOS: `brew install libmagic libpq`)
- Bekannte Fehlerfaelle: Ohne `libmagic` bricht schon der Import ab, ohne `libpq` scheitert der Procrastinate-Start im Lifespan. Beide Meldungen sehen nach Python-Fehlern aus, sind aber fehlende Systembibliotheken.
- Pruefung: `curl -s localhost:8000/health`
- Letzter Review: 2026-07-31

## Deploy auf infra-01

- Zweck: Neuen Stand von `main` in Produktion bringen.
- Start: auf dem Server, in dieser Reihenfolge:
  ```bash
  cd /opt/apps/beattrack && git pull --ff-only origin main
  cd /opt/stack && docker compose build beattrack-api beattrack-web beattrack-worker
  cd /opt/stack && docker compose up -d beattrack-api beattrack-web beattrack-worker
  ```
- Input: gemergter Stand auf `main`
- Output: neu gebaute Images, neu erzeugte Container
- Wichtige Dateien: `apps/api/Dockerfile` (ROLE=api/worker), `apps/web/Dockerfile`, `/opt/stack/docker-compose.yml` (Quelle: Repo `infra-migration`)
- Abhaengigkeiten: SSH-Zugang mit `~/.ssh/hetzner_infra`, Docker auf infra-01
- Bekannte Fehlerfaelle: **`git pull` allein deployt nichts.** Die Container laufen aus Images; ohne `build` und `up -d` läuft der alte Code weiter, während der Checkout schon neu aussieht. Genau das ist am 2026-07-30 passiert und fiel erst über die Image-IDs auf.
- Pruefung: siehe CHECKS.md, Abschnitt Deploy-Verifikation. Nur Doku- oder Test-Änderungen brauchen keinen Rebuild.
- Letzter Review: 2026-07-31

## Datenbank-Migration

- Zweck: Schemaänderung auf der eigenen Postgres ausrollen.
- Start: `docker exec -i postgres psql -U postgres -d beattrack < supabase/migrations/<datei>.sql`
- Input: SQL-Datei in `supabase/migrations/`
- Output: geändertes Schema
- Wichtige Dateien: `supabase/migrations/` (001–022 plus datierte Dateien)
- Abhaengigkeiten: laufender `postgres`-Container auf infra-01
- Bekannte Fehlerfaelle: Die Migrationen sind über die Zeit auseinandergelaufen. Zwei Dateien fehlten zeitweise ganz in der Versionskontrolle, obwohl die Live-DB die Objekte hatte; ein Neuaufbau rein aus dem Ordner wäre gescheitert. Vor Verlass auf den Ordner gegen die echte DB prüfen.
- Pruefung: `docker exec postgres psql -U postgres -d beattrack -c '\d <tabelle>'`
- Letzter Review: 2026-07-31

## Katalog-Backfill (MERT, Genre)

- Zweck: Fehlende Embeddings und Genres für bestehende Songs nachziehen.
- Start: `cd apps/api && .venv/bin/python scripts/extract_mert_batch.py --apply` bzw. `scripts/backfill_genre.py --apply`
- Input: Envvars `SUPABASE_URL` und `SUPABASE_ANON_KEY`, wobei letzterer den **service_role**-Wert braucht, weil die Scripts über RPC schreiben
- Output: gefüllte `mert_embedding` bzw. `genre` Spalten, Checkpoint-Dateien
- Wichtige Dateien: `apps/api/scripts/`, `app/workers/mert.py`
- Abhaengigkeiten: Checkpoint/Resume, Retry mit Backoff
- Bekannte Fehlerfaelle: Läuft seit dem Katalogwachstum hinterher (Stand 2026-07-31: MERT 53 %, handcrafted 21 % bei 588.707 Songs). Lange Jobs mit `nohup` starten. `app/workers/__init__.py` zieht Procrastinate mit, für reine MERT-Läufe `mert.py` direkt importieren.
- Pruefung: `select count(mert_embedding), count(*) from songs;`
- Letzter Review: 2026-07-31

## Abschluss einer Änderung

- Zweck: Nicht-triviale Arbeit belegt abschließen.
- Start: `python3 scripts/agent_finish.py --auto-claims` (läuft auch als Stop-Hook)
- Input: aktueller Arbeitsbaum
- Output: Eintrag in `.agents/finish_runs.jsonl`
- Wichtige Dateien: `scripts/`, `.agents/project_check`, `.agents/review_required`
- Abhaengigkeiten: Das Review-Gate ist scharf und verlangt bei Code-Änderungen ein Cross-Model-Review (`scripts/agent_review`).
- Bekannte Fehlerfaelle: Ein abgebrochenes Review schreibt bewusst keinen Beleg und hält das Gate zu. Login via `codex login` in einem echten Terminal.
- Pruefung: Exit-Code des Scripts
- Letzter Review: 2026-07-31
