"use client";

import { useState } from "react";
import { submitFeedback } from "@/lib/api";

interface FeedbackButtonsProps {
  querySongId: string;
  resultSongId: string;
  onFeedback?: (rating: 1 | -1) => void;
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

  return (
    <div className="flex items-center gap-1">
      {error && <span className="text-xs text-red-400">Failed</span>}
      <button
        onClick={() => handleClick(1)}
        disabled={loading || selected !== null}
        className={`rounded border border-border-subtle px-2 py-1 text-sm transition ${
          selected === 1
            ? "bg-amber/30 text-amber-light"
            : "text-text-tertiary hover:bg-amber-dim hover:text-text-secondary disabled:opacity-40"
        }`}
        title="Helpful"
      >
        👍
      </button>
      <button
        onClick={() => handleClick(-1)}
        disabled={loading || selected !== null}
        className={`rounded border border-border-subtle px-2 py-1 text-sm transition ${
          selected === -1
            ? "bg-red-500/30 text-red-400"
            : "text-text-tertiary hover:bg-red-500/15 hover:text-text-secondary disabled:opacity-40"
        }`}
        title="Not helpful"
      >
        👎
      </button>
    </div>
  );
}
