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
    <main className="min-h-screen bg-zinc-950 font-[var(--font-space-grotesk)] text-zinc-100">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <ApiStatus />
        {/* Header */}
        <header className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Beattrack</h1>
            <p className="mt-1 text-sm text-zinc-500">Find sonically similar songs</p>
          </div>
          {songCount !== null && (
            <span className="text-xs text-zinc-600" data-testid="song-count">
              {songCount.toLocaleString()} Songs im Katalog
            </span>
          )}
        </header>

        {/* Tabs */}
        <div className="mb-6 flex gap-1 rounded-lg bg-zinc-900 p-1" role="tablist">
          <button
            role="tab"
            aria-selected={tab === "catalog"}
            onClick={() => setTab("catalog")}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === "catalog"
                ? "bg-zinc-800 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300"
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
                ? "bg-zinc-800 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            Song analysieren
          </button>
        </div>

        {/* Catalog tab */}
        {tab === "catalog" && (
          <>
            <div className="mb-6">
              <SearchBar onResults={handleResults} />
            </div>

            <div className="flex flex-col gap-6 lg:flex-row">
              <section className="flex-1">
                {songs.length === 0 ? (
                  <p className="text-sm text-zinc-500">No songs found.</p>
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
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                    {/* Filters */}
                    <div className="mb-4 space-y-2 border-b border-zinc-800 pb-4">
                      <p className="text-xs font-medium text-zinc-400">Filter</p>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          placeholder="Min BPM"
                          value={minBpm}
                          onChange={(e) => setMinBpm(e.target.value)}
                          className="w-full rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-blue-500"
                          data-testid="filter-min-bpm"
                        />
                        <input
                          type="number"
                          placeholder="Max BPM"
                          value={maxBpm}
                          onChange={(e) => setMaxBpm(e.target.value)}
                          className="w-full rounded border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-blue-500"
                          data-testid="filter-max-bpm"
                        />
                      </div>
                      <div>
                        <label className="flex items-center justify-between text-xs text-zinc-500">
                          <span>Min. Ähnlichkeit: {Math.round(minSimilarity * 100)}%</span>
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={minSimilarity}
                          onChange={(e) => setMinSimilarity(Number(e.target.value))}
                          className="mt-1 w-full accent-blue-500"
                          data-testid="filter-similarity"
                        />
                      </div>
                      {(minBpm || maxBpm) && (
                        <button
                          onClick={() => handleFindSimilar(selectedSong)}
                          className="w-full rounded bg-zinc-700 px-2 py-1 text-xs text-zinc-200 transition hover:bg-zinc-600"
                        >
                          Erneut suchen
                        </button>
                      )}
                    </div>

                    {loadingSimilar ? (
                      <p className="text-sm text-zinc-500">Loading similar songs…</p>
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
                          <p className="mt-2 text-[10px] text-zinc-600">
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
    </main>
  );
}
