"use client";

import { useCallback, useEffect, useState } from "react";
import { findSimilar, searchSongs, type Song, type SimilarSong } from "@/lib/api";
import SearchBar from "./components/SearchBar";
import SongCard from "./components/SongCard";
import SimilarResults from "./components/SimilarResults";

export default function Home() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [selectedSong, setSelectedSong] = useState<Song | null>(null);
  const [similarResults, setSimilarResults] = useState<SimilarSong[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  // Load initial songs on mount
  useEffect(() => {
    searchSongs("").then(setSongs).catch(() => {});
  }, []);

  const handleResults = useCallback((results: Song[]) => {
    setSongs(results);
  }, []);

  async function handleFindSimilar(song: Song) {
    setSelectedSong(song);
    setLoadingSimilar(true);
    setSimilarResults([]);
    try {
      const results = await findSimilar(song.id);
      setSimilarResults(results);
    } catch {
      setSimilarResults([]);
    } finally {
      setLoadingSimilar(false);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-950 font-[var(--font-space-grotesk)] text-zinc-100">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Beattrack</h1>
          <p className="mt-1 text-sm text-zinc-500">Find sonically similar songs</p>
        </header>

        {/* Search */}
        <div className="mb-6">
          <SearchBar onResults={handleResults} />
        </div>

        {/* Content */}
        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Song list */}
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

          {/* Similar results panel */}
          {selectedSong && (
            <aside className="w-full lg:w-80 lg:shrink-0">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                {loadingSimilar ? (
                  <p className="text-sm text-zinc-500">Loading similar songs…</p>
                ) : (
                  <SimilarResults
                    results={similarResults}
                    querySong={selectedSong}
                    onFeedback={(qId, rId, rating) => {
                      console.log(`Feedback: ${rating} for ${qId} → ${rId}`);
                    }}
                  />
                )}
              </div>
            </aside>
          )}
        </div>
      </div>
    </main>
  );
}
