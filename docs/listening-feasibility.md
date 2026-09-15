# Lieblingssong → klanglich passende Entdeckungen

Stand: 2026-09-15 · **Aktives Ziel. Technische Vorbereitung umgesetzt; Hörurteile und unabhängige Gegenprobe offen.**

## Bestätigte Vision

Basti hat als Kern gewählt: „Einen Lieblingssong eingeben und wirklich ähnlich klingende Musik entdecken.“ Erfolg ist ein hörbar passender, interessanter Fund. Gleiche Genres, hohe Scores, funktionierende Requests oder zusätzliche Modelle belegen diesen Erfolg allein nicht.

## Ablauf und Entscheidung

1. Fünf Referenzaufnahmen identifizieren; den wichtigen Klangaspekt/Abschnitt festhalten.
2. Verfälschende Verarbeitungsfehler reparieren und mit realistischen Datenformaten testen.
3. Einen eingefrorenen Kandidatenbestand mit unterschiedlichen Verfahren bewerten und verdeckt anhören.
4. Fehler trennen: falsche Aufnahme, fehlender Kataloginhalt, unpassender Ausschnitt, schlechte Kandidatensuche oder schlechte Sortierung.
5. Auf zusätzlichen, vorher nicht zum Abstimmen verwendeten Songs gegenprüfen. Erst dann Gewichte, Datenaufbau oder Modellaufwand priorisieren.

Kein automatischer Qualitätsentscheid. Das zuvor diskutierte Ziel von drei passenden Top-10-Treffern bei acht von zehn Songs war ein Vorschlag, keine Prognose und kein mit fünf Songs prüfbares Erfolgskriterium. Zunächst Ausgangsniveau und konkrete Fehlermuster beschreiben.

## Referenzen

Die von Basti gelieferten Album-Links wurden über die Deezer-API aufgelöst. Basti hat die Titeltracks „Believe“ und „Deep Down“ für die beiden EPs ausdrücklich bestätigt. Die anderen Links enthalten jeweils einen Track. Klangaspekte/Abschnitte sind noch nicht benannt.

| Aufnahme | Deezer Track-ID | Exakte Aufnahme im Katalog am 15.09. |
|---|---:|---|
| Eli Brown – Believe | 1607099422 | vorhanden |
| Eli Brown – Deep Down | 2255159817 | vorhanden |
| Hiko – WHERE IS MY HUSBAND! (House Remix) | 3605490262 | fehlt |
| Jerri – Bad Habits | 3771836032 | fehlt |
| Paul van Dyk – Galaxy | 2347884865 | vorhanden |

