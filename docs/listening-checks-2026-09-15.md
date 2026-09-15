# Machbarkeitstest – technische Prüfung am 15.09.2026

**Ergebnis:** Referenzvergleich vorbereitet; keine musikalische Qualitätsabnahme. Änderungen zunächst lokal auf `codex/listening-feasibility`, ausgehend von `421ad65`.

## Daten und Vergleich

- Fünf von Basti bestätigte Aufnahmen: Believe, Deep Down, WHERE IS MY HUSBAND! (House Remix), Bad Habits, Galaxy. Siehe [Protokoll](listening-feasibility.md).
- Drei exakte Katalogtreffer. Zwei fehlende Aufnahmen anhand offizieller Vorschauen temporär analysiert; keine Datenbankeinträge oder Katalogerweiterung.
- Fünfmal 30 Kandidaten einmalig gelesen. Fünfmal 31 Rohmerkmalszeilen (Referenz + Kandidaten) in der Kopie mit derselben eingefrorenen Statistik normalisiert. Keine Normalisierung auf dem Server geschrieben.
- Nach Deduplizierung und Zusammenführung der drei Top-10-Listen: 84 zu bewertende Referenz-/Aufnahmepaare. Gleiches Audio unter mehreren Katalog-IDs bekommt ein gemeinsames Urteil.
- Snapshot: `data/listening/references-2026-09-15/snapshot.json`, SHA256 `a26d5ac8ceadcbe3c8678b5e812045c770bf40825e8bd87406276b92024b2bc8`.
- Finale Hörseite und separater Schlüssel: `data/listening/references-2026-09-15/review-final/` (lokal, nicht in Git). Experiment-ID `d7c98057e20bd865339e364ec1cc1e8259441fddaaf747fd71d9028166f0cec9`.
- Keine ausgefüllten musikalischen Bewertungen. Automatische Tests benutzen ausdrücklich synthetische Urteile.

## Prüfungen

- Backend: 192 pytest-Tests bestanden, zwei bestehende Supabase-Deprecation-Warnungen. Enthält Regression der Einzelroute mit JSON-Textvektoren und tatsächlichem Rangwechsel; fehlendes MERT; ungültige Vektoren; Aufnahme-Dubletten; einzelne/batch Radar-Antworten; reproduzierbare Verblindung; unvollständige Bewertungen.
- Frontend: 70 Vitest-Tests bestanden; Typprüfung und Produktionsbuild bestanden. Lint benötigt lokal wegen bestehender Bun-Hoisting-Struktur den vorhandenen Plugin-Pfad über `NODE_PATH`; danach keine ESLint-Warnungen oder Fehler. Keine Neuinstallation oder Abschaltung des Linters.
- Browser: gebaute Anwendung → Titelsuche „Believe“ per Enter → exakte Aufnahme auswählen → 20 Ergebnisse → „Class X“ zur Playlist hinzufügen und wieder entfernen. Backend-Routen liefen lokal gegen einen Adapter für den eingefrorenen, lokal normalisierten Snapshot. Das ist eine Browserprüfung mit echten Katalogdaten, **kein Live-DB-/Produktions-E2E-Nachweis**.
- Die Dev-Ausgabe lief zunächst nicht interaktiv, weil die bestehende CSP den Entwicklungsmodus mit eval blockiert. Prüfung deshalb mit dem Produktionsbuild; CSP nicht abgeschaltet.
- Bestehender Deezer-iframe blieb im Codex-Browser leer. Der separate Hörvergleich verwendet native Audioelemente und frische Preview-Weiterleitungen. Safari: „Believe“ gestartet, Dauer 29 Sekunden angezeigt, Wiedergabe bis 25 Sekunden fortgeschritten, anschließend pausiert. Das belegt Wiedergabe, keine inhaltliche Hörbewertung.
- Hörformular: eine ausdrücklich synthetische „nicht beurteilbar“-Bewertung über Safari exportiert und mit dem Python-Auswerter eingelesen; Experiment-Zuordnung korrekt, keine Precision für unvollständige Urteile. Testdownload gelöscht, Formular wieder auf 0/84 zurückgesetzt.
- Titelsuche zusätzlich bei 390 × 844 Pixeln visuell geprüft; Auswahlkarten und Plattformhinweise passen in die Breite. Temporäre Browsergröße zurückgesetzt.
- Codex-interner Browser stürzte beim Start nativer Audiowiedergabe ab. Daher Safari für die Hörabnahme verwenden; keine allgemeine Browserkompatibilität behaupten.
- Dokumentstruktur und `git diff --check` geprüft. Der historische doc_drift_check prüft nicht sämtliche Markdown-Links.

## Grenzen und nächster Schritt

1. Basti bewertet zunächst einen Ausgangssong; Teil-Export möglich. Die 84 Paare müssen nicht in einer Sitzung erledigt werden. Bewertungen bei Sitzungsende exportieren.
2. Kommentare und Urteile auswerten; konkrete Klangaspekte und unpassende Vorschauausschnitte festhalten. Kein Rückschluss auf den gesamten Katalog aus dieser kleinen Auswahl.
3. Vor Modell-/Gewichtsentscheidung zusätzliche unabhängige Referenzen verwenden. Bei Hiko/Jerri kein MERT-Vergleich möglich, weil die Referenz-MERT-Vektoren fehlen.
4. Radar-Skalierung, Prozentkommunikation, vollständiger Uploadpfad, katalogweite Normalisierung und echtes Produktions-E2E bleiben offen.
5. Keine Veröffentlichung auf Hetzner. Vor Push/Merge ist die weiterhin aktive Vercel-Veröffentlichung zu beachten: GitHub meldet für den letzten main-Merge `421ad65` ein neues Vercel-Deployment vom 15.09.2026 um 10:41:42 UTC. Freigabe für die jetzigen Funktionsänderungen erforderlich.
