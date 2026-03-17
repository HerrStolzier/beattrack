"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { searchSongs, findBlend, findVibe, type Song, type SimilarSong } from "@/lib/api";

type Mode = "blend" | "vibe";

interface MultiSongSearchProps {
  mode: Mode;
  onResults: (results: SimilarSong[], label: string) => void;
  onCancel: () => void;
}

const MODE_CONFIG = {
  blend: {
    title: "Sonic Blend",
    subtitle: "Finde Songs zwischen zwei Tracks",
    min: 2,
    max: 2,
    cta: "Blend finden",
  },
  vibe: {
    title: "Vibe definieren",
    subtitle: "Finde Songs die zu allen passen",
    min: 2,
    max: 5,
    cta: "Vibe finden",
  },
} as const;

export default function MultiSongSearch({ mode, onResults, onCancel }: MultiSongSearchProps) {
  const config = MODE_CONFIG[mode];
  const [selectedSongs, setSelectedSongs] = useState<Song[]>([]);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Song[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const handleSearch = useCallback((q: string) => {
    setQuery(q);
    setError(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (abortRef.current) abortRef.current.abort();

    if (q.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      setSearching(true);
      try {
        const results = await searchSongs(q.trim(), { limit: 8, signal: controller.signal });
        // Filter out already selected songs
        const selectedIds = new Set(selectedSongs.map((s) => s.id));
        setSearchResults(results.filter((s) => !selectedIds.has(s.id)));
      } catch {
        // Ignore abort errors
      } finally {
        setSearching(false);
      }
    }, 300);
  }, [selectedSongs]);

  const handleAddSong = useCallback((song: Song) => {
    if (selectedSongs.length >= config.max) return;
    setSelectedSongs((prev) => [...prev, song]);
    setQuery("");
    setSearchResults([]);
  }, [selectedSongs, config.max]);

  const handleRemoveSong = useCallback((songId: string) => {
    setSelectedSongs((prev) => prev.filter((s) => s.id !== songId));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (selectedSongs.length < config.min) return;
    setLoading(true);
    setError(null);

    try {
      let results: SimilarSong[];
      let label: string;

      if (mode === "blend") {
        results = await findBlend(selectedSongs[0].id, selectedSongs[1].id);
        label = `Blend: ${selectedSongs[0].artist} × ${selectedSongs[1].artist}`;
      } else {
        results = await findVibe(selectedSongs.map((s) => s.id));
        label = `Vibe: ${selectedSongs.map((s) => s.title).join(" + ")}`;
      }

      onResults(results, label);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suche fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }, [selectedSongs, mode, config.min, onResults]);

  const canSubmit = selectedSongs.length >= config.min && !loading;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-sm font-semibold text-text-primary">{config.title}</h2>
          <p className="text-[11px] text-text-tertiary">{config.subtitle}</p>
        </div>
        <button
          onClick={onCancel}
          className="rounded-lg border border-border-glass px-3 py-1.5 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-elevated hover:text-text-primary"
        >
          Abbrechen
        </button>
      </div>

      {/* Selected songs as chips */}
      {selectedSongs.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedSongs.map((song) => (
            <span
              key={song.id}
              className="flex items-center gap-1.5 rounded-full bg-amber/15 border border-amber/30 px-3 py-1 text-xs text-amber-light"
            >
              <span className="max-w-[150px] truncate">{song.artist} — {song.title}</span>
              <button
                onClick={() => handleRemoveSong(song.id)}
                className="text-amber-light/60 hover:text-amber-light transition-colors"
                aria-label={`${song.title} entfernen`}
              >
                ×
              </button>
            </span>
          ))}
          <span className="self-center text-[10px] text-text-tertiary">
            {selectedSongs.length}/{config.max}
          </span>
        </div>
      )}

      {/* Search input */}
      {selectedSongs.length < config.max && (
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Song suchen..."
            className="glass w-full rounded-xl border border-border-glass px-4 py-2.5 text-sm text-text-primary placeholder-text-tertiary outline-none transition focus:border-amber/50 focus:ring-1 focus:ring-amber/30"
          />
          {searching && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <svg className="h-4 w-4 animate-spin text-text-tertiary" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
              </svg>
            </div>
          )}

          {/* Search results dropdown */}
          <AnimatePresence>
            {searchResults.length > 0 && (
              <motion.ul
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-y-auto rounded-xl border border-border-glass bg-surface-elevated shadow-lg"
              >
                {searchResults.map((song) => (
                  <li key={song.id}>
                    <button
                      onClick={() => handleAddSong(song)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-surface-raised transition-colors cursor-pointer"
                    >
                      <span className="font-medium text-text-primary">{song.title}</span>
                      <span className="ml-2 text-xs text-text-secondary">{song.artist}</span>
                    </button>
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-error">{error}</p>
      )}

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full rounded-xl bg-amber/20 px-5 py-3 text-sm font-medium text-amber-light transition-colors hover:bg-amber/30 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
            </svg>
            Suche...
          </span>
        ) : (
          config.cta
        )}
      </button>

      {/* Hint for blend */}
      {mode === "blend" && selectedSongs.length === 2 && (
        <p className="text-[10px] text-text-tertiary text-center">
          Findet Songs in der Nähe beider Tracks — nicht unbedingt eine klangliche Mischung.
        </p>
      )}
    </div>
  );
}
