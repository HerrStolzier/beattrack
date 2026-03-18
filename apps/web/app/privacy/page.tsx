import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Datenschutz — Beattrack",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="glass rounded-xl p-6">
      <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-text-secondary">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-surface font-sans text-text-primary">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6">
          <Link
            href="/"
            className="text-sm text-amber transition-colors hover:text-amber-light"
          >
            ← Zurück zur Startseite
          </Link>
        </div>

        <h1 className="font-display mb-2 text-2xl font-bold tracking-tight text-text-primary">
          Datenschutzerklärung
        </h1>
        <p className="mb-8 text-sm text-text-tertiary">Stand: März 2026</p>

        <div className="flex flex-col gap-4">
          {/* 1. Verantwortlicher */}
          <Section title="1. Verantwortlicher">
            <p>
              Verantwortlich im Sinne der DSGVO:
            </p>
            <div className="space-y-1">
              <p className="font-medium text-text-primary">Sebastian Claessens</p>
              <p>c/o IP-Management #9295</p>
              <p>Ludwig-Erhard-Straße 18</p>
              <p>20459 Hamburg</p>
              <p>
                E-Mail:{" "}
                <a
                  href="mailto:dm-basti@pm.me"
                  className="text-amber transition-colors hover:text-amber-light"
                >
                  dm-basti@pm.me
                </a>
              </p>
            </div>
          </Section>

          {/* 2. Überblick */}
          <Section title="2. Überblick der Verarbeitung">
            <p>
              Beattrack ist ein Musikähnlichkeits-Tool. Es werden <strong className="text-text-primary">keine
              Benutzerkonten</strong> angelegt, <strong className="text-text-primary">keine Cookies</strong> gesetzt
              und <strong className="text-text-primary">kein Tracking</strong> durchgeführt. Die Verarbeitung
              beschränkt sich auf die technisch notwendige Bereitstellung des Dienstes.
            </p>
          </Section>

          {/* 3. Hosting & Infrastruktur */}
          <Section title="3. Hosting und Infrastruktur">
            <p>Die Website wird über folgende Dienste betrieben:</p>
            <ul className="list-inside list-disc space-y-2 pl-1">
              <li>
                <strong className="text-text-primary">Vercel Inc.</strong> (San Francisco, USA) — Hosting des
                Frontends. Vercel verarbeitet beim Seitenaufruf technisch notwendige
                Verbindungsdaten (IP-Adresse, Zeitstempel, User-Agent). Rechtsgrundlage:
                Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse). Datenschutzerklärung:{" "}
                <span className="text-text-tertiary">vercel.com/legal/privacy-policy</span>
              </li>
              <li>
                <strong className="text-text-primary">Railway Corp.</strong> (San Francisco, USA) — Hosting des
                Backends (API). Verarbeitet Verbindungsdaten bei API-Anfragen.
                Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO.
              </li>
              <li>
                <strong className="text-text-primary">Supabase Inc.</strong> (Singapur, Hosting: EU-Central/Frankfurt) —
                Datenbank. Speichert Musikmerkmale und anonymes Feedback. Server-Standort
                ist EU (Frankfurt). Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO.
              </li>
            </ul>
            <p>
              Für Datenübermittlungen in die USA stützen sich die Anbieter auf
              EU-Standardvertragsklauseln (Art. 46 Abs. 2 lit. c DSGVO) bzw. das
              EU-U.S. Data Privacy Framework.
            </p>
          </Section>

          {/* 4. Audio-Upload */}
          <Section title="4. Audio-Upload und Analyse">
            <ul className="list-inside list-disc space-y-2 pl-1">
              <li>Hochgeladene Audiodateien werden ausschließlich zur Feature-Extraktion
                (BPM, Tonart, Klangmerkmale) verarbeitet.</li>
              <li>Die Verarbeitung erfolgt serverseitig auf Railway. Die Audiodatei wird
                nach der Analyse (spätestens nach 15 Minuten) automatisch gelöscht.</li>
              <li>Es werden nur die extrahierten numerischen Merkmale (Vektoren)
                gespeichert — keine Audiodaten.</li>
              <li>Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung —
                Bereitstellung des angefragten Dienstes).</li>
            </ul>
          </Section>

          {/* 5. URL-Identifikation */}
          <Section title="5. URL-Identifikation (YouTube, Spotify, SoundCloud, Apple Music)">
            <p>
              Wenn du eine URL eingibst, wird diese an den jeweiligen Dienst
              weitergeleitet, um Metadaten (Titel, Künstler) abzurufen:
            </p>
            <ul className="list-inside list-disc space-y-2 pl-1">
              <li>
                <strong className="text-text-primary">YouTube</strong> — oEmbed-API von Google Ireland Ltd.
                (Gordon House, Dublin 4, Irland).
              </li>
              <li>
                <strong className="text-text-primary">Spotify</strong> — oEmbed-API und Trackseite von
                Spotify AB (Stockholm, Schweden).
              </li>
              <li>
                <strong className="text-text-primary">SoundCloud</strong> — oEmbed-API von SoundCloud Global
                Ltd. (Berlin, Deutschland).
              </li>
              <li>
                <strong className="text-text-primary">Apple Music</strong> — iTunes Search API von Apple Inc.
                (Cupertino, USA). Metadaten werden über die öffentliche Such-API abgerufen.
              </li>
            </ul>
            <p>
              Die URL wird nur zur einmaligen Abfrage verwendet und nicht gespeichert.
              Es werden dabei Verbindungsdaten (IP-Adresse) an den jeweiligen Dienst
              übermittelt. Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO.
            </p>
          </Section>

          {/* 5a. Audio-Fingerprinting */}
          <Section title="5a. Audio-Fingerprinting (AcoustID)">
            <p>
              Beim Upload einer Audiodatei kann zur Identifikation des Songs ein
              Audio-Fingerprint erzeugt und an den Dienst{" "}
              <strong className="text-text-primary">AcoustID</strong> (betrieben von Lukáš Lalinský,
              acoustid.org) gesendet werden. Dabei werden übermittelt:
            </p>
            <ul className="list-inside list-disc space-y-1 pl-1">
              <li>Der berechnete Audio-Fingerprint (Chromaprint)</li>
              <li>Die Dauer der Audiodatei</li>
              <li>Die IP-Adresse des Servers (nicht des Nutzers)</li>
            </ul>
            <p>
              Es werden keine Audiodaten an AcoustID übertragen — nur der numerische
              Fingerprint. Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO (Bereitstellung
              des angefragten Dienstes). Datenschutzerklärung:{" "}
              <span className="text-text-tertiary">acoustid.org/privacy</span>
            </p>
          </Section>

          {/* 6. Musikkatalog */}
          <Section title="6. Musikkatalog (Deezer)">
            <p>
              Der Katalog basiert auf Daten der <strong className="text-text-primary">Deezer SA</strong> (Paris,
              Frankreich). Es werden öffentlich verfügbare Metadaten (Titel, Künstler,
              Album, Genre) und 30-Sekunden-Vorschauen zur einmaligen Feature-Extraktion
              verwendet. Es werden keine Audiodateien dauerhaft gespeichert. Die
              Nutzung erfolgt im Rahmen der Deezer-API-Nutzungsbedingungen.
            </p>
          </Section>

          {/* 6a. Deezer-Vorschau-Player */}
          <Section title="6a. Deezer-Vorschau-Player (Embed)">
            <p>
              Für Songs mit Deezer-ID wird ein Vorschau-Widget der{" "}
              <strong className="text-text-primary">Deezer SA</strong> (24 rue de Calais,
              75009 Paris, Frankreich) eingebettet. Beim Laden des Widgets wird deine
              IP-Adresse an Deezer übermittelt.
            </p>
            <p>
              Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an
              der Bereitstellung einer Vorschau-Funktion). Datenschutzerklärung:{" "}
              <span className="text-text-tertiary">deezer.com/legal/personal-datas</span>
            </p>
          </Section>

          {/* 7. Feedback */}
          <Section title="7. Feedback-Bewertungen">
            <p>
              Wenn du eine Ähnlichkeitsempfehlung bewertest (Daumen hoch/runter), wird
              gespeichert:
            </p>
            <ul className="list-inside list-disc space-y-1 pl-1">
              <li>Die IDs der beiden verglichenen Songs</li>
              <li>Die Bewertung (+1 oder -1)</li>
              <li>Zeitstempel</li>
            </ul>
            <p>
              Es werden keine personenbezogenen Daten gespeichert — kein Benutzerkonto,
              keine IP-Adresse, keine Geräte-ID. Die Daten dienen ausschließlich der
              Qualitätsauswertung. Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO
              (berechtigtes Interesse an der Verbesserung des Dienstes).
            </p>
          </Section>

          {/* 8. Error-Tracking */}
          <Section title="8. Fehlerprotokollierung (Sentry)">
            <p>
              Zur Erkennung und Behebung technischer Fehler kann{" "}
              <strong className="text-text-primary">Sentry</strong> (Functional Software Inc., San Francisco, USA)
              eingesetzt werden. Im Fehlerfall werden technische Informationen
              übermittelt (Fehlermeldung, Browser-Typ, Seitenkontext). Es werden keine
              personenbezogenen Daten wie IP-Adressen oder Nutzerdaten übertragen.
              Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO.
            </p>
          </Section>

          {/* 9. SSL */}
          <Section title="9. SSL/TLS-Verschlüsselung">
            <p>
              Diese Seite nutzt aus Sicherheitsgründen eine SSL/TLS-Verschlüsselung.
              Eine verschlüsselte Verbindung erkennst du an dem Schloss-Symbol in der
              Adresszeile deines Browsers und daran, dass die Adresszeile mit
              &quot;https://&quot; beginnt.
            </p>
          </Section>

          {/* 10. Betroffenenrechte */}
          <Section title="10. Deine Rechte">
            <p>Du hast jederzeit folgende Rechte:</p>
            <ul className="list-inside list-disc space-y-1 pl-1">
              <li><strong className="text-text-primary">Auskunft</strong> (Art. 15 DSGVO) — Welche Daten über dich gespeichert sind</li>
              <li><strong className="text-text-primary">Berichtigung</strong> (Art. 16 DSGVO) — Korrektur unrichtiger Daten</li>
              <li><strong className="text-text-primary">Löschung</strong> (Art. 17 DSGVO) — Löschung deiner Daten</li>
              <li><strong className="text-text-primary">Einschränkung</strong> (Art. 18 DSGVO) — Einschränkung der Verarbeitung</li>
              <li><strong className="text-text-primary">Datenübertragbarkeit</strong> (Art. 20 DSGVO) — Herausgabe deiner Daten</li>
              <li><strong className="text-text-primary">Widerspruch</strong> (Art. 21 DSGVO) — Widerspruch gegen die Verarbeitung</li>
            </ul>
            <p>
              Da Beattrack keine personenbezogenen Daten oder Nutzerkonten speichert,
              sind diese Rechte in der Praxis nur eingeschränkt anwendbar. Wende dich
              bei Fragen an die oben genannte E-Mail-Adresse.
            </p>
          </Section>

          {/* 11. Beschwerderecht */}
          <Section title="11. Beschwerderecht bei einer Aufsichtsbehörde">
            <p>
              Wenn du der Ansicht bist, dass die Verarbeitung deiner Daten gegen die
              DSGVO verstößt, hast du das Recht, dich bei einer Datenschutz-Aufsichtsbehörde
              zu beschweren (Art. 77 DSGVO). Zuständig ist die Aufsichtsbehörde deines
              Bundeslandes oder des Bundeslandes, in dem der Verantwortliche seinen Sitz hat.
            </p>
          </Section>

          {/* 12. Änderungen */}
          <Section title="12. Änderungen dieser Datenschutzerklärung">
            <p>
              Diese Datenschutzerklärung kann bei Bedarf aktualisiert werden, um
              rechtliche Anforderungen oder Änderungen am Dienst abzubilden. Die
              aktuelle Version ist stets unter dieser URL abrufbar.
            </p>
          </Section>
        </div>
      </div>
    </main>
  );
}
