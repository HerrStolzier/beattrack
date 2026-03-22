import type { Metadata } from "next";
import { Syne, DM_Sans, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ToastProvider } from "./components/Toast";
import MouseGlow from "./components/MouseGlow";
import MeshGradient from "./components/MeshGradient";
import LensDistortion from "./components/LensDistortion";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  weight: ["700", "800"],
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  weight: ["400", "500", "600"],
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "700"],
});

const baseUrl = "https://beattrack.app";

export const metadata: Metadata = {
  title: {
    default: "Beattrack — Finde deinen nächsten Track",
    template: "%s — Beattrack",
  },
  description:
    "Finde klanglich ähnliche Songs durch Audio-Analyse. Paste eine YouTube, Spotify oder SoundCloud URL oder lade eine Audio-Datei hoch.",
  metadataBase: new URL(baseUrl),
  alternates: { canonical: "/" },
  openGraph: {
    title: "Beattrack — Finde deinen nächsten Track",
    description:
      "Finde klanglich ähnliche Songs durch Audio-Analyse. Über 50.000 Electronic-Tracks analysiert.",
    url: baseUrl,
    siteName: "Beattrack",
    locale: "de_DE",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Beattrack — Finde deinen nächsten Track",
    description:
      "Finde klanglich ähnliche Songs durch Audio-Analyse. Paste eine URL oder lade Audio hoch.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

// JSON-LD structured data — static, no user input, safe for inline rendering
const jsonLd = JSON.stringify({
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Beattrack",
  url: baseUrl,
  description:
    "Finde klanglich ähnliche Songs durch Audio-Analyse mit über 50.000 Electronic-Tracks.",
  applicationCategory: "MusicApplication",
  operatingSystem: "Web",
  inLanguage: "de",
  offers: { "@type": "Offer", price: "0", priceCurrency: "EUR" },
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <head>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd }} />
      </head>
      <body className={`${syne.variable} ${dmSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <MeshGradient />
        <MouseGlow />
        <LensDistortion />
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
