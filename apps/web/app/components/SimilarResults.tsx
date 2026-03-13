"use client";

import { type Song, type SimilarSong } from "@/lib/api";
import FeedbackButtons from "./FeedbackButtons";

interface SimilarResultsProps {
  results: SimilarSong[];
  querySong: Song;
  onFeedback?: (querySongId: string, resultSongId: string, rating: 1 | -1) => void;
}

function similarityColor(score: number): string {
  // score 0..1 — interpolate red -> yellow -> green
  if (score >= 0.7) return "from-emerald-600 to-emerald-400";
  if (score >= 0.4) return "from-yellow-600 to-yellow-400";
  return "from-red-600 to-red-400";
}

export default function SimilarResults({ results, querySong, onFeedback }: SimilarResultsProps) {
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-zinc-300">
        Similar to{" "}
        <span className="text-zinc-100">{querySong.title}</span>
      </h2>

      {results.length === 0 && (
        <p className="text-xs text-zinc-500">No similar songs found.</p>
      )}

      <ul className="flex flex-col gap-3">
        {results.map((song) => {
          const pct = Math.round(song.similarity * 100);
          return (
            <li
              key={song.id}
              className="rounded-xl border border-zinc-800 bg-zinc-900 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-100">
                    {song.title}
                  </p>
                  <p className="truncate text-xs text-zinc-400">{song.artist}</p>
                </div>
                <span className="shrink-0 text-xs font-semibold text-zinc-300">
                  {pct}%
                </span>
              </div>

              {/* Similarity bar */}
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${similarityColor(song.similarity)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              <div className="mt-2 flex items-center justify-end">
                <FeedbackButtons
                  querySongId={querySong.id}
                  resultSongId={song.id}
                  onFeedback={(rating) => onFeedback?.(querySong.id, song.id, rating)}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
