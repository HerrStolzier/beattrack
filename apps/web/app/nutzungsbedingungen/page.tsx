import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Nutzungsbedingungen — Beattrack",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="glass rounded-xl p-6">
      <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-text-secondary">{children}</div>
    </section>
  );
}

export default function NutzungsbedingungenPage() {
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
          Nutzungsbedingungen
        </h1>
        <p className="mb-8 text-sm text-text-tertiary">Stand: März 2026</p>

        <div className="flex flex-col gap-4">
          <Section title="1. Beschreibung des Dienstes">
            <p>
              Beattrack ist ein kostenloser Musikähnlichkeits-Dienst, der auf Basis
              automatisierter Audio-Analyse ähnlich klingende Songs vorschlägt. Der
              Dienst wird ohne Gewähr auf Verfügbarkeit, Vollständigkeit oder Richtigkeit
              der Ergebnisse bereitgestellt.
            </p>
          </Section>

          <Section title="2. Erlaubte Nutzung">
            <p>Die Nutzung von Beattrack ist ausschließlich für legale Zwecke gestattet. Untersagt ist insbesondere:</p>
            <ul className="list-inside list-disc space-y-1 pl-1">
              <li>Automatisiertes Scraping oder Crawling der Website oder API</li>
              <li>Übermäßige oder missbräuchliche API-Nutzung</li>
              <li>Nutzung zur Umgehung von Urheberrechten oder Lizenzvereinbarungen</li>
              <li>Weiterverkauf oder kommerzielle Verwertung der Analyseergebnisse</li>
            </ul>
          </Section>

          <Section title="3. Audio-Upload">
            <p>
              Beim Hochladen einer Audiodatei bestätigst du, dass du die erforderlichen
              Rechte an dem Material besitzt oder die Nutzung anderweitig zulässig ist
              (z.B. Fair Use, eigene Aufnahmen, lizenzierte Inhalte). Beattrack übernimmt
              keine Verantwortung für urheberrechtlich geschütztes Material, das von
              Nutzern hochgeladen wird.
            </p>
            <p>
              Hochgeladene Audiodateien werden ausschließlich zur einmaligen Analyse
              verwendet und spätestens nach 15 Minuten automatisch gelöscht.
            </p>
          </Section>

          <Section title="4. Haftungsbeschränkung">
            <p>
              Die Ähnlichkeitsempfehlungen basieren auf automatisierter Audio-Analyse
              und stellen keine redaktionelle Bewertung dar. Die Ergebnisse können
              ungenau oder unvollständig sein. Beattrack übernimmt keine Gewähr für
              die Qualität, Richtigkeit oder Vollständigkeit der Empfehlungen.
            </p>
            <p>
              Eine Haftung für Schäden, die aus der Nutzung des Dienstes entstehen,
              ist — soweit gesetzlich zulässig — ausgeschlossen.
            </p>
          </Section>

          <Section title="5. Verfügbarkeit">
            <p>
              Beattrack wird als kostenloser Dienst ohne Verfügbarkeitsgarantie
              betrieben. Der Dienst kann jederzeit ohne Vorankündigung eingeschränkt,
              verändert oder eingestellt werden.
            </p>
          </Section>

          <Section title="6. Änderungsvorbehalt">
            <p>
              Diese Nutzungsbedingungen können jederzeit angepasst werden. Die
              aktuelle Version ist stets unter dieser URL abrufbar. Durch die
              weitere Nutzung des Dienstes nach einer Änderung akzeptierst du
              die aktualisierte Fassung.
            </p>
          </Section>

          <Section title="7. Geltendes Recht">
            <p>
              Es gilt das Recht der Bundesrepublik Deutschland. Gerichtsstand
              ist — soweit gesetzlich zulässig — Hamburg.
            </p>
          </Section>
        </div>
      </div>
    </main>
  );
}
