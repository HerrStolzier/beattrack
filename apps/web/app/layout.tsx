import type { Metadata } from "next";
import { Syne, DM_Sans } from "next/font/google";
import "./globals.css";
import { ToastProvider } from "./components/Toast";
import MouseGlow from "./components/MouseGlow";
import MeshGradient from "./components/MeshGradient";

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

export const metadata: Metadata = {
  title: "Beattrack",
  description: "Finde klanglich ähnliche Songs durch Audio-Analyse",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className={`${syne.variable} ${dmSans.variable} font-sans antialiased`}>
        <MeshGradient />
        <MouseGlow />
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
