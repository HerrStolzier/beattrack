# Lieblingssong → klanglich passende Entdeckungen

> **Eingestellt am 16.09.2026 auf Nutzerauftrag.** Die Entwicklung wird nicht fortgesetzt. Frühere Ziele und Pläne sind historisch, kein aktiver Umsetzungsauftrag. [Rückbau und Nachweise](retirement-2026-09-16.md).

Stand: 2026-09-15 · **Plan nach unabhängigem Review aktualisiert. Bisheriger Nachsortierungsversuch vorbereitet; eigenständiger Modellvergleich noch nicht umgesetzt.**

## Bestätigte Vision

Basti hat als Kern gewählt: „Einen Lieblingssong eingeben und wirklich ähnlich klingende Musik entdecken.“ Erfolg ist ein hörbar passender, interessanter Fund. Gleiche Genres, hohe Scores, funktionierende Requests oder zusätzliche Modelle belegen diesen Erfolg allein nicht.

## Zielpräzisierung und Planentscheidung

Gelernte Muster aus Audio sollen die Suche tragen. Tempo, Basshärte und Vorwärtsdrang sind Beschreibungen von Fehlertypen, keine neuen handgebauten Rankingregeln. Ein neuronaler Encoder allein garantiert keine wahrgenommene Ähnlichkeit: Trainingsziel, Ausschnitt und Suchverfahren müssen gemeinsam geprüft werden.

Der unabhängige Astra-High-Review vom 15.09. bestätigt einen begrenzten Versuch mit vortrainierten Modellen. Er begründet weder eigenes Training noch einen Katalogumbau. Code, Modellkarten und Literatur wurden geprüft; neue Modelle und deren Rechenbedarf wurden nicht ausgeführt beziehungsweise gemessen. Der aktuelle Auftrag aktualisiert die Planung und startet keine neue Analyse, Installation oder Veröffentlichung.

## Neuer Ablauf mit Entscheidungspunkten

### P0 – Nutzbaren Audiobestand sichern

Für jede Quelle dokumentieren, ob Analyse, Speicherung, Hörtest und gegebenenfalls Training abgedeckt sind. Öffentlich abspielbare Vorschauen sind kein Nachweis dafür. Anbieterbedingungen und etwaige Vereinbarungen prüfen; alternativ ausdrücklich freigegebenes Künstler-/Labelmaterial oder passend lizenzierte Aufnahmen verwenden. Modellgewichte und Audiomaterial getrennt betrachten. Die [konkrete Quellenprüfung vom 16.09.](audio-source-decision-2026-09-16.md) behandelt die ausdrückliche Mining-Beschränkung bei Deezer und die noch offenen Alternativen für den Zielversuch.

**Weiter, wenn:** die vorgesehene Verarbeitung für den Versuch abgedeckt ist. Sonst Quelle wechseln oder den Versuch ausdrücklich auf einen freigegebenen Bestand begrenzen. Keine Aussage über beliebige Lieblingssongs aus einem eingeschränkten Katalog ableiten.

### P1 – Positive Beispiele und unabhängigen Bestand vorbereiten

Die fünf bisherigen Referenzen sind Entwicklungsfälle. Verschiedene Songs als passende Vergleichspaare bestätigen; schwierige Negative und unabhängig ausgewählte Hintergrundtitel ergänzen. Unbewertete Aufnahmen bleiben unbewertet. Original, Remix, Remaster und Ausschnitte derselben Aufnahmefamilie bleiben gemeinsam in Entwicklung oder Test; möglichst auch Künstler trennen. Die beiden Eli-Brown-Songs sind keine unabhängigen Künstlerfälle.

**Umfangsvorschlag, keine Mindestgröße:** fünf neue Referenzen und zwei getrennte Suchbestände mit jeweils 150–300 Aufnahmen. Je Entwicklungsreferenz möglichst ein bis zwei bestätigte Positive. Umfang nach Audiozugang und Hörbudget begrenzen. Bekannte Positive dienen der Diagnose und zählen nicht als neue Entdeckungen.

**Weiter, wenn:** passende und unpassende Beispiele in verdeckten Wiederholungen hinreichend stabil beurteilt werden. Sonst Referenzabschnitt oder Suchziel präzisieren. Ohne positive Beispiele kein Tripeltraining.

### P2 – Drei eigenständige Suchverfahren vergleichen

Startvorschlag: bestehendes MusiCNN als Ausgangsniveau, MERT-v1-95M und CLAP `laion/larger_clap_music`. Jedes Modell durchsucht denselben vollständigen zulässigen Bestand per exaktem Vektorvergleich. Keine MusiCNN-Vorauswahl, handgewichtete Fusion, BPM-Filter oder MMR im isolierten Vergleich. Neue Suchinfrastruktur ist dafür nicht erforderlich.

