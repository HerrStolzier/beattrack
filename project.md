# Beattrack – Projektübersicht

Stand: 2026-09-15. Pflege bei Änderungen von Ziel, Architektur, Prioritäten oder Betrieb.

## Ziel und Grenzen

Beattrack hilft beim Entdecken klanglich ähnlicher Musik und soll Gemeinsamkeiten verständlich erklären. Der dokumentierte Katalogschwerpunkt ist Electronic. Playlist, Verlauf, Blend/Vibe und DJ-Hilfen unterstützen diesen Ablauf.

Die zuletzt dokumentierte Produktentscheidung lautet: unmonetarisiert. Daraus entstehen keine automatische neue Monetarisierungsstrategie und keine Zusage über zukünftige Geschäftsmodelle. Lizenz- und Anbieterbedingungen sind bei einer solchen Änderung separat zu prüfen.

## Dokumentenregister

- Dieses Dokument: Ziel, Umfang und Orientierung.
- [Roadmap](docs/roadmap.md): priorisierte Arbeitspakete und Abnahmekriterien.
- [Architektur](docs/architecture.md): Zusammenhänge und Code-Einstiegspunkte.
- [Infrastruktur](docs/infrastructure.md): Produktionsmodell, Zuständigkeiten und Risiken.
- [Entwicklung](docs/development.md): Voraussetzungen und lokale Abläufe.
- [Workflows](WORKFLOWS.md): Änderungen und Freigabegrenzen.
- [Checks](CHECKS.md): passende Nachweise pro Änderungsart.
- [Bekannte Fehler](KNOWN_ERRORS.md): offene Funktions- und Betriebsprobleme.
- [Statusbericht](docs/status-2026-09-15.md): zeitlicher Bezug für Messungen.
- [Entscheidungen](docs/decisions.md): Herkunft und Geltung wichtiger Festlegungen.

Aktueller Code und direkte Messungen haben bei Tatsachen Vorrang vor älteren Berichten. Neue Nutzerentscheidungen haben Vorrang vor dokumentierten Planvorschlägen. Bei Widersprüchen Quelle und Datum nennen.

## Funktionsstand

| Bereich | Stand der Bestandsaufnahme |
|---|---|
| Einzelähnlichkeit, Blend, Vibe | Implementiert; ausgewählte Live-Abfragen erfolgreich |
| Blend-Oberfläche | Zwei Ausgangssongs bis zu 20 sichtbaren Ergebnissen geprüft |
| Audio-Upload und Identifikation | Implementiert; vollständige aktuelle End-to-End-Abnahme offen |
| Radar, Fokus, kombinierte Klangbewertung | Implementiert, bekannte Daten- und Verarbeitungsprobleme |
| Journey, DJ-Modus, Playlist, Verlauf | Implementiert; vollständige Funktionsabnahme offen |
| Feedback und A/B-Ereignisse | Implementiert; Wirksamkeit des Lernens nicht nachgewiesen |

## Umfang der Dokumentationsrunde

Projektführung und Dokumentation werden auf GitHub-Stand `f5ea2fa` konsolidiert. Keine Funktion wird dadurch als repariert oder veröffentlicht markiert. Die Roadmap ist ein Vorschlag zur nächsten Umsetzung, kein Auftrag zum Start von Backfills, Upgrades oder Deployments.

## Definition von fertig

Ein Arbeitspaket ist fertig, wenn sein Abnahmekriterium erfüllt, angemessen geprüft und dokumentiert ist. Zustände getrennt führen: **vorgeschlagen → umgesetzt → getestet → veröffentlicht**. Für Produktionsbefunde muss die Wirkung im laufenden System bestätigt werden.

Keine Prozentangabe über die Gesamtfertigstellung: alte Phasenpläne und heutiger Funktionsumfang sind nicht deckungsgleich.
