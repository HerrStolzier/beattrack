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

  const slotLabels = mode === "blend"
    ? ["Song A", "Song B"]
    : ["Song 1", "Song 2", "Song 3", "Song 4", "Song 5"];

  const nextSlotIndex = selectedSongs.length;
  const nextSlotLabel = nextSlotIndex < slotLabels.length ? slotLabels[nextSlotIndex] : "";

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

      {/* Song slots — visual stepper */}
      <div className="flex flex-col gap-2">
        {Array.from({ length: config.max }).map((_, i) => {
          const song = selectedSongs[i];
          const isNext = i === nextSlotIndex && nextSlotIndex < config.max;
          const isFuture = i > nextSlotIndex;
          const isOptional = i >= config.min;

          if (song) {
            // Filled slot
            return (
              <motion.div
                key={song.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-3 rounded-xl border border-amber/30 bg-amber/10 px-4 py-2.5"
              >
                <span className="shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-amber/20 text-[10px] font-bold text-amber-light">
                  {slotLabels[i].slice(-1)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">{song.title}</p>
                  <p className="truncate text-[11px] text-text-secondary">{song.artist}</p>
                </div>
                <button
                  onClick={() => handleRemoveSong(song.id)}
                  className="shrink-0 text-text-tertiary hover:text-error transition-colors"
                  aria-label={`${song.title} entfernen`}
                >
                  ×
                </button>
              </motion.div>
            );
          }

          if (isNext) {
            // Active search slot
            return (
              <div key={`slot-${i}`} className="relative">
                <div className="flex items-center gap-3 rounded-xl border border-border-glass border-dashed bg-surface-raised/50 px-4 py-2.5">
                  <span className="shrink-0 flex h-6 w-6 items-center justify-center rounded-full border border-border-glass text-[10px] font-bold text-text-tertiary">
                    {slotLabels[i].slice(-1)}
                  </span>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => handleSearch(e.target.value)}
                    placeholder={`${slotLabels[i]} suchen — Titel oder Artist eingeben`}
                    className="flex-1 bg-transparent text-sm text-text-primary placeholder-text-tertiary outline-none"
                    // eslint-disable-next-line jsx-a11y/no-autofocus
                    autoFocus
                  />
                  {searching && (
                    <svg className="h-4 w-4 animate-spin text-text-tertiary shrink-0" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                      <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                    </svg>
                  )}
                </div>

                {/* Search results dropdown */}
                <AnimatePresence>
                  {searchResults.length > 0 && (
                    <motion.ul
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-y-auto rounded-xl border border-border-glass bg-surface-elevated shadow-lg"
                    >
                      {searchResults.map((s) => (
                        <li key={s.id}>
                          <button
                            onClick={() => handleAddSong(s)}
                            className="w-full px-4 py-2 text-left text-sm hover:bg-surface-raised transition-colors cursor-pointer"
                          >
                            <span className="font-medium text-text-primary">{s.title}</span>
                            <span className="ml-2 text-xs text-text-secondary">{s.artist}</span>
                          </button>
                        </li>
                      ))}
                    </motion.ul>
                  )}
                </AnimatePresence>
              </div>
            );
          }

          if (isFuture) {
            // Empty future slot
            return (
              <div
                key={`slot-${i}`}
                className="flex items-center gap-3 rounded-xl border border-border-glass/30 border-dashed px-4 py-2.5 opacity-40"
              >
                <span className="shrink-0 flex h-6 w-6 items-center justify-center rounded-full border border-border-glass/50 text-[10px] font-bold text-text-tertiary">
                  {slotLabels[i].slice(-1)}
                </span>
                <span className="text-sm text-text-tertiary">
                  {isOptional ? `${slotLabels[i]} (optional)` : slotLabels[i]}
                </span>
              </div>
            );
          }

          return null;
        })}
      </div>

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
