# Checks

> **Zweck:** Welche Prüfungen dieses Projekt kennt und wann welche greift.
> **Scope:** Standardabschluss, technischer Projektcheck, Review-Gate, CI, Deploy-Verifikation. Nicht: Inhalt der Tests selbst.
> **Suchbegriffe:** check, test, pytest, vitest, bun, uv, ci, review, gate, deploy, verifikation, agent_finish, trivy, codeql
> **Stand:** 2026-07-31

## Standardabschluss

```bash
python3 scripts/agent_finish.py --auto-claims
```

Läuft auch automatisch als Stop-Hook (`.claude/settings.json`). Umfasst
Struktur-Guard, Doc-Drift, Projektcheck, Review-Gate und Claim-Check.

## Technischer Projektcheck

Hinterlegt in `.agents/project_check`: beide Test-Suiten, rund 20 Sekunden.

```bash
(cd apps/api && uv run pytest -q)     # 164 Tests
(cd apps/web && bun run test)         # 67 Tests (Vitest)
```

Bewusst **nicht** enthalten:

- **Web-Build** (`bun run build`) — kostet ~25 s pro Abschluss, die CI baut ohnehin.
- **Frontend-Lint** — lokal kaputt durch Bun-Workspace-Hoisting von
  `@next/eslint-plugin-next`, läuft nur in der CI. Deshalb committen Agenten hier
  mit `--no-verify`, sonst blockt der Husky-Pre-Commit-Hook jeden Commit.
- **Raw `bun test`** — nutzt Buns eigenen Runner ohne jsdom-Setup und schlägt fehl.
  Immer `bun run test`.

## Review-Gate (scharf seit 2026-07-31)

`.agents/review_required` liegt im Repo, damit blockiert `scripts/review_gate.py`
den Abschluss, bis ein Cross-Model-Review den aktuellen **Code**-Stand abdeckt.
Reine Doku-Änderungen (`.md`, `.txt`) lösen das Gate nicht aus.

```bash
scripts/agent_review --uncommitted        # Standardfall
scripts/agent_review --base main          # Diff gegen main
scripts/agent_review --commit <SHA>       # ein bestimmter Commit
```

Modell und Effort sind gesetzt (`gpt-5.6-terra`, `medium`) und werden nicht
angehoben. Ein fehlgeschlagenes Review (Login abgelaufen, Kontingent leer)
schreibt kein `last_review.json` und gilt **nicht** als Beleg.

## CI (GitHub Actions)

Läuft auf Pull Requests gegen `main`:

| Workflow | Prüft |
|---|---|
| `ci.yml` | Frontend Lint + Type-Check + Build + Vitest, Backend pytest + pip-audit |
| `codeql.yml` | Code-Scanning TypeScript + Python |
| `container-scan.yml` | Trivy über die Base-Images aller Dockerfiles |
| `secret-scan.yml` | gitleaks über die volle History |

**Bekannt rot:** `Scan node:22-alpine` meldet CVE-2026-59873 (node-tar in npm).
Kein Node-Base-Image hat den Fix bisher. npm ist aus unserem Runtime-Image
entfernt, der Scan prüft aber den Original-Tag und kann das nicht sehen.
Bewusst so belassen.

## Deploy-Verifikation

Nach jedem Deploy auf infra-01 von außen prüfen, nicht nur Container-Status:

```bash
curl -s https://beattrack.app/api/health
curl -s -o /dev/null -w '%{http_code}\n' https://beattrack.app
```

Container-Uptime allein beweist nichts: Ein `git pull` ohne `docker compose build`
plus `docker compose up -d` lässt die alten Images weiterlaufen. Gegenprobe über
die Image-ID (`docker inspect beattrack-api --format '{{.Image}}'`) oder über eine
Datei, die es nur im neuen Stand gibt.
