"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { type Song, type SimilarSong } from "@/lib/api";
import FeedbackButtons from "./FeedbackButtons";
import HarmonicBadge from "./HarmonicBadge";
import RadarChart from "./RadarChart";
import DeezerEmbed from "./DeezerEmbed";

import type { FocusCategory } from "@/lib/api";
import FocusSelector from "./FocusSelector";

interface SimilarResultsProps {
  results: SimilarSong[];
  querySong: Song;
  onFeedback?: (querySongId: string, resultSongId: string, rating: 1 | -1) => void;
  focus?: FocusCategory | null;
  onFocusChange?: (focus: FocusCategory | null) => void;
  focusLoading?: boolean;
  onAddToPlaylist?: (song: Song) => void;
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
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function SimilarResults({ results, querySong, onFeedback, focus, onFocusChange, focusLoading, onAddToPlaylist }: SimilarResultsProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [djMode, setDjMode] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-secondary">
          Ähnlich wie{" "}
          <span className="text-text-primary">{querySong.title}</span>
          <span className="ml-2 text-xs font-normal text-text-tertiary">
            {results.length} {results.length === 1 ? "Treffer" : "Treffer"}
          </span>
        </h2>
        <button
          onClick={() => setDjMode(!djMode)}
          className={`cursor-pointer rounded-lg px-2.5 py-1 text-[10px] font-medium transition-colors ${
            djMode
              ? "bg-cyan/15 text-cyan border border-cyan/30"
              : "text-text-tertiary hover:text-text-secondary hover:bg-surface-elevated"
          }`}
          title={djMode ? "DJ-Modus aus" : "DJ-Modus an — zeigt harmonische Kompatibilität"}
        >
          DJ
        </button>
      </div>

      {onFocusChange && (
        <FocusSelector
          selected={focus ?? null}
          onSelect={onFocusChange}
          disabled={focusLoading}
        />
      )}

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
          const isTop3 = index < 3;
          const hasDeezer = !!song.deezer_id;

          return (
            <motion.li
              key={song.id}
              variants={itemVariants}
              className="group/card relative overflow-hidden rounded-xl border border-border-subtle bg-surface-glass/60 backdrop-blur-sm transition-all duration-300 hover:border-amber/15 hover:bg-surface-elevated hover:shadow-[0_0_30px_rgba(245,158,11,0.04)]"
            >
              {/* Top-3 glow accent line */}
              {isTop3 && (
                <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-amber/50 to-transparent" />
              )}

              <div className="p-5">
                {/* Header: Rank + Title + Score */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    {/* Rank — glowing for top 3 */}
                    <motion.span
                      className={`shrink-0 flex h-9 w-9 items-center justify-center rounded-lg font-mono text-sm font-black ${
                        isTop3
                          ? "bg-gradient-to-br from-amber/25 to-gold/15 text-amber-light border border-amber/30 shadow-[0_0_10px_rgba(245,158,11,0.12)]"
                          : "bg-surface-elevated text-text-secondary"
                      }`}
                      initial={{ scale: 0.6, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: index * 0.04, type: "spring", stiffness: 500 }}
                    >
                      {index + 1}
                    </motion.span>

                    <div className="min-w-0 flex-1">
                      <p className="truncate font-display text-base font-semibold tracking-tight text-white">
                        {song.title}
                      </p>
                      <p className="mt-0.5 truncate text-[13px] text-text-secondary">
                        {song.artist}
                      </p>
                      <div className="mt-1.5 flex items-center gap-2">
                        {song.bpm != null && (
                          <span className="inline-flex items-center gap-1 rounded-md bg-amber/8 px-2 py-0.5 font-mono text-[11px] font-medium text-amber-light">
                            {Math.round(song.bpm)}
                            <span className="text-[9px] font-normal text-amber-light/50">BPM</span>
                          </span>
                        )}
                        {song.genre && (
                          <span className="rounded-md bg-surface-elevated px-2 py-0.5 text-[11px] text-text-tertiary">
                            {song.genre}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Score badge */}
                  <motion.div
                    className="shrink-0 text-right"
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.2 + index * 0.05, type: "spring", stiffness: 400 }}
                  >
                    <span
                      className={`font-display text-xl font-bold tabular-nums tracking-tight ${
                        pct >= 90 ? "text-amber" : pct >= 70 ? "text-amber-light" : "text-text-secondary"
                      }`}
                      style={pct >= 90 ? { textShadow: "0 0 12px var(--color-amber-glow), 0 0 4px var(--color-amber-dim)" } : undefined}
                    >
                      {pct}<span className="text-sm">%</span>
                    </span>
                    <p className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary">{similarityLabel(song.similarity)}</p>
                  </motion.div>
                </div>

                {/* Harmonic badge (DJ mode) */}
                {djMode && (
                  <div className="mt-2">
                    <HarmonicBadge
                      queryKey={querySong.musical_key}
                      queryBpm={querySong.bpm}
                      resultKey={song.musical_key}
                      resultBpm={song.bpm}
                    />
                  </div>
                )}

                {/* Similarity bar — ultra-thin with glow */}
                <div
                  className="mt-3 h-[2px] w-full overflow-hidden rounded-full bg-surface-raised"
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${pct}% ähnlich`}
                >
                  <motion.div
                    className={`h-full rounded-full bg-gradient-to-r ${similarityColor(song.similarity)}`}
                    style={{ boxShadow: isTop3 ? "0 0 12px var(--color-amber-glow)" : "none" }}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ delay: 0.3 + index * 0.05, duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
                  />
                </div>

                {/* Action row — compact tiles */}
                <div className="mt-3 flex items-stretch gap-1.5">
                  {/* Play / Preview — primary action, bigger */}
                  {hasDeezer ? (
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : song.id)}
                      className={`group/play flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl border py-2.5 transition-all duration-200 ${
                        isExpanded
                          ? "border-amber/30 bg-amber/10 text-amber-light shadow-[0_0_16px_rgba(245,158,11,0.1)]"
                          : "border-border-subtle bg-surface-raised/50 text-text-secondary hover:border-amber/30 hover:bg-amber/5 hover:text-amber-light"
                      }`}
                      title={isExpanded ? "Player schließen" : "Song anhören"}
                    >
                      {isExpanded ? (
                        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
                      ) : (
                        <svg className="h-5 w-5 transition-transform duration-200 group-hover/play:scale-110" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.14v14.72a1 1 0 001.5.86l11-7.36a1 1 0 000-1.72l-11-7.36a1 1 0 00-1.5.86z"/></svg>
                      )}
                      <span className="text-xs font-medium">{isExpanded ? "Pause" : "Anhören"}</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : song.id)}
                      className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl border border-border-subtle bg-surface-raised/50 py-2.5 text-text-secondary transition-all hover:border-cyan/30 hover:bg-cyan/5 hover:text-cyan"
                    >
                      <svg className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-180" : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 9l6 6 6-6"/></svg>
                      <span className="text-xs font-medium">{isExpanded ? "Weniger" : "Details"}</span>
                    </button>
                  )}

                  {/* Secondary actions — icon-only, compact */}
                  <button
                    onClick={() => window.open(searchUrl("spotify", song.artist, song.title), "_blank")}
                    className="flex cursor-pointer items-center justify-center rounded-xl border border-border-subtle bg-surface-raised/50 px-3 py-2.5 text-emerald/60 transition-all hover:border-emerald/30 hover:bg-emerald/5 hover:text-emerald"
                    title="Auf Spotify suchen"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>
                  </button>
                  <button
                    onClick={() => window.open(searchUrl("youtube", song.artist, song.title), "_blank")}
                    className="flex cursor-pointer items-center justify-center rounded-xl border border-border-subtle bg-surface-raised/50 px-3 py-2.5 text-rose/60 transition-all hover:border-rose/30 hover:bg-rose/5 hover:text-rose"
                    title="Auf YouTube suchen"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                  </button>
                  {onAddToPlaylist && (
                    <button
                      onClick={() => onAddToPlaylist(song)}
                      className="flex cursor-pointer items-center justify-center rounded-xl border border-border-subtle bg-surface-raised/50 px-3 py-2.5 text-amber-light/60 transition-all hover:border-amber/30 hover:bg-amber/5 hover:text-amber-light"
                      title="Zur Playlist hinzufügen"
                    >
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>
                    </button>
                  )}
                </div>

                {/* Feedback — full width CTA */}
                <div className="mt-3 border-t border-border-subtle pt-3">
                  <FeedbackButtons
                    querySongId={querySong.id}
                    resultSongId={song.id}
                    onFeedback={(rating) => onFeedback?.(querySong.id, song.id, rating)}
                  />
                </div>
              </div>

              {/* Expanded: Deezer player + Radar */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    className="border-t border-border-subtle bg-surface-raised/30 px-4 pb-4 pt-3 space-y-3"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    {song.deezer_id && (
                      <div onClick={(e) => e.stopPropagation()}>
                        <DeezerEmbed deezerId={song.deezer_id} compact={false} autoplay />
                      </div>
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
