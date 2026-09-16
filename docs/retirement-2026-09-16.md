# Beattrack – Einstellung und Rückbau

Stand: 16.09.2026. Basti hat nach dem letzten Machbarkeitscheck erst die Abschaltung und anschließend Vercel-, Domain- und Infrastruktur-Rückbau ausdrücklich freigegeben.

## Entscheidung

Die Produktentwicklung ist beendet. Für beliebige, auch neue Lieblingssongs wurde unter den Bedingungen „nur Streaming, keine Käufe, unabhängige akustische Analyse, rechtlich belastbarer Zugang“ kein tragfähiger vollständiger Weg nachgewiesen. Das ist kein allgemeiner Beweis technischer oder rechtlicher Unmöglichkeit. Ein begrenzter freier Katalog würde das bestätigte Ziel verändern.

Die bisherigen Pläne und Versuche bleiben als historische Arbeit erhalten. Keine Fortsetzung, Katalogerweiterung, Modellinstallation oder Wiederveröffentlichung aus alten Aufgaben ableiten.

## Rückbau

- Vercel-Projekt `beattrack` samt Deployments, Einstellungen und Projekt-Domainzuordnungen gelöscht; die übrigen Projekte erhalten.
- Automatische Verlängerung von `beattrack.app` abgeschaltet. Angezeigtes Ablaufdatum: **18.03.2027**. Die Registrierung bleibt bis dahin bestehen; keine neue Domain gekauft oder übertragen.
- A-Records für Root-Domain und `www` zum Hetzner-Server entfernt. Verbleibende Standard-DNS-Einträge verwaltet Vercel; keine App ist mit der Domain verbunden.
- Vier Hetzner-Container (`beattrack-web`, `beattrack-api`, `beattrack-worker`, `postgrest-beattrack`) und ihre Compose-Definitionen entfernt.
- Beattrack-spezifische Images, Upload-Volume `stack_uploads` und Datenbank `beattrack` nach Sicherungsprüfung entfernt.
- Server-Checkout und eindeutig Beattrack-spezifische Hilfsscripts archiviert. Gemeinsame Datenbankrollen, PostgreSQL, Proxy und PostgREST-Image bleiben für andere Projekte erhalten.
- Beattrack aus dem gemeinsamen Backup-Script und den Gesundheitsprüfungen entfernt; übrige Prüfungen und Backups bleiben aktiv. Cron-Datei heißt jetzt `stack-health`.
- UptimeRobot-Monitore „beattrack API“ und „beattrack.app“ pausiert; historische Statistiken erhalten. Hund-Monitor bleibt aktiv.
- GitHub Actions werden nach dem abschließenden Dokumentations-Merge deaktiviert und das Repository archiviert. Code wird nicht gelöscht.

## Sicherung und Prüfung

Serverarchiv: `/opt/archive/beattrack-retired-20260916` (nur für den Administrator zugänglich). Enthält aktuellen PostgreSQL-Dump, Upload-Archiv, Server-Checkout und private Betriebsinformationen. Diese Inhalte gehören nicht in Git.

Lokales Archiv: `/Users/basti/Beattrack-Archiv-2026-09-16`. Enthält außerdem ein geprüftes Git-Bundle mit sämtlichen lokalen Referenzen, einschließlich noch nicht gemergter Arbeit.

Die Sicherung wurde in eine separate temporäre Datenbank zurückgespielt: **Schema und Daten aller 9 Tabellen importiert; Zeilenzahlen aller Tabellen mit der Quelldatenbank identisch; `public.songs`: 588.707 Zeilen.** Post-Data-Objekte wie Indizes und Constraints wurden bei diesem Test nicht neu aufgebaut. Das ist eine Datenwiederherstellungsprüfung, keine vollständige Betriebsabnahme. Die Testdatenbank wurde anschließend entfernt.

SHA-256-Prüfsummen für Datenbankdump, Checkout-Archiv und Upload-Archiv liegen in `SHA256SUMS`. Der lokale Transfer wird gegen diese Prüfsummen geprüft.

Die verbleibenden Compose-Dienste wurden vor/nach der Änderung strukturell verglichen und sind unverändert. Kein Neustart der gemeinsam genutzten Dienste. Hund-Webseite und der tatsächliche ICG-REST-Pfad `/rest/v1/` antworteten mit HTTP 200. Die alte ICG-Basisadresse ohne REST-Pfad liefert 503 und ist kein geeigneter Funktionscheck.

## Grenzen

- Domainregistrierung läuft erst am genannten Datum aus; eine sofortige Freigabe der Domain wurde nicht vorgenommen.
- Gemeinsamer Hetzner-Server und dessen Kosten bleiben wegen anderer Projekte bestehen. Bestehende Sicherungen werden nicht pauschal gelöscht.
- Lokale Forschungsdaten und Quellcode bleiben erhalten; keine pauschale Löschung unbekannter Dateien oder gemeinsamer Entwicklungswerkzeuge.
- Frühere Railway-/Supabase-Kündigungen bzw. Löschungen sind historische Betriebsnachweise, keine in dieser Runde erneut vorgenommenen Kontoaktionen.
- Wiederinbetriebnahme benötigt einen neuen ausdrücklichen Auftrag sowie eine neue Quellen-, Lizenz- und Betriebsprüfung.
