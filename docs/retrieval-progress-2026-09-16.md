# Unabhängiger Audiomodellvergleich – 16.09.2026

## Ergebnis und Auftrag

Endziel als aktives Ziel gesetzt; Umsetzung beauftragt. Die separate lokale Python-Installation und Downloads für MERT/CLAP wurden ausdrücklich freigegeben. Umsetzung des Retrieval-Kerns mit delegate-work an Sol Low delegiert und hier integriert. Kein Hetzner-Deployment, keine Änderung der Produktionsumgebung.

## Umgesetzt

- [retrieval.py](../apps/api/scripts/listening/retrieval.py): unabhängiger exakter Kosinusvergleich im gesamten zulässigen Bestand je Split. Keine Vorauswahl, Fusion oder MMR. Vollständige Ranglisten, optional Ränge bestätigter Positiver, Abdeckung und Input-Fingerprints.
- Manifest trennt Aufnahmeidentität von Aufnahmefamilie: dieselbe Aufnahme ist kein Treffer für sich selbst; verschiedene Remixe bleiben unterscheidbar. Familien und Künstlergruppen dürfen Entwicklung/Test nicht verbinden.
- Fehlende/ungültige Vektoren und voneinander abweichende Audio-Prüfsummen/Zeitbereiche werden abgewiesen. Quellenberechtigungen sind dokumentierte Erklärungen, keine automatische Rechtsprüfung.
- [encode.py](../apps/api/scripts/listening/encode.py): lokale Dateien und explizite Ausschnitte für MusiCNN, MERT und CLAP verarbeiten; kein automatischer Download. Quellen- und Dateiprüfung vor Analyse, reproduzierbare Vorverarbeitung, getrennte Decodier-/Inferenzzeiten. Ausgaben enthalten Audiosegment-Nachweise. Lauf auf CPU.

## Lokaler Betriebsstand

Umgebung: `data/listening/runtime/.venv`, getrennt von API/Web. Bibliotheken und Modelle unter ignoriertem `data/`; installierte Versionen in `requirements-frozen.txt` daneben. Zum Installationszeitpunkt ca. 1,8 GB inklusive Modellcache; keine Cloudressourcen.

- torch 2.14.0, transformers 4.57.6, numpy 2.5.3; bestehendes Essentia/MusiCNN läuft weiter in `apps/api/.venv`.
- MERT-v1-95M Revision `12af15fef9d0ac838c3f475bfbbf26d2060dd4f5`.
- CLAP larger_clap_music Revision `a0b4534a14f58e20944452dff00a22a06ce629d1`.
- MERT Custom-Code lokal gelesen; Modell wird nur aus lokalem Snapshot geladen. Für Modellupdates erneute Prüfung und neue Revision. nnAudio-Warnung beim Import, aber der geprüfte Modellpfad benötigt die optionale CQT-Erweiterung nicht.

## Prüfung und Aussagegrenze

Alle drei echten Encoder haben dieselben zwei synthetischen Sinusdateien aus `phase0/fixtures` über explizite Drei-Sekunden-Ausschnitte verarbeitet: MusiCNN 200, MERT 768, CLAP 512 Dimensionen. Der gemeinsame CLI-Vergleich akzeptierte deren identische Audiosegment-Nachweise und erzeugte Ranglisten. Artefakte: `data/listening/runtime/synthetic-*.json`.

Das belegt lokale Ausführbarkeit und den technischen Datenweg, **keine musikalische Qualität**. Kein echter Hörvergleich, kein Lasttest, keine Produktions-E2E-Abnahme. Einzelne Laufzeiten aus synthetischen Kurzsignalen sind keine Katalogdauer- oder Kostenprognose. 14 gezielte Tests bestanden; sie prüfen abweichende Audiobasis, Leakage, fehlende Vektoren, ungültige Zahlen, Remixe und Encoder-Preflight; keine neue Komplettprüfung unveränderter Frontendpfade.

## Audioquellen: konkrete Recherche

