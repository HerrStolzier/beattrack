# scripts/ - Guard-Kopien (NICHT hier editieren)

> **Zweck:** Klarstellen, dass diese Scripts Kopien sind und wo die Quelle liegt.
> **Scope:** Herkunft der Guard-Scripts, wie man sie korrekt aendert.
> **Suchbegriffe:** guard, kopie, artefakt, source of truth, sync, kanonisch
> **Stand:** 2026-07-15

Diese Dateien sind **Kopien** aus dem zentralen Workflow-Guard-System, per
`tools/guard sync` hierher geschrieben. Aenderungen hier werden beim naechsten
Sync ueberschrieben.

**Quelle:** `workflow-guard-system/plugin/scripts/` (im claude-projects-Workspace).
Dort editieren, committen, dann `tools/guard sync`. Volle Architektur und
Voraussetzungen: `workflow-guard-system/ARCHITECTURE.md`.

Ausnahme: `.agents/project_check` ist projekt-eigen und gehoert HIERHER (bzw.
nach `.agents/`), nicht in die Quelle - das ist die Definition von "fertig" fuer
genau dieses Repo.
