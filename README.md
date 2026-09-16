# Beattrack

> **Eingestellt am 16.09.2026 auf Nutzerauftrag.** Die Entwicklung wird nicht fortgesetzt. Frühere Ziele und Pläne sind historisch, kein aktiver Umsetzungsauftrag. [Rückbau und Nachweise](docs/retirement-2026-09-16.md).

Musik anhand ihres Klangs entdecken: ähnliche Songs, Sonic Blend und Vibe aus einem Electronic-Katalog. Open Source unter [AGPL-3.0](LICENSE).

**Betrieb:** eingestellt. Website und API wurden abgeschaltet.

## Einstieg

| Frage | Dokument |
|---|---|
| Ziel, Umfang und Stand? | [Projektübersicht](project.md) |
| Was kommt als Nächstes? | [Roadmap](docs/roadmap.md) |
| Wie funktionieren Code und Datenfluss? | [Architektur](docs/architecture.md) |
| Wo und wie läuft Produktion? | [Infrastruktur](docs/infrastructure.md) |
| Wie richte ich Entwicklung ein? | [Entwicklung](docs/development.md) |
| Wie ändere und prüfe ich etwas? | [Workflows](WORKFLOWS.md), [Checks](CHECKS.md) |
| Welche Probleme sind bekannt? | [Bekannte Fehler](KNOWN_ERRORS.md) |
| Welche Entscheidungen gelten? | [Entscheidungen](docs/decisions.md) |
| Woher stammen die Aussagen? | [Bestandsaufnahme vom 15.09.2026](docs/status-2026-09-15.md) |

## Stack

- Web: Next.js 15, React 19, TypeScript, Tailwind CSS 4.
- API: FastAPI/Python, Essentia und MusiCNN; MERT als ergänzende Modellpipeline.
- Speicherung: PostgreSQL 17 mit pgvector, Zugriff über PostgREST.
- Hintergrundaufgaben: Procrastinate, eigener Worker und gemeinsames Upload-Volume.
- Produktion: Docker Compose auf Hetzner; Traefik für HTTPS und Routing.
- Abhängigkeiten: Bun und uv. Aufgelöste Versionen stehen in den Lockfiles.

## Aktuelle Grenze

Die geprüften Suchwege liefern live Ergebnisse. Radar und die Kombination mehrerer Klangsignale sind beeinträchtigt; ein großer Teil der Merkmale ist noch nicht normalisiert. Details und Prüfgrenzen stehen im datierten Statusbericht. Eine erreichbare Website beweist nicht alle Funktionen.

## Historische Pläne

[PLAN.md](PLAN.md), [PLAN2.0.md](PLAN2.0.md), [PLAN3.0.md](PLAN3.0.md) und der [alte Skalierungsplan](docs/scaling-plan.md) bleiben als Entwicklungsgeschichte erhalten. Neue Prioritäten werden ausschließlich in der aktuellen Roadmap gepflegt.

Sicherheitsprobleme bitte gemäß [SECURITY.md](SECURITY.md) vertraulich melden.