Quellaudio und Zeitbereiche gleich halten; modellgerechte Vorverarbeitung verwenden. Modellrevision, Schicht, Pooling, Normalisierung und Ausschnitte einfrieren. Fehlende Vektoren und Fehler sichtbar zählen, kein stiller Ersatz durch ein anderes Modell. Identische Aufnahmen zusammenführen; verschiedene Remixe nicht allein wegen des Basistitels entfernen. Unbekannte Überlappung mit dem ursprünglichen Modelltraining als Grenze nennen.

**Weiter, wenn:** alle Verfahren auf vergleichbarer Basis laufen. Andernfalls technische oder Datenprobleme lösen, bevor Qualität verglichen wird.

### P3 – Hörqualität und Entdeckungsnutzen prüfen

Top 5 je Verfahren und Entwicklungsreferenz ergeben höchstens 75 einzigartige Paare. Die Vereinigung entsteht erst nach unabhängiger Suche. Methode, Rang und Score sowie möglichst Titel/Künstler zunächst verbergen. Vergleichbare Wiedergabelautheit ohne klangverändernde Kompression; einige verdeckte Wiederholungen. Persönliche Urteile bleiben lokal.

Danach nur den gewählten Herausforderer gegen MusiCNN auf fünf unbenutzten Referenzen prüfen: höchstens 50 weitere Paare. Insgesamt höchstens 125 Paare zuzüglich positiver Bestätigungspaare und Wiederholungen; Überschneidungen senken den Aufwand. Kein Anspruch, dass diese Größen statistisch genügen.

Messen: Rang bestätigter Positiver; vollständig bewertete passende Top-5-Treffer; unbekannte, passende und merkenswerte Funde; Gewinne/Verluste pro Referenz und Künstlergruppe; Wiederholungsstabilität. Fehlende oder nicht beurteilbare Urteile sind keine negativen Stimmen. Vorschauähnlichkeit und Vollsongähnlichkeit getrennt ausweisen.

**Vor dem Versuch festzulegen:** Nutzenschwelle und Hör-/Rechenbudget. Review-Vorschlag: mindestens zwei unbekannte, passende und merkenswerte Top-5-Treffer bei mindestens drei von fünf neuen Referenzen und insgesamt mehr solche Funde als MusiCNN. Das ist keine bestätigte Nutzervorgabe oder Erfolgsprognose. Der frühere Top-10-Vorschlag ist ebenfalls nicht beschlossen.

**Entscheidung:** Bei Vorteil größeren Bestand prüfen. Werden nur bekannte Positive gefunden, bleibt Entdeckungsnutzen offen. Scheitern alle Modelle, genau einen begründeten Diagnosezweig wählen: Bestand, anderer Abschnitt oder zusätzlicher Encoder. Bleibt ein Vorteil aus, den Ansatz beenden oder auf eine belegte Teilaufgabe begrenzen. Ein zur Auswahl verwendeter Test ist danach nicht mehr unangetastet.

### P4 – Nur begründete Erweiterungen

- **Abschnitte:** Bei verfügbarem Vollaudio mehrere festgelegte Zeitbereiche symmetrisch vergleichen. Ein zweiter Abschnitt soll den Vorteil bestätigen. Fehlendes Audio kann ein Modell nicht rekonstruieren.
- **Training:** Erst bei stabilen Urteilen, vorhandenen Positiven und systematischen Rankingfehlern eine kleine regularisierte Projektion versuchen. Nach Song-/Künstlergruppen trennen, dann Tripel bilden. Gegen denselben Encoder ohne Projektion auf unbenutzten Songs prüfen. Kein Gewinn außerhalb des Trainings: Trainingszweig beenden.
- **Weitere Modelle:** MuQ-MuLan oder MERIT nur mit konkreter Hypothese hinzufügen. MERITs Instrumentklassen sind kein Nachweis für Basshärte. Keine nachträgliche Auswahl günstiger Gewichtsmischungen am Testsatz.
- **Betrieb:** Kaltstart, warme Analyse, Decodierung, Suche, RAM/GPU-Speicher, Durchsatz, Fehler und Vektorspeicher messen. Erst dann Aufwand hochrechnen. Kein pauschaler GPU-Server und kein Training eines Grundmodells von null.
- **Katalogumbau:** Erst bei hörbarem Nutzen, geklärter Nutzung und akzeptablem gemessenem Aufwand; versionierter Rückweg und konkrete Veröffentlichungsfreigabe erforderlich.

## Modellquellen und Grenzen

| Kandidat | Rolle und Stand laut Review | Nutzungsgrenze laut Veröffentlichung |
|---|---|---|
| MusiCNN / MTG | Bestehende Vergleichsbasis | MTG nennt CC BY-NC-SA bzw. gesonderte Lizenzierung; konkreten Modellstand prüfen |
| MERT-v1-95M | Vorhandene Repräsentation unabhängig suchen lassen | CC BY-NC 4.0 |
| CLAP larger_clap_music | Anders trainierter Gegenkandidat mit verfügbaren Gewichten | Modellkarte Apache-2.0; anderer Checkpoint als in der zitierten Wahrnehmungsstudie |
| MuQ-MuLan-large | Optionaler zweiter Versuch | Gewichte CC BY-NC 4.0, Code separat |
| MERIT | Optionale getrennte Rhythmus-/Klangfarbenprüfung | Köpfe MIT; MERT-330M-Basis separat CC BY-NC |
| MULE | Für ersten Versuch zurückgestellt | Gewichte CC BY-NC, Code GPL-3.0 |

