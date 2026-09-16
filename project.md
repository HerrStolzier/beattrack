# Beattrack – Projektübersicht

Stand: 2026-09-16. Pflege bei Änderungen von Ziel, Architektur, Prioritäten oder Betrieb.

## Ziel und Grenzen

Bestätigtes langfristiges Endziel (16.09.2026): **Beattrack findet zu einem Lieblingssong zuverlässig unbekannte, hörbar ähnliche Musik – mit geprüftem Nutzen und bezahlbarem Betrieb.** Die [Roadmap](docs/roadmap.md) führt vom begrenzten Machbarkeitstest bis zur wiederholten Produktabnahme; die Erreichbarkeit bleibt nachweispflichtig.

Beattrack hilft beim Entdecken klanglich ähnlicher Musik und soll Gemeinsamkeiten verständlich erklären. Der dokumentierte Katalogschwerpunkt ist Electronic. Playlist, Verlauf, Blend/Vibe und DJ-Hilfen unterstützen diesen Ablauf.

Die zuletzt dokumentierte Produktentscheidung lautet: unmonetarisiert. Daraus entstehen keine automatische neue Monetarisierungsstrategie und keine Zusage über zukünftige Geschäftsmodelle. Lizenz- und Anbieterbedingungen sind bei einer solchen Änderung separat zu prüfen.

## Dokumentenregister

- Dieses Dokument: Ziel, Umfang und Orientierung.
- [Roadmap](docs/roadmap.md): priorisierte Arbeitspakete und Abnahmekriterien.
- [Aktives Ziel und Hörvergleich](docs/listening-feasibility.md): Lieblingssong → klanglich passende Entdeckungen; technische Vorbereitung und offene Hörabnahme.
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

## Aktueller Umsetzungsauftrag

Am 15.09. wurde der begrenzte Machbarkeitstest beauftragt. Ranking-Reparaturen, Titelsuche und Hörvergleich wurden geprüft und mit PR #48 gemergt; Vercel meldete die Veröffentlichung für Merge ca02e7c als abgeschlossen. Kein Hetzner-Deployment in dieser Runde. Die musikalische Abnahme ist offen.

Nach unabhängigem Review wurde der Plan aktualisiert: Audioquellen und positive Vergleichspaare klären, vortrainierte Modelle unabhängig suchen lassen, Nutzen an unbenutzten Referenzen prüfen. Training und Katalogumbau benötigen belegten Nutzen. Am 16.09. wurde die Umsetzung bis zum bestätigten Endziel beauftragt. Die separate lokale Installation für MERT/CLAP wurde konkret freigegeben. Der unabhängige Offline-Vergleich ist mit PR #49 gemergt und lokal auf 18 realen CC-BY-Aufnahmen ausgeführt. Eine separate Top-5-Hörseite ist lokal umgesetzt und teilweise im Browser geprüft ([Nachweise](docs/retrieval-progress-2026-09-16.md)); musikalische Qualität bleibt offen; neue Live-Veröffentlichungen bleiben separat freigabepflichtig. Einzelne persönliche Hörurteile bleiben lokal.

## Umfang der Dokumentationsrunde

Projektführung und Dokumentation werden auf GitHub-Stand `f5ea2fa` konsolidiert. Keine Funktion wird dadurch als repariert oder veröffentlicht markiert. Die Roadmap ist ein Vorschlag zur nächsten Umsetzung, kein Auftrag zum Start von Backfills, Upgrades oder Deployments.

## Definition von fertig

Ein Arbeitspaket ist fertig, wenn sein Abnahmekriterium erfüllt, angemessen geprüft und dokumentiert ist. Zustände getrennt führen: **vorgeschlagen → umgesetzt → getestet → veröffentlicht**. Für Produktionsbefunde muss die Wirkung im laufenden System bestätigt werden.

Keine Prozentangabe über die Gesamtfertigstellung: alte Phasenpläne und heutiger Funktionsumfang sind nicht deckungsgleich.
