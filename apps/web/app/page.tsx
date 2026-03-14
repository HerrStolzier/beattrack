"use client";

import { useCallback, useEffect, useState } from "react";
import { findSimilar, searchSongs, getSongCount, type Song, type SimilarSong } from "@/lib/api";
import SearchBar from "./components/SearchBar";
import SongCard from "./components/SongCard";
import SimilarResults from "./components/SimilarResults";
import AnalyzeView from "./components/AnalyzeView";
import ApiStatus from "./components/ApiStatus";
import { useToast } from "./components/Toast";

type Tab = "catalog" | "analyze";

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
  }, [toast]);

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
    <main className="min-h-screen font-sans text-text-primary">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <ApiStatus />
        {/* Header */}
        <header className="mb-8 flex items-end justify-between animate-fade-in-up">
          <div>
            <h1 className="font-display text-4xl font-extrabold tracking-tight">
              <span className="bg-gradient-to-r from-amber to-gold bg-clip-text text-transparent">
                Beattrack
              </span>
            </h1>
            <p className="mt-1 text-sm text-text-secondary">Find sonically similar songs</p>
          </div>
          {songCount !== null && (
            <span className="text-xs text-text-tertiary" data-testid="song-count">
              {songCount.toLocaleString()} Songs im Katalog
            </span>
          )}
        </header>

        {/* Tabs */}
        <div className="mb-6 flex gap-1 rounded-lg bg-surface-raised p-1 animate-fade-in-up stagger-1" role="tablist">
          <button
            role="tab"
            aria-selected={tab === "catalog"}
            onClick={() => setTab("catalog")}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === "catalog"
                ? "bg-amber-dim text-amber-light"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Katalog durchsuchen
          </button>
          <button
            role="tab"
            aria-selected={tab === "analyze"}
            onClick={() => setTab("analyze")}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === "analyze"
                ? "bg-amber-dim text-amber-light"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Song analysieren
          </button>
        </div>

        {/* Catalog tab */}
        {tab === "catalog" && (
          <>
            <div className="mb-6 animate-fade-in-up stagger-2">
              <SearchBar onResults={handleResults} />
            </div>

            <div className="flex flex-col gap-6 lg:flex-row animate-fade-in-up stagger-3">
              <section className="flex-1">
                {songs.length === 0 ? (
                  <p className="text-sm text-text-secondary">No songs found.</p>
                ) : (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {songs.map((song) => (
                      <SongCard
                        key={song.id}
                        song={song}
                        onFindSimilar={handleFindSimilar}
                        isSelected={selectedSong?.id === song.id}
                      />
                    ))}
                  </div>
                )}
              </section>

              {selectedSong && (
                <aside className="w-full lg:w-80 lg:shrink-0">
                  <div className="glass rounded-xl p-4">
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
                </aside>
              )}
            </div>
          </>
        )}

        {/* Analyze tab */}
        {tab === "analyze" && <AnalyzeView />}
      </div>
      <footer className="mx-auto max-w-6xl px-4 py-6">
        <div className="flex items-center justify-between border-t border-border-subtle pt-4">
          <p className="text-xs text-text-tertiary">Beattrack — Find sonically similar songs</p>
          <a href="/privacy" className="text-xs text-amber transition-colors hover:text-amber-light">
            Datenschutz
          </a>
        </div>
      </footer>
    </main>
  );
}
