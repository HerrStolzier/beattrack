import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Datenschutz — Beattrack",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-zinc-950 font-[var(--font-space-grotesk)] text-zinc-100">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6">
          <Link
            href="/"
            className="text-sm text-zinc-500 transition-colors hover:text-zinc-300"
          >
            ← Zurück zur Startseite
          </Link>
        </div>

        <h1 className="mb-8 text-2xl font-bold tracking-tight text-zinc-100">Datenschutz</h1>

        <div className="flex flex-col gap-4">
          {/* Section 1 */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
            <h2 className="mb-3 text-lg font-semibold text-zinc-100">Was passiert mit deinem Audio?</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-zinc-400">
              <li>Hochgeladene Audiodateien werden nur temporär verarbeitet.</li>
              <li>Nach der Analyse (max. 15 Minuten) wird die Datei automatisch gelöscht.</li>
              <li>Es wird kein Audio dauerhaft gespeichert.</li>
            </ul>
          </div>

          {/* Section 2 */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
            <h2 className="mb-3 text-lg font-semibold text-zinc-100">Welche Daten werden gespeichert?</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-zinc-400">
              <li>Nur extrahierte Audio-Features (BPM, Tonart, Klangmerkmale als numerische Vektoren).</li>
              <li>Diese Daten sind keine personenbezogenen Daten — sie beschreiben Musik, nicht Personen.</li>
              <li>Keine IP-Adressen, keine Cookies, keine Tracking-Pixel.</li>
            </ul>
          </div>

          {/* Section 3 */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
            <h2 className="mb-3 text-lg font-semibold text-zinc-100">Feedback</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-zinc-400">
              <li>Wenn du einen Match bewertest (Daumen hoch/runter), wird die Bewertung anonym gespeichert.</li>
              <li>Es gibt keine User-Accounts und keine Zuordnung zu Personen.</li>
            </ul>
          </div>

          {/* Section 4 */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
            <h2 className="mb-3 text-lg font-semibold text-zinc-100">YouTube-URLs</h2>
            <ul className="space-y-2 text-sm leading-relaxed text-zinc-400">
              <li>YouTube-URLs werden nur zur Metadaten-Abfrage verwendet (Titel, Künstler).</li>
              <li>Die URL wird nicht gespeichert.</li>
            </ul>
          </div>

          {/* Section 5 */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6">
            <h2 className="mb-3 text-lg font-semibold text-zinc-100">Kontakt</h2>
            <p className="text-sm leading-relaxed text-zinc-400">
              Bei Fragen zum Datenschutz: GitHub Issues oder E-Mail.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
