"use client";

import { motion } from "framer-motion";
import AnalyzeView from "./components/AnalyzeView";
import ApiStatus from "./components/ApiStatus";
import AudioWaveform from "./components/AudioWaveform";

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const },
  }),
};

export default function Home() {
  return (
    <main className="ambient-glow flex min-h-screen flex-col font-sans text-text-primary">
      <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <ApiStatus />

        {/* Header */}
        <motion.header
          className="mb-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
          initial="hidden"
          animate="visible"
          variants={fadeInUp}
          custom={0}
        >
          <div className="flex items-center gap-6">
            <div>
              <motion.h1
                className="font-display text-5xl font-extrabold tracking-tight md:text-7xl"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
              >
                <a
                  href="/"
                  className="bg-gradient-to-r from-amber via-gold to-amber-light bg-[length:200%_auto] bg-clip-text text-transparent animate-gradient-shift transition-opacity hover:opacity-80"
                >
                  Beattrack
                </a>
              </motion.h1>
              <motion.p
                className="mt-2 text-base text-text-secondary"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.6 }}
              >
                Finde deinen nächsten Track
              </motion.p>
            </div>
            <AudioWaveform className="hidden sm:flex" />
          </div>
        </motion.header>

        {/* Gradient divider */}
        <div className="mb-8 h-px bg-gradient-to-r from-transparent via-amber/30 to-transparent" />

        {/* Main content — URL identify + file upload */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          <AnalyzeView />
        </motion.div>
      </div>

      <footer className="mx-auto mt-auto w-full max-w-6xl px-4 py-8">
        <div className="h-px bg-gradient-to-r from-transparent via-border-glass to-transparent" />
        <div className="flex items-center justify-between pt-6">
          <p className="text-xs text-text-tertiary">Beattrack — Finde deinen nächsten Track</p>
          <div className="flex gap-4">
            <a href="/impressum" className="text-xs text-text-tertiary transition-colors hover:text-amber-light">
              Impressum
            </a>
            <a href="/privacy" className="text-xs text-text-tertiary transition-colors hover:text-amber-light">
              Datenschutz
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}
