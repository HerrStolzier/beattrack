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

Metadaten und vorläufige Kandidaten liegen unter `data/listening/source-audit-2026-09-16/`. Keine Audiodateien dieses Bestands heruntergeladen. Individuelle Quellenzuordnung, Attribution, tatsächlich zugängliche Audiodateien und geeignete musikalische Beispiele bleiben zu prüfen. [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) beschreibt die Bedingungen; daraus folgt keine pauschale Prüfung aller gelieferten Aufnahmen. Die bisherigen Deezer-Referenzen erhalten dadurch keine zusätzliche Nutzungserlaubnis.

## Verwendung

Das vollständige Manifest-/Embedding-Schema steht im Modultext von retrieval.py. Encoder benötigt zusätzlich pro Aufnahme `path`, relativ zum Manifest oder absolut. Manifest enthält Audio-SHA256 sowie Start und Dauer (Encoder: 3–30 Sekunden). Modellgewichte vorher explizit lokal bereitstellen; bei MusiCNN ist die Revision die SHA256 der PB-Datei.

```sh
python apps/api/scripts/listening/encode.py MANIFEST.json --model mert --weights LOCAL_SNAPSHOT --revision PINNED_REVISION --output mert.json
python apps/api/scripts/listening/retrieval.py MANIFEST.json --embeddings musicnn=musicnn.json --embeddings mert=mert.json --embeddings clap=clap.json --output report.json
```

Für MERT/CLAP den Interpreter der neuen Umgebung verwenden, für MusiCNN den der API. Die bestehende Top-10-Hörseite/assess-Auswertung ist noch nicht an dieses neue unabhängige Top-5-Protokoll angeschlossen. Keine Kompatibilität vortäuschen und keine alten Urteile als neue Modellurteile verwenden.

## Nächste erforderliche Nachweise

1. Nutzbaren Audio-Pilotbestand abschließen; zulässige Referenzquellen klären.
2. Zwei positive Vergleichssongs wurden von Basti bestätigt und lokal erfasst; deren Audioquellen und unabhängige zusätzliche Referenzen bleiben offen.
3. Einen kleinen realen Analysepilot samt Quellenmanifest durchführen, dann faire Bestände einfrieren.
4. Top-5-Hörvergleich anbinden und musikalischen Vorteil auf neuen Referenzen prüfen.

E1–E6 bleiben offen. Keine automatische Modellwahl, kein Training und kein Katalogbackfill aus dem synthetischen Test ableiten.