Quellen: [Essentia-Modelle](https://essentia.upf.edu/models.html), [MERT](https://huggingface.co/m-a-p/MERT-v1-95M), [CLAP](https://huggingface.co/laion/larger_clap_music), [MuQ-MuLan](https://huggingface.co/OpenMuQ/MuQ-MuLan-large), [MERIT](https://huggingface.co/amaai-lab/merit), [MERT-330M](https://huggingface.co/m-a-p/MERT-v1-330M), [MULE](https://github.com/PandoraMedia/music-audio-representations).

Forschungsgrenzen: Die [CLAP/MuQ-Wahrnehmungsstudie](https://arxiv.org/html/2601.19109v1) verwendet kurze Ausschnitte synthetischer Musik. [MERIT](https://arxiv.org/html/2605.27346v1) prüft unter anderem Instrumentklassen und ausgewählte Trainingspaare. Beides belegt keine Entdeckungsqualität für Beattracks Referenzen. Audioquelle gesondert anhand der [Deezer-Bedingungen](https://www.deezer.com/legal/cgu) und [Entwicklerbedingungen](https://developers.deezer.com/termsofuse) beziehungsweise eigener Erlaubnisse prüfen; keine pauschale rechtliche Freigabe aus diesem Plan ableiten.

## Referenzen

Die von Basti gelieferten Album-Links wurden über die Deezer-API aufgelöst. Basti hat die Titeltracks „Believe“ und „Deep Down“ für die beiden EPs ausdrücklich bestätigt. Die anderen Links enthalten jeweils einen Track. Einzelne qualitative Fehlerbeschreibungen liegen vor; zwei positive Vergleichssongs wurden am 16.09. bestätigt und lokal erfasst; genaue Referenzabschnitte und nutzbare Audiodateien bleiben offen. Persönliche Einzelbewertungen bleiben in den lokalen Versuchsdaten.

| Aufnahme | Deezer Track-ID | Exakte Aufnahme im Katalog am 15.09. |
|---|---:|---|
| Eli Brown – Believe | 1607099422 | vorhanden |
| Eli Brown – Deep Down | 2255159817 | vorhanden |
| Hiko – WHERE IS MY HUSBAND! (House Remix) | 3605490262 | fehlt |
| Jerri – Bad Habits | 3771836032 | fehlt |
| Paul van Dyk – Galaxy | 2347884865 | vorhanden |

Quellen: [Believe](https://api.deezer.com/album/284078032), [Deep Down](https://api.deezer.com/album/434163207), [Hiko](https://api.deezer.com/album/839085032), [Jerri](https://api.deezer.com/album/896680432), [Galaxy](https://api.deezer.com/album/459081125). Katalogmitgliedschaft wurde zusätzlich direkt per Deezer-ID in der Datenbank gelesen; ähnliche Titel anderer Künstler wurden nicht als Ersatz verwendet.

Für Hiko und Jerri wurden ausschließlich die offiziellen Vorschauen temporär im bestehenden Worker analysiert. Die Dateien wurden im TemporaryDirectory aufgeräumt. Kein Ingest, keine Nachbarerweiterung, keine Produktionsschreiboperation. Der Snapshot enthält Merkmale und Preview-Prüfsummen, keine Audiodateien oder Zugangsdaten.

## Bisheriger Versuch – Nachsortierung (historisches Protokoll)

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

## Lokaler Ablauf des bisherigen Versuchs

Diese Werkzeuge implementieren noch nicht P0–P4. Vor erneuter Audioerfassung die vorgesehene Nutzung gemäß P0 klären. Vorhandene API-Python-Umgebung verwenden, keine neue Installation nötig. Aus dem Repository-Root:

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

Offen: vollständige musikalische Abnahme, unabhängige Referenzen und Modellsuche, Audioquellenklärung, gemessener Modellaufwand und katalogweite Merkmalskonsistenz. Technische Änderungen wurden mit PR #48 gemergt; Vercel meldete für Merge ca02e7c am 15.09. eine abgeschlossene Veröffentlichung. Kein Hetzner-Deployment in dieser Runde. Die inhaltliche Radar-Skalierung und bestehende Prozentdarstellung sind weiterhin ungeprüft bzw. problematisch; der Hörvergleich zeigt sie bewusst nicht. Die bestehenden Deezer-Widgets der Anwendung konnten im Codex-Browser nicht zur Wiedergabe gebracht werden; der separate Hörvergleich spielt native Audio-Vorschauen in Safari.
