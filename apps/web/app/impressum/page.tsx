import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Impressum — Beattrack",
};

export default function ImpressumPage() {
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

        <h1 className="font-display mb-8 text-2xl font-bold tracking-tight text-text-primary">
          Impressum
        </h1>

        <div className="flex flex-col gap-4">
          {/* Angaben gemäß § 5 TMG */}
          <section className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">
              Angaben gemäß § 5 DDG
            </h2>
            <div className="space-y-1 text-sm leading-relaxed text-text-secondary">
              <p className="font-medium text-text-primary">Sebastian Claessens</p>
              <p>c/o IP-Management #9295</p>
              <p>Ludwig-Erhard-Straße 18</p>
              <p>20459 Hamburg</p>
              <p>Deutschland</p>
            </div>
          </section>

          {/* Kontakt */}
          <section className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">
              Kontakt
            </h2>
            <div className="space-y-1 text-sm leading-relaxed text-text-secondary">
              <p>
                E-Mail:{" "}
                <a
                  href="mailto:dm-basti@pm.me"
                  className="text-amber transition-colors hover:text-amber-light"
                >
                  dm-basti@pm.me
                </a>
              </p>
              <p>Telefon: 017655389114</p>
            </div>
          </section>

          {/* Verantwortlich für den Inhalt */}
          <section className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">
              Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV
            </h2>
            <div className="space-y-1 text-sm leading-relaxed text-text-secondary">
              <p className="font-medium text-text-primary">Sebastian Claessens</p>
              <p>c/o IP-Management #9295</p>
              <p>Ludwig-Erhard-Straße 18</p>
              <p>20459 Hamburg</p>
            </div>
          </section>

          {/* Haftungsausschluss */}
          <section className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">
              Haftung für Inhalte
            </h2>
            <p className="text-sm leading-relaxed text-text-secondary">
              Die Inhalte dieser Seite wurden mit größter Sorgfalt erstellt. Für die
              Richtigkeit, Vollständigkeit und Aktualität der Inhalte kann jedoch keine
              Gewähr übernommen werden. Als Diensteanbieter bin ich gemäß § 7 Abs. 1 DDG
              für eigene Inhalte auf diesen Seiten nach den allgemeinen Gesetzen
              verantwortlich. Nach §§ 8 bis 10 DDG bin ich als Diensteanbieter jedoch
              nicht verpflichtet, übermittelte oder gespeicherte fremde Informationen zu
              überwachen oder nach Umständen zu forschen, die auf eine rechtswidrige
              Tätigkeit hinweisen.
            </p>
          </section>

          {/* Haftung für Links */}
          <section className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">
              Haftung für Links
            </h2>
            <p className="text-sm leading-relaxed text-text-secondary">
              Diese Seite enthält Links zu externen Webseiten Dritter, auf deren Inhalte
              ich keinen Einfluss habe. Für die Inhalte der verlinkten Seiten ist stets
              der jeweilige Anbieter oder Betreiber verantwortlich. Eine permanente
              inhaltliche Kontrolle der verlinkten Seiten ist ohne konkrete Anhaltspunkte
              einer Rechtsverletzung nicht zumutbar. Bei Bekanntwerden von
              Rechtsverletzungen werde ich derartige Links umgehend entfernen.
            </p>
          </section>

          {/* Urheberrecht */}
          <section className="glass rounded-xl p-6">
            <h2 className="font-display mb-3 text-lg font-semibold text-text-primary">
              Urheberrecht
            </h2>
            <p className="text-sm leading-relaxed text-text-secondary">
              Die Audiodaten im Katalog stammen aus öffentlich zugänglichen
              Vorschau-Snippets der Deezer-API und dienen ausschließlich der
              Feature-Extraktion für die Ähnlichkeitssuche. Es werden keine
              Audiodateien dauerhaft gespeichert oder zum Streaming bereitgestellt.
              Die Rechte an den Musikwerken liegen bei den jeweiligen Rechteinhabern.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