Offizielle [MTG-Jamendo-Daten](https://github.com/MTG/mtg-jamendo-dataset) einschließlich `audio_licenses.txt`, `raw.meta.tsv` und `raw_30s_cleantags_50artists.tsv` lokal gelesen. Schnittmenge aus ausgewiesener CC-BY-Lizenz und Electronic/House/Techno-Tags: **1.048 Aufnahmen von 133 Künstlergruppen**, darunter **312 mit House-/Techno-Tag**. Diese Tags helfen bei der Bestandsauswahl, nicht beim späteren Ranking.

Metadaten und vorläufige Kandidaten liegen unter `data/listening/source-audit-2026-09-16/`. Inzwischen wurden 18 Aufnahmen des unten beschriebenen technischen Piloten heruntergeladen und gegen offizielle Track-Prüfsummen geprüft. Die Quellenzuordnung stützt sich auf die veröffentlichten Datensatz-Lizenzzeilen; keine zusätzliche individuelle Rechtezusage der Künstler. Geeignete musikalische Beispiele für die Zielabnahme bleiben zu prüfen. [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) beschreibt die Bedingungen; daraus folgt keine pauschale Prüfung aller gelieferten Aufnahmen. Die bisherigen Deezer-Referenzen erhalten dadurch keine zusätzliche Nutzungserlaubnis.

## Verwendung

Das vollständige Manifest-/Embedding-Schema steht im Modultext von retrieval.py. Encoder benötigt zusätzlich pro Aufnahme `path`, relativ zum Manifest oder absolut. Manifest enthält Audio-SHA256 sowie Start und Dauer (Encoder: 3–30 Sekunden). Modellgewichte vorher explizit lokal bereitstellen; bei MusiCNN ist die Revision die SHA256 der PB-Datei.

```sh
python apps/api/scripts/listening/encode.py MANIFEST.json --model mert --weights LOCAL_SNAPSHOT --revision PINNED_REVISION --output mert.json
python apps/api/scripts/listening/retrieval.py MANIFEST.json --embeddings musicnn=musicnn.json --embeddings mert=mert.json --embeddings clap=clap.json --output report.json
```

Für MERT/CLAP den Interpreter der neuen Umgebung verwenden, für MusiCNN den der API. Für das neue unabhängige Top-5-Protokoll gibt es eine separate Hörseite, siehe unten. Die alte Top-10-Seite und ihre Urteile bleiben ein eigener historischer Versuch; alte Urteile sind keine neuen Modellurteile.

## Nächste erforderliche Nachweise

1. Nutzbaren Audio-Pilotbestand abschließen; zulässige Referenzquellen klären.
2. Zwei positive Vergleichssongs wurden von Basti bestätigt und lokal erfasst; deren Audioquellen und unabhängige zusätzliche Referenzen bleiben offen.
3. Einen kleinen realen Analysepilot samt Quellenmanifest durchführen, dann faire Bestände einfrieren.
4. Top-5-Hörvergleich anbinden und musikalischen Vorteil auf neuen Referenzen prüfen.

E1–E6 bleiben offen. Keine automatische Modellwahl, kein Training und kein Katalogbackfill aus dem synthetischen Test ableiten.


## Reale Musikpipeline und Hörseite – weiterer Nachweis am 16.09.

**Lokal umgesetzt und geprüft, noch nicht veröffentlicht.** PR #49 mit dem Retrieval-Kern und den Encodern ist zuvor als `4afe25e` gemergt worden; CI und Vercel melden Erfolg. Die neue Hörseite gehört nicht zu diesem veröffentlichten Stand. Kein Hetzner-Deployment.

### Technischer Musikpilot

18 CC-BY-Aufnahmen von 16 Künstlergruppen aus dem offiziellen MTG-Jamendo-Archiv `raw_30s_audio-23.tar`. Auswahl vor Modellläufen: alle 19 Electronic-/House-/Techno-Kandidaten dieses Archivs, abzüglich einer einzelnen Datei über dem lokalen 35-MB-Downloadlimit. Das ist eine praktische, **nicht repräsentative** Pilotstichprobe. Genre-Tags werden nicht fürs Ranking verwendet. Zugriff über HTTP-Teilabrufe am offiziellen Freesound-Mirror; jede MP3 stimmt mit `raw_30s_audio_sha256_tracks.txt` überein. Audio insgesamt 261.180.379 Bytes, keine vollständigen Archive gespeichert.

Für alle Modelle exakt dieselben zehn Sekunden ab 00:45. Drei vor der Analyse festgelegte Pilotreferenzen, sämtliche Aufnahmen im Entwicklungssplit. Keine bestätigten Positiven, keine unbenutzte Gegenprobe, keine Nutzerurteile. Alle drei Modelle lieferten 18 gültige Vektoren und je Referenz 17 unabhängige Kandidatenbewertungen. Die vereinigten Top-5 ergeben insgesamt 32 zu bewertende Paare.

| Modell | Prozessdauer für 18 Ausschnitte einschließlich Import/Modellladen |
|---|---:|
| MusiCNN | 3,29 s |
| MERT-95M | 8,83 s |
| CLAP | 4,35 s |

Ein einzelner lokaler CPU-Lauf mit bereits vorhandenen Gewichten. Keine belastbare Hochrechnung auf Hetzner, Vollsongs oder Katalogkosten; RAM-Spitzen und Lastbetrieb noch nicht gemessen. Artefakte unter `data/listening/source-audit-2026-09-16/pilot-run/`: Manifest, Modellvektoren, Logs, Laufzeiten, Report und vorbereitete Hörseite. Quellenbelege und Download-Prüfsummen liegen im übergeordneten Verzeichnis.

### Neuer Hörtest

- [review_retrieval.py](../apps/api/scripts/listening/review_retrieval.py) erstellt lokale Hörproben aus den manifestierten Ausschnitten. Vollständiger Manifest-Hash, Audiofingerprint, IDs, Quellenprüfsumme und tatsächliche Clipdauer werden geprüft. Doppelte Query-Ergebnisse, Selbsttreffer und Split-Übertritte werden abgewiesen.
- [review_retrieval.html](../apps/api/scripts/listening/review_retrieval.html) mischt die Top-5-Vereinigung deterministisch. Verfahren, Rang und Score erscheinen nicht. Titel/Künstler erst nach Klangurteil; Attribution und Lizenzen sind zusätzlich jederzeit zugänglich, wodurch die Verblindung bewusst begrenzt bleibt. Lokal exportieren und gültige Bewertungen atomar importieren.
- [serve_local.py](../apps/api/scripts/listening/serve_local.py) bindet ausschließlich an Loopback und liefert nur die Seite und vorbereitete Clips. Schlüssel und Quelldateien werden nicht ausgeliefert.
- Auswertung: Precision@5 nur bei fünf beurteilbaren Treffern. Eine Entdeckung zählt nur bei **passend + vorher unbekannt + merkenswert**. Fehlende Antworten sind kein negatives Urteil.

```sh
python3 apps/api/scripts/listening/review_retrieval.py prepare MANIFEST.json REPORT.json NEW_REVIEW_DIR
python3 apps/api/scripts/listening/serve_local.py NEW_REVIEW_DIR --port 8110
python3 apps/api/scripts/listening/review_retrieval.py assess NEW_REVIEW_DIR/key.json RATINGS.json
```

Das Manifest benötigt zusätzlich `title`, `artist`, `source_path` (absoluter lokaler Pfad), `attribution`, `license`; optional `review_note` für sichtbare Versuchsgrenzen. Für den vorhandenen Pilot `NEW_REVIEW_DIR` durch `data/listening/source-audit-2026-09-16/pilot-run/review` ersetzen und nur den Server starten. Vorbereitung überschreibt keine vorhandenen Versuche.

### Prüfung und Grenzen

31 gezielte Tests bestanden: Retrieval, Encoder-Preflight und neue Hörseite einschließlich realem synthetischem FFmpeg-/FFprobe-Durchlauf und HTTP-Zugriffsgrenzen. Zusätzlich echte MP3 → drei Encoder → unabhängige Ranglisten → lokale WAV-Hörseite ausgeführt.

Safari: Referenz spielte bis 10/10 Sekunden, Testauswahl erhöhte den Fortschritt von 0 auf 1 und zeigte Titel/Attribution; Screenshot auf Darstellung geprüft. Der Codex-In-App-Browser stürzte beim Play-Klick ab. Safari-Export erreichte eine Download-Berechtigungsabfrage; diese wurde abgebrochen, keine Browsereinstellung geändert. Exportdatei und erneuter UI-Import sind daher **nicht Ende-zu-Ende verifiziert**. Keine Testbewertung als echtes Hörurteil gespeichert. Safari-Testtab geschlossen und lokaler Testserver beendet; der abgestürzte In-App-Testtab ließ sich wegen einer Werkzeug-URL-Sperre nicht explizit schließen.

Weiterhin entscheidend: nutzbare Audioquelle für die bestätigten Lieblingssongs/Positiven, fairer größerer Bestand, Hörurteile und unbenutzte Referenzen. Der CC-Pilot ersetzt diese Anforderungen nicht und rechtfertigt weder Modellwahl noch Training oder Backfill.

## Quellenentscheidung nach direkter Bedingungenprüfung

Die [Quellenentscheidung](audio-source-decision-2026-09-16.md) hält die aktuelle Deezer-Mining-Beschränkung und zulässige nächste Prüfschritte fest. Für die Zielaufnahmen ist kein neuer Audioabruf erfolgt. Vorhandene lokale Dateien sind angefragt; ein kostenpflichtiger Bezug oder externer Kontakt wurde nicht ausgelöst.