Quellen: [Believe](https://api.deezer.com/album/284078032), [Deep Down](https://api.deezer.com/album/434163207), [Hiko](https://api.deezer.com/album/839085032), [Jerri](https://api.deezer.com/album/896680432), [Galaxy](https://api.deezer.com/album/459081125). Katalogmitgliedschaft wurde zusätzlich direkt per Deezer-ID in der Datenbank gelesen; ähnliche Titel anderer Künstler wurden nicht als Ersatz verwendet.

Für Hiko und Jerri wurden ausschließlich die offiziellen Vorschauen temporär im bestehenden Worker analysiert. Die Dateien wurden im TemporaryDirectory aufgeräumt. Kein Ingest, keine Nachbarerweiterung, keine Produktionsschreiboperation. Der Snapshot enthält Merkmale und Preview-Prüfsummen, keine Audiodateien oder Zugangsdaten.

## Vergleichsprotokoll

Werkzeuge: [capture.py](../apps/api/scripts/listening/capture.py), [experiment.py](../apps/api/scripts/listening/experiment.py), [serve.py](../apps/api/scripts/listening/serve.py).

- Einmalig maximal 30 MusiCNN-Kandidaten pro Ausgangssong erfassen. Alle Varianten verwenden exakt diesen Bestand.
- Handcrafted-Rohmerkmale ausschließlich in der lokalen Kopie mit derselben eingefrorenen `normalization_stats`-Konfiguration normalisieren. Bestehende normalisierte Vektoren werden im Versuch nicht mit neu berechneten Skalen vermischt.
- Drei Varianten: MusiCNN; MusiCNN + Handcrafted; zusätzlich MERT, soweit verfügbar. Der gemeinsame Scorer stammt aus der Anwendung. Fehlende Signale werden pro Kandidat behandelt und im separaten Schlüssel ausgewiesen.
- Genre-Feedbackgewichte, MMR und die Ausgabeschwelle der Anwendung sind für diesen isolierten Vergleich ausgeschaltet. Deshalb ist dies **kein identischer Nachbau der gesamten Live-Suche**. Er misst zunächst die Sortierung innerhalb des MusiCNN-Kandidatenbestands. Kandidaten außerhalb dieses Bestands können damit nicht entdeckt oder beurteilt werden.
- Pro Variante Top 10 nach derselben Deduplizierung: Aufnahme-ID sowie bisherige Künstler-/Basistitelregel. Diese Regel kann unterschiedliche Remixe zusammenfassen; die spätere Höranalyse muss solche Verluste berücksichtigen.
- Gemeinsame Treffer nur einmal bewerten. Verfahren, Scores und Rangplätze verbergen; Titel/Künstler bleiben sichtbar. Die Aufnahmedubletten können verschiedene Katalog-IDs haben: Bewertungen müssen dann gemeinsam zugeordnet werden.
- Reproduzierbare zufällige Reihenfolge; Hashes von Snapshot und Scoring-Code kennzeichnen den Versuch. Keine Gewichtsänderung mitten in einer Bewertungsrunde.
- Getrennte Urteile: klanglich passend / teilweise / nein / nicht beurteilbar; schon bekannt; würde ich merken; optionale Begründung.
- Nicht beurteilbare oder fehlende Bewertungen sind keine negativen Stimmen. Precision@10 nur ausgeben, wenn zehn zurückgegebene Vorschläge tatsächlich beurteilt wurden. Kein statistischer Überlegenheitsnachweis aus fünf ausgewählten Songs.

**Wichtige Grenzen:** Für die neu analysierten Hiko-/Jerri-Referenzen fehlt MERT. Dort sind zweite und dritte Variante identisch und kein MERT-Vergleich. Auch bei den anderen Referenzen ist MERT nicht für jeden Kandidaten verfügbar. Fünfmal 31 Merkmalszeilen konnten lokal normalisiert werden; das belegt keine katalogweite Normalisierung. Vorschau- und Vollsongähnlichkeit sind getrennte Fragen.

## Lokaler Ablauf

Vorhandene API-Python-Umgebung verwenden, keine neue Installation nötig. Aus dem Repository-Root:

```sh
# Capture nur in einer bereits konfigurierten API-Umgebung; Ausgabe nicht ins Git.
# UUIDs: reine Kataloglektüre. deezer:ID nur mit --allow-preview-analysis:
PYTHONPATH=apps/api apps/api/.venv/bin/python apps/api/scripts/listening/capture.py UUID > data/listening/snapshot.json

# Aus eingefrorenem Snapshot ein neues, noch nicht bestehendes Verzeichnis erzeugen:
PYTHONPATH=apps/api apps/api/.venv/bin/python apps/api/scripts/listening/experiment.py prepare data/listening/snapshot.json data/listening/review
python3 apps/api/scripts/listening/serve.py data/listening/review --port 8108

# Exportierte Bewertungen auswerten:
PYTHONPATH=apps/api apps/api/.venv/bin/python apps/api/scripts/listening/experiment.py assess data/listening/review/key.json data/listening/ratings.json
```

Der Server bindet ausschließlich an Loopback. Er liefert nur das Formular und leitet für dessen gelistete Track-IDs auf frische offizielle Preview-URLs weiter. Audio streamt direkt vom Deezer-CDN; Schlüssel und Snapshot werden nicht ausgeliefert. Keine Bewertungen werden gesendet. Formular vor dem Schließen exportieren; auch Teilbewertungen sind möglich. Für eine neue Sitzung nach einem Teil-Export ist die Übernahme der bisherigen Bewertungen noch manuell.

Aktuelle lokale Artefakte liegen unter `data/listening/references-2026-09-15/` (absichtlich durch `data/` ignoriert). `snapshot.json` bleibt eingefroren; das jeweilige finale Review-Verzeichnis wird im Prüfbericht benannt. Generierte Daten und persönliche Hörurteile gehören nicht automatisch in das öffentliche Git-Repository.

## Technischer Stand und verbleibende Arbeit

Umgesetzt: gültige PostgREST-Textvektoren parsen; ungültige optionale Vektoren isolieren; kandidatenspezifische Gewichtung; doppelte Deezer-Aufnahmen entfernen; Titelsuche mit Aufnahmewahl; verständlicher Fehler nach fehlgeschlagener Ähnlichkeitssuche; einzelne/batch Radar-Endpunkte akzeptieren Textvektoren.

Offen: musikalische Hörurteile, unabhängige Referenzen, Live-Veröffentlichung, katalogweite Merkmalskonsistenz. Die inhaltliche Radar-Skalierung und bestehende Prozentdarstellung sind weiterhin ungeprüft bzw. problematisch; der Hörvergleich zeigt sie bewusst nicht. Die bestehenden Deezer-Widgets der Anwendung konnten im Codex-Browser nicht zur Wiedergabe gebracht werden; der separate Hörvergleich spielt native Audio-Vorschauen in Safari.
