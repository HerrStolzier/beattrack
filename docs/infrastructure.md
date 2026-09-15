# Infrastruktur und Betrieb

Stand: 2026-09-15. Messungen: [Statusbericht](status-2026-09-15.md). Kanonische Serverkonfiguration liegt im separaten [infra-migration-Repository](https://github.com/HerrStolzier/infra-migration), insbesondere [Compose](https://github.com/HerrStolzier/infra-migration/blob/4b2b8dee6e673afba6f5745d4fb967acede8c7f9/stack/docker-compose.yml) und [Serverdokumentation](https://github.com/HerrStolzier/infra-migration/blob/4b2b8dee6e673afba6f5745d4fb967acede8c7f9/docs/server.md). Konfiguration nicht als zweite Compose-Kopie in diesem Repo pflegen.

## Aktuelles Produktionsmodell

- infra-01 bei Hetzner, Helsinki; dokumentierter CX33 mit 4 vCPU, 8 GB RAM und 80 GB Speicher.
- Manueller Docker-Compose-Stack unter /opt/stack; Server-Checkout unter /opt/apps/beattrack.
- Container: beattrack-web, beattrack-api, beattrack-worker, postgrest-beattrack und gemeinsame PostgreSQL.
- Traefik/Coolify-Proxy terminiert TLS und routet /api zur API sowie /rest/v1 zu PostgREST. Coolify selbst ist laut Serverdokumentation kein App-Deployment-Manager.
- API und Worker nutzen ein gemeinsames Upload-Volume; Worker auf eine CPU begrenzt.
- Dokumentierte Speicherlimits und gemessene Ressourcen stehen im Statusbericht, nicht als garantierte Kapazität in diesem Architekturtext.

## Domains und alte Anbieter

Die öffentliche Anwendung ist unter https://beattrack.app erreichbar. Vercel bleibt laut Betreiberdokumentation Registrar/DNS-Anbieter; Railway ist laut Dokumentation gekündigt, die alte API-Adresse antwortete am 15.09. mit „Application not found“.

**Historische Deployment-Einträge, aktueller Trigger ungeklärt:** Basti bestätigt am 15.09.2026, dass Vercel gekündigt ist und Beattrack auf Hetzner läuft. Die Domain wurde erneut mit HTTP 200 vom Hetzner-Server geprüft. GitHub enthält Vercel-Erfolgseinträge vom 07.09. (Preview) und 17.08. (Umgebungsname Production). Die geprüfte Preview-URL leitet heute zur Vercel-Anmeldung weiter. Diese Einträge belegen frühere Statusmeldungen, keinen aktiven kostenpflichtigen Vertrag und keinen heute wirksamen Deployment-Trigger. Production ist hier eine GitHub-Umgebungsbezeichnung, kein Nachweis des Hostings von beattrack.app. Vor Push/Merge bei Bedarf den aktuellen Trigger prüfen; aus historischen Einträgen allein keine zusätzliche Veröffentlichung behaupten. Integrationen nicht eigenständig ändern.

## Zugriff und Geheimnisse

SSH nur mit vorhandenem, autorisiertem Zugang. Keine privaten Schlüssel, IP-bezogenen Zugangsinventare oder Tokenwerte im Repo sammeln. Variablen stehen in der geschützten Serverkonfiguration; Compose-/docker-inspect-Ausgaben können Secrets enthalten und dürfen nicht vollständig in Berichte übernommen werden.

Die FastAPI verwendet in Produktion einen Service-Role-Zugang zu PostgREST; der Browser bekommt diesen Schlüssel nicht. Procrastinate verbindet sich direkt mit PostgreSQL. Namen mit SUPABASE sind Kompatibilitätsnamen, kein Cloud-Zwang.

## Backups, Überwachung und Verfügbarkeit

- Täglicher Datenbankdump um 03:30 Serverzeit, lokale Ablage /opt/backups, Aufbewahrung laut Script sieben Tage.
- Erfolgreicher Beattrack-Dump vom 15.09.2026 wurde geprüft; Restore nicht durchgeführt.
- Zusätzliche Hetzner-VM-Backups sind dokumentiert; aktuelle externe Aufbewahrung nicht separat bestätigt.
- Health-Cron alle zehn Minuten; UptimeRobot dokumentiert, aktuelle Alarmzustellung nicht bestätigt.
- Health liefert einen einfachen Prozessnachweis. Datenbank, Queue, Modell und Benutzerweg müssen gesondert geprüft werden.
- Ein Host ohne geprüftes Ausweichsystem: Ausfall betrifft alle darauf laufenden Dienste. Backup ist kein Hochverfügbarkeitsmechanismus.

Historische Kostenschätzungen sind keine aktuellen Rechnungen. Bei Budgetentscheidungen tatsächlichen Tarif, IPv4, Backups und gemeinsam genutzte Ressourcen neu prüfen.

## Deployment und Rückweg

Siehe [WORKFLOWS.md](../WORKFLOWS.md). Hetzner benötigt Build und Containerersetzung nach dem Git-Update. Ein Merge oder git pull allein veröffentlicht dort nichts. Vorher Zielcommit und bisherige Image-IDs sichern; einen getesteten Rückweg einschließlich Datenbankänderungen planen. Images nicht vorschnell löschen.

Ein Rollback der Anwendung setzt eine kompatible Datenbank voraus. SQL-Änderungen und Massennormalisierung daher unabhängig vom Code-Rollback behandeln. Wiederherstellungen niemals zum Test über die Produktionsdatenbank schreiben.
