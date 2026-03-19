"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { submitFeedback } from "@/lib/api";

interface FeedbackButtonsProps {
  querySongId: string;
  resultSongId: string;
  onFeedback?: (rating: 1 | -1) => void;
}

// Particle burst positions (relative offsets)
const PARTICLES = Array.from({ length: 8 }, (_, i) => {
  const angle = (i / 8) * Math.PI * 2;
  return { x: Math.cos(angle) * 28, y: Math.sin(angle) * 28 };
});

function ParticleBurst({ color }: { color: string }) {
  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
      {PARTICLES.map((p, i) => (
        <motion.span
          key={i}
          className="absolute h-1 w-1 rounded-full"
          style={{ backgroundColor: color }}
          initial={{ x: 0, y: 0, opacity: 1, scale: 1.5 }}
          animate={{ x: p.x, y: p.y, opacity: 0, scale: 0 }}
          transition={{ duration: 0.5, delay: i * 0.02, ease: "easeOut" }}
        />
      ))}
    </div>
  );
}

export default function FeedbackButtons({
  querySongId,
  resultSongId,
  onFeedback,
}: FeedbackButtonsProps) {
  const [selected, setSelected] = useState<1 | -1 | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [burst, setBurst] = useState<1 | -1 | null>(null);

  async function handleClick(rating: 1 | -1) {
    if (loading || selected !== null) return;
    setLoading(true);
    setError(false);
    setBurst(rating);
    try {
      await submitFeedback(querySongId, resultSongId, rating);
      setSelected(rating);
      onFeedback?.(rating);
    } catch {
      setError(true);
      setBurst(null);
    } finally {
      setLoading(false);
    }
  }

  // After selection: show confirmed state
  if (selected !== null) {
    return (
      <motion.div
        className="flex w-full items-center justify-center gap-3"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
      >
        <div
          className={`relative flex items-center gap-2 rounded-xl px-5 py-2.5 text-xs font-semibold ${
            selected === 1
              ? "bg-emerald/15 text-emerald shadow-[0_0_20px_rgba(52,211,153,0.2)]"
              : "bg-rose/15 text-rose shadow-[0_0_20px_rgba(251,113,133,0.2)]"
          }`}
        >
          {selected === 1 ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          )}
          {selected === 1 ? "Guter Match!" : "Passt nicht"}
        </div>
      </motion.div>
    );
  }

  return (
    <div className="flex w-full items-center justify-center gap-3">
      {error && (
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-xs text-red-400"
        >
          Fehler
        </motion.span>
      )}

      {/* PASS button */}
      <motion.button
        onClick={() => handleClick(1)}
        disabled={loading}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.92 }}
        className="group relative flex cursor-pointer items-center gap-2.5 overflow-hidden rounded-xl border border-emerald/20 bg-emerald/5 px-5 py-2.5 text-xs font-semibold text-emerald/80 transition-all duration-200 hover:border-emerald/40 hover:bg-emerald/10 hover:text-emerald hover:shadow-[0_0_24px_rgba(52,211,153,0.15)] disabled:opacity-40"
        title="Passend"
      >
        <AnimatePresence>
          {burst === 1 && <ParticleBurst color="#34d399" />}
        </AnimatePresence>
        <svg className="relative z-10 h-5 w-5 transition-transform duration-200 group-hover:scale-110" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M7.5 12.5 10.5 15.5 16.5 9.5" /></svg>
        <span className="relative z-10">Passt</span>
        <div className="absolute inset-0 bg-gradient-to-r from-emerald/0 via-emerald/5 to-emerald/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      </motion.button>

      {/* FAIL button */}
      <motion.button
        onClick={() => handleClick(-1)}
        disabled={loading}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.92 }}
        className="group relative flex cursor-pointer items-center gap-2.5 overflow-hidden rounded-xl border border-rose/20 bg-rose/5 px-5 py-2.5 text-xs font-semibold text-rose/80 transition-all duration-200 hover:border-rose/40 hover:bg-rose/10 hover:text-rose hover:shadow-[0_0_24px_rgba(251,113,133,0.15)] disabled:opacity-40"
        title="Unpassend"
      >
        <AnimatePresence>
          {burst === -1 && <ParticleBurst color="#fb7185" />}
        </AnimatePresence>
        <svg className="relative z-10 h-5 w-5 transition-transform duration-200 group-hover:scale-110" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="16" y1="8" x2="8" y2="16" /><line x1="8" y1="8" x2="16" y2="16" /></svg>
        <span className="relative z-10">Passt nicht</span>
        <div className="absolute inset-0 bg-gradient-to-r from-rose/0 via-rose/5 to-rose/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      </motion.button>
    </div>
  );
}
