"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { HistoryEntry } from "@/app/hooks/useSessionHistory";

interface SessionHistoryProps {
  history: HistoryEntry[];
  onClear: () => void;
}

function relativeTime(timestamp: number): string {
  const diff = Math.floor((Date.now() - timestamp) / 1000);
  if (diff < 60) return "gerade eben";
  if (diff < 3600) return `vor ${Math.floor(diff / 60)} Min.`;
  if (diff < 86400) return `vor ${Math.floor(diff / 3600)} Std.`;
  return `vor ${Math.floor(diff / 86400)} Tag${Math.floor(diff / 86400) === 1 ? "" : "en"}`;
}

function TypeIcon({ type }: { type: HistoryEntry["type"] }) {
  if (type === "upload") {
    return (
      <svg className="h-3.5 w-3.5 shrink-0 text-amber-light" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    );
  }
  if (type === "url") {
    return (
      <svg className="h-3.5 w-3.5 shrink-0 text-cyan" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
      </svg>
    );
  }
  if (type === "blend") {
    return (
      <svg className="h-3.5 w-3.5 shrink-0 text-amber" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="9" cy="12" r="6" />
        <circle cx="15" cy="12" r="6" />
      </svg>
    );
  }
  // vibe
  return (
    <svg className="h-3.5 w-3.5 shrink-0 text-violet" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" fill="currentColor" stroke="none" />
      <circle cx="18" cy="16" r="3" fill="currentColor" stroke="none" />
    </svg>
  );
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function SessionHistory({ history, onClear }: SessionHistoryProps) {
  if (history.length === 0) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">Verlauf</h3>
        <button
          onClick={onClear}
          className="text-[10px] text-text-tertiary hover:text-error transition-colors"
        >
          Verlauf löschen
        </button>
      </div>

      <AnimatePresence>
        <motion.ul
          className="flex flex-col gap-1.5"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {history.map((entry) => (
            <motion.li
              key={entry.id}
              variants={itemVariants}
              className="flex items-center gap-2.5 rounded-lg border border-border-subtle bg-surface-glass/40 px-3 py-2"
            >
              <TypeIcon type={entry.type} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium text-text-primary">{entry.query}</p>
                {entry.topResult && (
                  <p className="truncate text-[10px] text-text-tertiary">
                    Top: {entry.topResult.artist} — {entry.topResult.title}
                  </p>
                )}
              </div>
              <div className="shrink-0 text-right">
                <p className="text-[10px] text-text-tertiary">{relativeTime(entry.timestamp)}</p>
                <p className="text-[10px] text-text-tertiary">{entry.resultCount} Treffer</p>
              </div>
            </motion.li>
          ))}
        </motion.ul>
      </AnimatePresence>
    </div>
  );
}
