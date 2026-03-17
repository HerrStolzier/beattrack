"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { type Song, type SimilarSong } from "@/lib/api";
import { getGenreColor } from "./GenreFilter";
import FeedbackButtons from "./FeedbackButtons";
import RadarChart from "./RadarChart";
import DeezerEmbed from "./DeezerEmbed";


interface SimilarResultsProps {
  results: SimilarSong[];
  querySong: Song;
  onFeedback?: (querySongId: string, resultSongId: string, rating: 1 | -1) => void;
}

function similarityColor(score: number): string {
  if (score >= 0.7) return "from-amber to-gold";
  if (score >= 0.4) return "from-amber-light to-amber";
  return "from-text-tertiary to-border-glass";
}

function similarityLabel(score: number): string {
  if (score >= 0.7) return "Sehr ähnlich";
  if (score >= 0.4) return "Ähnlich";
  return "Entfernt";
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
        <span className="ml-2 text-xs font-normal text-text-tertiary">
          {results.length} {results.length === 1 ? "Treffer" : "Treffer"}
        </span>
      </h2>

      {results.length === 0 && (
        <div className="rounded-xl bg-surface-raised p-6 text-center">
          <p className="text-sm text-text-secondary">Keine passenden Treffer</p>
          <p className="mt-1 text-[11px] text-text-tertiary">
            Der Katalog enthält aktuell keine Songs, die diesem Track klanglich ähnlich genug sind.
          </p>
        </div>
      )}

      <motion.ul
        className="flex flex-col gap-3"
        variants={listVariants}
        initial="hidden"
        animate="visible"
      >
        {results.map((song, index) => {
          const pct = Math.round(song.similarity * 100);
          const isExpanded = expandedId === song.id;
          const genreColor = getGenreColor(song.genre);

          return (
            <motion.li
              key={song.id}
              variants={itemVariants}
              className="glass rounded-xl p-4 transition-colors duration-200 hover:bg-surface-elevated"
            >
              <div className="flex items-start justify-between gap-3">
                {/* Rank number */}
                <span className="shrink-0 w-7 h-7 flex items-center justify-center rounded-full bg-surface-raised text-[11px] font-mono font-bold text-text-tertiary">
                  {index + 1}
                </span>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">
                    {song.title}
                  </p>
                  <p className="truncate text-xs text-text-secondary mt-0.5">{song.artist}</p>
                </div>

                {/* Similarity score + label */}
                <div className="shrink-0 text-right">
                  <span className={`text-sm font-bold ${song.similarity >= 0.4 ? "text-amber-light" : "text-text-secondary"}`}>
                    {pct}%
                  </span>
                  <p className="text-[10px] text-text-tertiary">{similarityLabel(song.similarity)}</p>
                </div>
              </div>

              {/* Metadata row: genre + tags */}
              <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px]">
                {song.genre && (
                  <span
                    className="genre-badge"
                    style={{
                      color: genreColor,
                      background: `color-mix(in srgb, ${genreColor} 15%, transparent)`,
                    }}
                  >
                    {song.genre}
                  </span>
                )}
                {song.bpm != null && (
                  <span className="rounded-full bg-amber-dim px-2.5 py-0.5 font-mono text-amber-light">
                    {Math.round(song.bpm)} BPM
                  </span>
                )}
                {song.musical_key && (
                  <span className="rounded-full bg-violet-dim px-2.5 py-0.5 font-mono text-violet">
                    {song.musical_key}
                  </span>
                )}
                {song.duration_sec != null && song.duration_sec > 0 && (
                  <span className="rounded-full bg-surface-raised px-2.5 py-0.5 font-mono text-text-tertiary">
                    {formatDuration(song.duration_sec)}
                  </span>
                )}
              </div>

              {/* Animated similarity bar */}
              <div
                className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-surface-raised"
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${pct}% ähnlich`}
              >
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

              {/* Actions */}
              <div className="mt-3 flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => window.open(searchUrl("spotify", song.artist, song.title), "_blank")}
                    className="inline-flex cursor-pointer items-center gap-1 rounded-lg px-1.5 py-1 text-[10px] font-medium text-emerald transition-colors hover:bg-emerald-dim"
                    title="Auf Spotify suchen"
                  >
                    <svg className="h-3 w-3 shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>
                  </button>
                  <button
                    onClick={() => window.open(searchUrl("youtube", song.artist, song.title), "_blank")}
                    className="inline-flex cursor-pointer items-center gap-1 rounded-lg px-1.5 py-1 text-[10px] font-medium text-rose transition-colors hover:bg-rose-dim"
                    title="Auf YouTube suchen"
                  >
                    <svg className="h-3 w-3 shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                  </button>
                  {song.deezer_id && (
                    <button
                      onClick={() => window.open(`https://www.deezer.com/track/${song.deezer_id}`, "_blank")}
                      className="inline-flex cursor-pointer items-center gap-1 rounded-lg px-1.5 py-1 text-[10px] font-medium text-purple-400 transition-colors hover:bg-purple-400/10"
                      title="Auf Deezer anhören"
                    >
                      <svg className="h-3 w-3 shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M18.81 4.16v3.03H24V4.16h-5.19zM6.27 8.38v3.027h5.19V8.38H6.27zm6.27 0v3.027h5.19V8.38h-5.19zm6.27 0v3.027H24V8.38h-5.19zM6.27 12.566v3.027h5.19v-3.027H6.27zm6.27 0v3.027h5.19v-3.027h-5.19zm6.27 0v3.027H24v-3.027h-5.19zM0 16.752v3.027h5.19v-3.027H0zm6.27 0v3.027h5.19v-3.027H6.27zm6.27 0v3.027h5.19v-3.027h-5.19zm6.27 0v3.027H24v-3.027h-5.19z"/></svg>
                    </button>
                  )}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : song.id)}
                    className="inline-flex cursor-pointer items-center rounded-lg px-1.5 py-1 text-[10px] font-medium text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary"
                  >
                    {isExpanded ? "▾" : "▸"}
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
                    className="mt-3 border-t border-border-subtle pt-3 space-y-3"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    {song.deezer_id && (
                      <DeezerEmbed deezerId={song.deezer_id} compact={false} />
                    )}
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
