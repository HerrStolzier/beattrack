import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Datenschutz — Beattrack",
};

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

        <h1 className="font-display mb-8 text-2xl font-bold tracking-tight text-text-primary">Datenschutz</h1>

        <div className="flex flex-col gap-4">
          {/* Section 1 */}
          <div className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">Was passiert mit deinem Audio?</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-text-secondary">
              <li>Hochgeladene Audiodateien werden nur temporär verarbeitet.</li>
              <li>Nach der Analyse (max. 15 Minuten) wird die Datei automatisch gelöscht.</li>
              <li>Es wird kein Audio dauerhaft gespeichert.</li>
            </ul>
          </div>

          {/* Section 2 */}
          <div className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">Welche Daten werden gespeichert?</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-text-secondary">
              <li>Nur extrahierte Audio-Features (BPM, Tonart, Klangmerkmale als numerische Vektoren).</li>
              <li>Diese Daten sind keine personenbezogenen Daten — sie beschreiben Musik, nicht Personen.</li>
              <li>Keine IP-Adressen, keine Cookies, keine Tracking-Pixel.</li>
            </ul>
          </div>

          {/* Section 3 */}
          <div className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">Feedback</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-text-secondary">
              <li>Wenn du einen Match bewertest (Daumen hoch/runter), wird die Bewertung anonym gespeichert.</li>
              <li>Es gibt keine User-Accounts und keine Zuordnung zu Personen.</li>
            </ul>
          </div>

          {/* Section 4 */}
          <div className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">YouTube-URLs</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-text-secondary">
              <li>YouTube-URLs werden nur zur Metadaten-Abfrage verwendet (Titel, Künstler).</li>
              <li>Die URL wird nicht gespeichert.</li>
            </ul>
          </div>

          {/* Section 5 */}
          <div className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">Kontakt</h2>
            <p className="text-sm leading-relaxed text-text-secondary">
              Bei Fragen zum Datenschutz: GitHub Issues oder E-Mail.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
