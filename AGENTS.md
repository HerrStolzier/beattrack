# Arbeiten an Beattrack

## Orientierung

Lies zuerst [project.md](project.md), dann nur auftragsrelevante Dokumente. Offene Arbeit steht in [docs/roadmap.md](docs/roadmap.md), Prüfungen in [CHECKS.md](CHECKS.md), Betriebsabläufe in [WORKFLOWS.md](WORKFLOWS.md).

## Umfang und Freigaben

- Erklären, recherchieren und planen verändert weder Anwendung noch Produktion.
- Bei Umsetzung notwendige reversible Änderungen im vereinbarten Umfang durchführen und prüfen. Nutzeränderungen und unbekannte Daten erhalten.
- Routine-Commits, Pushes und geprüfte Merges gehören zum autorisierten Umsetzungsauftrag. Vor Push/Merge Hosting-Integrationen prüfen: automatische Preview- oder Produktionsveröffentlichungen können zusätzliche Freigabe erfordern. Historische GitHub-Deployment-Einträge beweisen keinen aktuellen Hosting-Trigger oder Vertragsstatus.
- Live-Deployment, Installation neuer Software, destruktive Aktionen, neue Zugriffsrechte oder wesentliche Zielerweiterungen brauchen konkrete Freigabe. Bestehende Freigaben nicht wiederholt erfragen.
- Keine Secrets in Repository, Ausgabe, Berichte oder Beispiele aufnehmen.

## Qualität und Abschluss

- Lokalen Branch, GitHub, Server-Checkout und laufende Images getrennt behandeln.
- Angemessene Prüfungen aus CHECKS.md wählen. Dokumentation braucht keine Audio-Pipeline oder pauschale Testserie.
- Sichtbare Änderungen möglichst über echte Benutzerwege prüfen. Testdaten und selbst erzeugte Testfenster anschließend aufräumen.
- Nachweise als Codebefund, aktuelle Messung, historischer Beleg oder offene Frage kennzeichnen.
- Commit-Nachrichten auf Englisch, Dokumentation und UI grundsätzlich auf Deutsch.
- Keine zusätzlichen Agenten, Modelle, Workflow-Guards oder Automationen allein aufgrund alter Pläne starten. Vorhandene Guard-Scriptkopien nicht eigenständig verändern oder reaktivieren.
- Ergebnis, Prüfung, Veröffentlichungsstand und verbleibende Grenzen knapp nennen.
