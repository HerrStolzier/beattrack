"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { findSimilar, searchSongs, getSongCount, type Song, type SimilarSong } from "@/lib/api";
import SearchBar from "./components/SearchBar";
import SongCard from "./components/SongCard";
import SimilarResults from "./components/SimilarResults";
import AnalyzeView from "./components/AnalyzeView";
import ApiStatus from "./components/ApiStatus";
import { useToast } from "./components/Toast";
import AudioWaveform from "./components/AudioWaveform";

type Tab = "catalog" | "analyze";

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const },
  }),
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.2 },
  },
};

const cardVariant = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 300, damping: 24 },
  },
};

const slideIn = {
  hidden: { opacity: 0, x: 30 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { type: "spring" as const, stiffness: 200, damping: 20 },
  },
  exit: { opacity: 0, x: -30, transition: { duration: 0.2 } },
};

export default function Home() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("catalog");
  const [songs, setSongs] = useState<Song[]>([]);
  const [selectedSong, setSelectedSong] = useState<Song | null>(null);
  const [similarResults, setSimilarResults] = useState<SimilarSong[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [songCount, setSongCount] = useState<number | null>(null);

  // Filters
  const [minBpm, setMinBpm] = useState<string>("");
  const [maxBpm, setMaxBpm] = useState<string>("");
  const [minSimilarity, setMinSimilarity] = useState<number>(0);

  // Load initial songs + count on mount
  useEffect(() => {
    searchSongs("").then(setSongs).catch((err) => toast.error(err.message || "Anfrage fehlgeschlagen"));
    getSongCount().then(setSongCount).catch((err) => toast.error(err.message || "Anfrage fehlgeschlagen"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleResults = useCallback((results: Song[]) => {
    setSongs(results);
  }, []);

  async function handleFindSimilar(song: Song) {
    setSelectedSong(song);
    setLoadingSimilar(true);
    setSimilarResults([]);
    try {
      const opts: { minBpm?: number; maxBpm?: number } = {};
      if (minBpm) opts.minBpm = Number(minBpm);
      if (maxBpm) opts.maxBpm = Number(maxBpm);
      const results = await findSimilar(song.id, opts);
      setSimilarResults(results);
    } catch (err) {
      setSimilarResults([]);
      toast.error((err instanceof Error ? err.message : null) || "Anfrage fehlgeschlagen");
    } finally {
      setLoadingSimilar(false);
    }
  }

  // Apply client-side similarity filter
  const filteredResults = similarResults.filter((s) => s.similarity >= minSimilarity);

  return (
    <main className="ambient-glow min-h-screen font-sans text-text-primary">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <ApiStatus />

        {/* Header */}
        <motion.header
          className="mb-12 flex items-end justify-between"
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
                <span className="bg-gradient-to-r from-amber via-gold to-amber-light bg-[length:200%_auto] bg-clip-text text-transparent animate-gradient-shift">
                  Beattrack
                </span>
              </motion.h1>
              <motion.p
                className="mt-2 text-sm text-text-secondary tracking-widest uppercase"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.6 }}
              >
                Find sonically similar songs
              </motion.p>
            </div>
            <AudioWaveform className="hidden md:flex" />
          </div>
          {songCount !== null && (
            <motion.span
              className="glass-premium rounded-full px-4 py-1.5 text-xs font-medium text-amber-light"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6, type: "spring", stiffness: 300 }}
              data-testid="song-count"
            >
              {songCount.toLocaleString()} Songs
            </motion.span>
          )}
        </motion.header>

        {/* Gradient divider */}
        <div className="mb-8 h-px bg-gradient-to-r from-transparent via-amber/30 to-transparent" />

        {/* Tabs */}
        <motion.div
          className="mb-8 flex gap-1 glass-premium rounded-xl p-1.5"
          role="tablist"
          initial="hidden"
          animate="visible"
          variants={fadeInUp}
          custom={1}
        >
          {(["catalog", "analyze"] as const).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`relative flex-1 rounded-lg px-4 py-3 text-sm font-semibold transition-colors duration-200 ${
                tab === t ? "text-amber-light" : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {tab === t && (
                <motion.div
                  layoutId="active-tab"
                  className="absolute inset-0 rounded-lg bg-gradient-to-r from-amber-dim to-violet-dim"
                  style={{ zIndex: -1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              {t === "catalog" ? "Katalog durchsuchen" : "Song analysieren"}
            </button>
          ))}
        </motion.div>

        {/* Tab content */}
        <AnimatePresence mode="wait">
          {tab === "catalog" && (
            <motion.div
              key="catalog"
              initial="hidden"
              animate="visible"
              exit="hidden"
              variants={staggerContainer}
            >
              {/* Search bar */}
              <motion.div className="mb-6" variants={fadeInUp} custom={2}>
                <SearchBar onResults={handleResults} />
              </motion.div>

              <div className="flex flex-col gap-6 lg:flex-row">
                <section className="flex-1">
                  {songs.length === 0 ? (
                    <p className="text-sm text-text-secondary">No songs found.</p>
                  ) : (
                    <motion.div
                      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
                      variants={staggerContainer}
                    >
                      {songs.map((song) => (
                        <motion.div key={song.id} variants={cardVariant}>
                          <SongCard
                            song={song}
                            onFindSimilar={handleFindSimilar}
                            isSelected={selectedSong?.id === song.id}
                          />
                        </motion.div>
                      ))}
                    </motion.div>
                  )}
                </section>

                <AnimatePresence>
                  {selectedSong && (
                    <motion.aside
                      className="w-full lg:w-80 lg:shrink-0"
                      variants={slideIn}
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                    >
                      <div className="glass-premium rounded-xl p-4">
                        {/* Filters */}
                        <div className="mb-4 space-y-2 border-b border-border-subtle pb-4">
                          <p className="text-xs font-medium text-text-secondary">Filter</p>
                          <div className="flex gap-2">
                            <input
                              type="number"
                              placeholder="Min BPM"
                              value={minBpm}
                              onChange={(e) => setMinBpm(e.target.value)}
                              className="w-full rounded border border-border-glass bg-surface-raised px-2 py-1 text-xs text-text-primary placeholder:text-text-tertiary outline-none focus:border-amber/50 focus:ring-1 focus:ring-amber/30"
                              data-testid="filter-min-bpm"
                            />
                            <input
                              type="number"
                              placeholder="Max BPM"
                              value={maxBpm}
                              onChange={(e) => setMaxBpm(e.target.value)}
                              className="w-full rounded border border-border-glass bg-surface-raised px-2 py-1 text-xs text-text-primary placeholder:text-text-tertiary outline-none focus:border-amber/50 focus:ring-1 focus:ring-amber/30"
                              data-testid="filter-max-bpm"
                            />
                          </div>
                          <div>
                            <label className="flex items-center justify-between text-xs text-text-tertiary">
                              <span>Min. Ähnlichkeit: {Math.round(minSimilarity * 100)}%</span>
                            </label>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.05"
                              value={minSimilarity}
                              onChange={(e) => setMinSimilarity(Number(e.target.value))}
                              className="mt-1 w-full accent-amber"
                              data-testid="filter-similarity"
                            />
                          </div>
                          {(minBpm || maxBpm) && (
                            <button
                              onClick={() => handleFindSimilar(selectedSong)}
                              className="w-full rounded bg-amber-dim px-2 py-1 text-xs text-amber-light transition hover:bg-amber/30"
                            >
                              Erneut suchen
                            </button>
                          )}
                        </div>

                        {loadingSimilar ? (
                          <p className="text-sm text-text-secondary">Loading similar songs…</p>
                        ) : (
                          <>
                            <SimilarResults
                              results={filteredResults}
                              querySong={selectedSong}
                              onFeedback={(qId, rId, rating) => {
                                console.log(`Feedback: ${rating} for ${qId} → ${rId}`);
                              }}
                            />
                            {filteredResults.length < similarResults.length && (
                              <p className="mt-2 text-[10px] text-text-tertiary">
                                {similarResults.length - filteredResults.length} Ergebnis(se) durch Filter ausgeblendet
                              </p>
                            )}
                          </>
                        )}
                      </div>
                    </motion.aside>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}

          {tab === "analyze" && (
            <motion.div
              key="analyze"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <AnalyzeView />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <footer className="mx-auto max-w-6xl px-4 py-8">
        <div className="h-px bg-gradient-to-r from-transparent via-border-glass to-transparent" />
        <div className="flex items-center justify-between pt-6">
          <p className="text-xs text-text-tertiary">Beattrack — Find sonically similar songs</p>
          <a href="/privacy" className="text-xs text-text-tertiary transition-colors hover:text-amber-light">
            Datenschutz
          </a>
        </div>
      </footer>
    </main>
  );
}
