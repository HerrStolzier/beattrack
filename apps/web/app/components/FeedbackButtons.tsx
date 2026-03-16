"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { submitFeedback } from "@/lib/api";

interface FeedbackButtonsProps {
  querySongId: string;
  resultSongId: string;
  onFeedback?: (rating: 1 | -1) => void;
}

function CheckIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function XIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
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

  async function handleClick(rating: 1 | -1) {
    if (loading || selected !== null) return;
    setLoading(true);
    setError(false);
    try {
      await submitFeedback(querySongId, resultSongId, rating);
      setSelected(rating);
      onFeedback?.(rating);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  if (selected !== null) {
    return (
      <motion.span
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-medium ${
          selected === 1
            ? "bg-emerald-dim text-emerald"
            : "bg-rose-dim text-rose"
        }`}
      >
        {selected === 1 ? <CheckIcon /> : <XIcon />}
        {selected === 1 ? "Passend" : "Unpassend"}
      </motion.span>
    );
  }

  return (
    <div className="flex items-center gap-1">
      {error && <span className="text-[10px] text-red-400">Fehler</span>}
      <button
        onClick={() => handleClick(1)}
        disabled={loading}
        className="inline-flex items-center gap-1 rounded-full border border-border-subtle px-2 py-1 text-[10px] text-text-tertiary transition hover:border-emerald/30 hover:bg-emerald-dim hover:text-emerald disabled:opacity-40"
        title="Passender Treffer"
      >
        <CheckIcon />
        <span>Passend</span>
      </button>
      <button
        onClick={() => handleClick(-1)}
        disabled={loading}
        className="inline-flex items-center gap-1 rounded-full border border-border-subtle px-2 py-1 text-[10px] text-text-tertiary transition hover:border-rose/30 hover:bg-rose-dim hover:text-rose disabled:opacity-40"
        title="Unpassender Treffer"
      >
        <XIcon />
        <span>Unpassend</span>
      </button>
    </div>
  );
}
