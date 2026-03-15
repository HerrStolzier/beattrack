"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { type Song, type SimilarSong } from "@/lib/api";
import FeedbackButtons from "./FeedbackButtons";
import RadarChart from "./RadarChart";

interface SimilarResultsProps {
  results: SimilarSong[];
  querySong: Song;
  onFeedback?: (querySongId: string, resultSongId: string, rating: 1 | -1) => void;
}

function similarityColor(score: number): string {
  if (score >= 0.7) return "from-amber to-gold";
  if (score >= 0.4) return "from-amber-light to-amber";
  return "from-red-500 to-red-400";
}

function formatDuration(sec: number | null | undefined): string {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function searchUrl(platform: "spotify" | "youtube", artist: string, title: string): string {
  const q = encodeURIComponent(`${artist} ${title}`);
  if (platform === "spotify") {
    return `https://open.spotify.com/search/${q}`;
  }
  return `https://www.youtube.com/results?search_query=${q}`;
}

const listVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function SimilarResults({ results, querySong, onFeedback }: SimilarResultsProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-text-secondary">
        Ähnlich wie{" "}
        <span className="text-text-primary">{querySong.title}</span>
      </h2>

      {results.length === 0 && (
        <p className="text-xs text-text-secondary">Keine ähnlichen Songs gefunden.</p>
      )}

      <motion.ul
        className="flex flex-col gap-3"
        variants={listVariants}
        initial="hidden"
        animate="visible"
      >
        {results.map((song) => {
          const pct = Math.round(song.similarity * 100);
          const isExpanded = expandedId === song.id;

          return (
            <motion.li
              key={song.id}
              variants={itemVariants}
              className="glass-interactive rounded-xl p-3"
              whileHover={{ scale: 1.01 }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">
                    {song.title}
                  </p>
                  <p className="truncate text-xs text-text-secondary">{song.artist}</p>
                </div>
                <span className={`shrink-0 text-xs font-semibold ${song.similarity >= 0.4 ? "text-amber-light" : "text-text-secondary"}`}>
                  {pct}%
                </span>
              </div>

              {/* Metadata tags */}
              <div className="mt-1.5 flex flex-wrap gap-1.5 text-[10px]">
                {song.bpm != null && (
                  <span className="rounded bg-amber-dim px-1.5 py-0.5 font-mono text-amber-light">
                    {Math.round(song.bpm)} BPM
                  </span>
                )}
                {song.musical_key && (
                  <span className="rounded bg-amber-dim px-1.5 py-0.5 font-mono text-amber-light">
                    {song.musical_key}
                  </span>
                )}
                {song.duration_sec != null && song.duration_sec > 0 && (
                  <span className="rounded bg-amber-dim px-1.5 py-0.5 font-mono text-amber-light">
                    {formatDuration(song.duration_sec)}
                  </span>
                )}
              </div>

              {/* Animated similarity bar */}
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
                <motion.div
                  className={`h-full rounded-full bg-gradient-to-r ${similarityColor(song.similarity)}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ delay: 0.3, duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
                />
              </div>

              {/* Low score explanation */}
              {song.similarity < 0.3 && (
                <p className="mt-1 text-[10px] text-text-tertiary">
                  Niedrige Ähnlichkeit — der Katalog enthält möglicherweise keine engeren Matches.
                </p>
              )}

              {/* Actions row */}
              <div className="mt-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {/* Search links */}
                  <a
                    href={searchUrl("spotify", song.artist, song.title)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded px-1.5 py-0.5 text-[10px] text-emerald-400 transition hover:bg-emerald-400/10"
                    title="Auf Spotify suchen"
                  >
                    Spotify
                  </a>
                  <a
                    href={searchUrl("youtube", song.artist, song.title)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded px-1.5 py-0.5 text-[10px] text-red-400 transition hover:bg-red-400/10"
                    title="Auf YouTube suchen"
                  >
                    YouTube
                  </a>
                  {/* Radar toggle */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : song.id)}
                    className="rounded px-1.5 py-0.5 text-[10px] text-text-tertiary transition hover:text-text-secondary"
                  >
                    {isExpanded ? "Radar -" : "Radar +"}
                  </button>
                </div>
                <FeedbackButtons
                  querySongId={querySong.id}
                  resultSongId={song.id}
                  onFeedback={(rating) => onFeedback?.(querySong.id, song.id, rating)}
                />
              </div>

              {/* Radar chart with AnimatePresence */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    className="mt-3 border-t border-border-subtle pt-3"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <RadarChart querySongId={querySong.id} resultSongId={song.id} />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.li>
          );
        })}
      </motion.ul>
    </div>
  );
}
