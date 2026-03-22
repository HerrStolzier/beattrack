"use client";

import { useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { findSimilar, type Song, type SimilarSong } from "@/lib/api";
import { getGenreColor } from "./GenreFilter";
import DeezerEmbed from "./DeezerEmbed";
import RadarChart from "./RadarChart";

interface JourneyViewProps {
  startSong: Song;
  onExit: () => void;
}

type JourneyStep = {
  song: Song;
  similarity: number; // similarity to previous song (0 for first)
};

function formatDuration(sec: number | null | undefined): string {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function JourneyView({ startSong, onExit }: JourneyViewProps) {
  const [path, setPath] = useState<JourneyStep[]>([{ song: startSong, similarity: 0 }]);
  const [candidates, setCandidates] = useState<SimilarSong[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRadar, setShowRadar] = useState(false);

  const currentSong = path[path.length - 1].song;
  const visitedIds = path.map((s) => s.song.id);

  // Gamification stats
  const totalDistance = path.reduce((acc, step) => acc + (1 - step.similarity), 0);
  const genresDiscovered = new Set(path.map((s) => s.song.genre).filter(Boolean));

  const fetchCandidates = useCallback(
    async (songId: string, excludeIds: string[]) => {
      setLoading(true);
      setError(null);
      try {
        const results = await findSimilar(songId, {
          limit: 5,
          excludeIds: excludeIds,
        });
        setCandidates(results);
      } catch {
        setError("Ähnliche Songs konnten nicht geladen werden.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Fetch candidates for the first step on mount
  const [initialized, setInitialized] = useState(false);
  if (!initialized) {
    setInitialized(true);
    fetchCandidates(startSong.id, [startSong.id]);
  }

  const handleSelectCandidate = useCallback(
    (candidate: SimilarSong) => {
      const newStep: JourneyStep = {
        song: candidate,
        similarity: candidate.similarity,
      };
      const newPath = [...path, newStep];
      setPath(newPath);
      setShowRadar(false);

      // Fetch next candidates, excluding all visited + new song
      const allIds = [...visitedIds, candidate.id];
      fetchCandidates(candidate.id, allIds);
    },
    [path, visitedIds, fetchCandidates],
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold text-text-primary">
          Sonic Journey
        </h2>
        <button
          onClick={onExit}
          className="rounded-lg border border-border-glass px-3 py-1.5 text-xs font-medium text-amber-light transition-colors hover:bg-amber-dim hover:text-amber"
        >
          Beenden
        </button>
      </div>

      {/* Stats bar — glass-premium-noise */}
      <div className="flex flex-wrap gap-3 text-xs">
        <div className="glass-premium-noise rounded-lg px-3 py-1.5">
          <span className="text-text-tertiary">Schritte </span>
          <span className="font-mono font-bold text-amber-light">{path.length - 1}</span>
        </div>
        <div className="glass-premium-noise rounded-lg px-3 py-1.5">
          <span className="text-text-tertiary">Sonic Distance </span>
          <span className="font-mono font-bold text-cyan">{totalDistance.toFixed(2)}</span>
        </div>
        <div className="glass-premium-noise rounded-lg px-3 py-1.5">
          <span className="text-text-tertiary">Genres </span>
          <span className="font-mono font-bold text-violet">{genresDiscovered.size}</span>
        </div>
      </div>

      {/* Journey path — horizontal scrollable chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
        {path.map((step, i) => {
          const isActive = i === path.length - 1;
          const genreColor = getGenreColor(step.song.genre);
          return (
            <div key={`${step.song.id}-${i}`} className="flex items-center gap-1.5 shrink-0">
              {i > 0 && (
                <svg className="h-3 w-3 text-text-tertiary shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              )}
              <motion.button
                whileTap={{ scale: 0.95 }}
                className={`rounded-full px-2.5 py-1 text-[10px] font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? "bg-amber/20 text-amber-light border border-amber/30"
                    : "bg-surface-raised text-text-secondary"
                }`}
                style={!isActive && step.song.genre ? {
                  borderLeft: `2px solid ${genreColor}`,
                } : undefined}
              >
                {step.song.artist} — {step.song.title}
              </motion.button>
            </div>
          );
        })}
      </div>

      {/* Current song detail */}
      <motion.div
        key={currentSong.id}
        className="glass-premium-noise relative overflow-hidden rounded-xl p-4 space-y-3"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Amber bottom accent */}
        <div className="absolute inset-x-0 bottom-0 h-[1px] bg-gradient-to-r from-transparent via-amber/40 to-transparent" />

        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-display text-sm font-medium text-text-primary">
              {currentSong.artist} — {currentSong.title}
            </h3>
            <div className="mt-1 flex flex-wrap gap-2 text-[10px]">
              {currentSong.genre && (
                <span
                  className="genre-badge"
                  style={{
                    color: getGenreColor(currentSong.genre),
                    background: `color-mix(in srgb, ${getGenreColor(currentSong.genre)} 15%, transparent)`,
                  }}
                >
                  {currentSong.genre}
                </span>
              )}
              {currentSong.bpm != null && (
                <span className="rounded-full bg-amber-dim px-2.5 py-0.5 font-mono tabular-nums text-amber-light">
                  {Math.round(currentSong.bpm)} BPM
                </span>
              )}
              {currentSong.musical_key && (
                <span className="rounded-full bg-violet-dim px-2.5 py-0.5 font-mono tabular-nums text-violet">
                  {currentSong.musical_key}
                </span>
              )}
              {currentSong.duration_sec != null && currentSong.duration_sec > 0 && (
                <span className="rounded-full bg-surface-raised px-2.5 py-0.5 font-mono text-text-tertiary">
                  {formatDuration(currentSong.duration_sec)}
                </span>
              )}
            </div>
          </div>
          {path.length > 1 && (
            <button
              onClick={() => setShowRadar(!showRadar)}
              className="shrink-0 rounded-lg border border-border-glass px-2 py-1 text-[10px] text-text-secondary transition-colors hover:bg-surface-elevated hover:text-text-primary"
            >
              {showRadar ? "▾ Radar" : "▸ Radar"}
            </button>
          )}
        </div>

        {/* Deezer player */}
        {currentSong.deezer_id && (
          <DeezerEmbed deezerId={currentSong.deezer_id} compact />
        )}

        {/* Radar chart comparing previous → current */}
        <AnimatePresence>
          {showRadar && path.length > 1 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <RadarChart
                querySongId={path[path.length - 2].song.id}
                resultSongId={currentSong.id}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Candidates — next step choices */}
      <div className="space-y-2">
        <h3 className="text-xs font-medium text-text-secondary">Wohin als nächstes?</h3>

        {loading && (
          <div className="glass rounded-xl p-6 text-center">
            <svg className="mx-auto mb-2 h-5 w-5 animate-spin text-amber" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
            </svg>
            <p className="text-xs text-text-tertiary">Suche ähnliche Songs...</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-error/30 bg-error-dim p-4">
            <p className="text-xs text-error">{error}</p>
          </div>
        )}

        {/* Dead-end state */}
        {!loading && !error && candidates.length === 0 && (
          <div className="glass-premium-noise rounded-xl p-6 text-center">
            <p className="text-sm text-text-secondary">Sackgasse erreicht!</p>
            <p className="mt-1 text-[10px] text-text-tertiary">
              Keine weiteren unbesuchten Songs in der Nähe. Deine Reise endet hier nach {path.length - 1} Schritten.
            </p>
          </div>
        )}

        <AnimatePresence mode="wait">
          {!loading && candidates.length > 0 && (
            <motion.ul
              key={currentSong.id}
              className="flex flex-col gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {candidates.map((candidate, idx) => {
                const pct = Math.round(candidate.similarity * 100);
                const genreColor = getGenreColor(candidate.genre);
                return (
                  <motion.li
                    key={candidate.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ type: "spring", stiffness: 300, damping: 24 }}
                  >
                    <motion.button
                      onClick={() => handleSelectCandidate(candidate)}
                      className="w-full glass-premium-noise group relative overflow-hidden rounded-xl p-3 text-left hover:border-amber/20 cursor-pointer"
                      whileHover={{ y: -2 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ type: "spring", stiffness: 400, damping: 25 }}
                    >
                      {/* Amber bottom accent */}
                      <div className="absolute inset-x-0 bottom-0 h-[1px] bg-gradient-to-r from-transparent via-transparent group-hover:via-amber/40 to-transparent transition-all duration-300" />

                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-text-primary group-hover:text-amber-light transition-colors">
                            {candidate.title}
                          </p>
                          <p className="truncate text-xs text-text-secondary mt-0.5">{candidate.artist}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-xs font-bold font-mono tabular-nums ${candidate.similarity >= 0.4 ? "text-amber-light" : "text-text-secondary"}`}>
                            {pct}%
                          </span>
                          <svg className="h-4 w-4 text-text-tertiary group-hover:text-amber-light transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                          </svg>
                        </div>
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-1.5 text-[10px]">
                        {candidate.genre && (
                          <span
                            className="genre-badge"
                            style={{
                              color: genreColor,
                              background: `color-mix(in srgb, ${genreColor} 15%, transparent)`,
                            }}
                          >
                            {candidate.genre}
                          </span>
                        )}
                        {candidate.bpm != null && (
                          <span className="rounded-full bg-amber-dim px-2 py-0.5 font-mono tabular-nums text-amber-light">
                            {Math.round(candidate.bpm)} BPM
                          </span>
                        )}
                      </div>
                      {/* Similarity bar */}
                      <div className="mt-1.5 h-[2px] w-full overflow-hidden rounded-full bg-white/5">
                        <div
                          className="similarity-bar"
                          style={{ width: `${pct}%`, "--bar-delay": `${0.2 + idx * 0.06}s` } as React.CSSProperties}
                        />
                      </div>
                    </motion.button>
                  </motion.li>
                );
              })}
            </motion.ul>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
