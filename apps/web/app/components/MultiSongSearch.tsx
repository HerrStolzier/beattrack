"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  searchSongs,
  findBlend,
  findVibe,
  identifyUrl,
  detectPlatform,
  type Song,
  type SimilarSong,
} from "@/lib/api";

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

function looksLikeUrl(input: string): boolean {
  const trimmed = input.trim();
  return /^https?:\/\//.test(trimmed) || /^(www\.)?[\w-]+\.\w{2,}\//.test(trimmed);
}

const Spinner = ({ className = "h-4 w-4" }: { className?: string }) => (
  <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
    <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
  </svg>
);

// Subtle waveform SVG background for input cards
const WaveformBg = () => (
  <svg
    className="pointer-events-none absolute inset-0 h-full w-full"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    {/* Repeating vertical bars mimicking an audio waveform */}
    {Array.from({ length: 28 }).map((_, i) => {
      const heights = [30, 55, 75, 45, 90, 60, 35, 80, 50, 40, 70, 85, 45, 65, 30, 75, 50, 90, 40, 60, 80, 35, 70, 55, 45, 85, 30, 65];
      const h = heights[i % heights.length];
      const x = (i / 27) * 100;
      return (
        <rect
          key={i}
          x={`${x}%`}
          y={`${50 - h / 2}%`}
          width="2"
          height={`${h}%`}
          rx="1"
          fill="currentColor"
          className="text-amber"
          opacity={0.04}
        />
      );
    })}
  </svg>
);

export default function MultiSongSearch({ mode, onResults, onCancel }: MultiSongSearchProps) {
  const config = MODE_CONFIG[mode];
  const [selectedSongs, setSelectedSongs] = useState<Song[]>([]);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Song[]>([]);
  const [searching, setSearching] = useState(false);
  const [identifying, setIdentifying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slotError, setSlotError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const addSong = useCallback((song: Song) => {
    setSelectedSongs((prev) => {
      if (prev.length >= config.max) return prev;
      if (prev.some((s) => s.id === song.id)) return prev;
      return [...prev, song];
    });
    setQuery("");
    setSearchResults([]);
    setSlotError(null);
  }, [config.max]);

  const handleInput = useCallback((q: string) => {
    setQuery(q);
    setSlotError(null);
    setError(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (abortRef.current) abortRef.current.abort();

    const trimmed = q.trim();

    // URL detected → identify flow
    if (looksLikeUrl(trimmed) && trimmed.length > 10) {
      setSearchResults([]);

      // Auto-trigger on paste (detected via length jump)
      debounceRef.current = setTimeout(async () => {
        const platform = detectPlatform(trimmed);
        if (!platform) {
          setSlotError("URL nicht erkannt. Unterstützt: YouTube, SoundCloud, Spotify, Apple Music.");
          return;
        }

        setIdentifying(true);
        try {
          const result = await identifyUrl(trimmed);
          if (result.matched && result.song) {
            addSong(result.song);
          } else {
            setSlotError(
              result.ingesting
                ? `„${result.parsed_artist} – ${result.parsed_title}" wird gerade zur Datenbank hinzugefügt. Bitte in ~30s erneut versuchen.`
                : result.parsed_title
                  ? `„${result.parsed_artist} – ${result.parsed_title}" nicht in der Datenbank gefunden.`
                  : "Song konnte nicht identifiziert werden."
            );
          }
        } catch (err) {
          setSlotError(err instanceof Error ? err.message : "Identifikation fehlgeschlagen.");
        } finally {
          setIdentifying(false);
        }
      }, 200);
      return;
    }

    // Title search flow
    if (trimmed.length < 2) {
      setSearchResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      abortRef.current = controller;
      setSearching(true);
      try {
        const results = await searchSongs(trimmed, { limit: 8, signal: controller.signal });
        const selectedIds = new Set(selectedSongs.map((s) => s.id));
        setSearchResults(results.filter((s) => !selectedIds.has(s.id)));
      } catch {
        // Ignore abort errors
      } finally {
        setSearching(false);
      }
    }, 300);
  }, [selectedSongs, addSong]);

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
        label = `Blend: ${selectedSongs[0].artist} \u00d7 ${selectedSongs[1].artist}`;
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

  return (
    // Container with pulsing amber border glow when loading is in progress
    <motion.div
      className="space-y-4"
      animate={
        loading
          ? { boxShadow: ["0 0 0px rgba(245,158,11,0)", "0 0 20px rgba(245,158,11,0.3)", "0 0 0px rgba(245,158,11,0)"] }
          : { boxShadow: "0 0 0px rgba(245,158,11,0)" }
      }
      transition={loading ? { duration: 1.4, repeat: Infinity, ease: "easeInOut" } : { duration: 0.4 }}
      style={{ borderRadius: 16 }}
    >
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

      {/* Song slots */}
      <div className="flex flex-col gap-2">
        {Array.from({ length: config.max }).map((_, i) => {
          const song = selectedSongs[i];
          const isNext = i === nextSlotIndex && nextSlotIndex < config.max;
          const isFuture = i > nextSlotIndex;
          const isOptional = i >= config.min;

          if (song) {
            return (
              <motion.div
                key={song.id}
                initial={{ opacity: 0, scale: 0.95, y: -6 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 28, delay: i * 0.04 }}
                className="relative flex items-center gap-3 overflow-hidden rounded-xl border border-amber/30 bg-amber/10 px-4 py-2.5"
              >
                {/* Subtle waveform background */}
                <WaveformBg />
                <span className="relative shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-amber/20 text-[10px] font-bold text-amber-light">
                  {slotLabels[i].slice(-1)}
                </span>
                <div className="relative min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">{song.title}</p>
                  <p className="truncate text-[11px] text-text-secondary">{song.artist}</p>
                </div>
                <button
                  onClick={() => handleRemoveSong(song.id)}
                  className="relative shrink-0 text-text-tertiary hover:text-error transition-colors"
                  aria-label={`${song.title} entfernen`}
                >
                  ×
                </button>
              </motion.div>
            );
          }

          if (isNext) {
            return (
              <div key={`slot-${i}`} className="relative">
                <div className={`relative flex items-center gap-3 overflow-hidden rounded-xl border px-4 py-2.5 ${
                  identifying
                    ? "border-amber/40 bg-amber/5"
                    : "border-border-glass border-dashed bg-surface-raised/50"
                }`}>
                  {/* Subtle waveform background on active input slot */}
                  <WaveformBg />
                  <span className={`relative shrink-0 flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold ${
                    identifying
                      ? "bg-amber/20 text-amber-light"
                      : "border border-border-glass text-text-tertiary"
                  }`}>
                    {slotLabels[i].slice(-1)}
                  </span>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => handleInput(e.target.value)}
                    onPaste={(e) => {
                      // Trigger immediately on paste
                      const pasted = e.clipboardData.getData("text");
                      if (looksLikeUrl(pasted)) {
                        e.preventDefault();
                        handleInput(pasted);
                      }
                    }}
                    placeholder="URL einfügen oder Titel suchen..."
                    disabled={identifying}
                    className="relative flex-1 bg-transparent text-sm text-text-primary placeholder-text-tertiary outline-none disabled:opacity-50"
                    autoFocus
                  />
                  {(searching || identifying) && (
                    <div className="relative flex items-center gap-2 shrink-0">
                      <Spinner className="h-4 w-4 text-text-tertiary" />
                      {identifying && (
                        <span className="text-[11px] text-amber-light">Identifiziere...</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Slot-level error */}
                <AnimatePresence>
                  {slotError && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-1.5 text-xs text-error px-4"
                    >
                      {slotError}
                    </motion.p>
                  )}
                </AnimatePresence>

                {/* Search results dropdown */}
                <AnimatePresence>
                  {searchResults.length > 0 && (
                    <motion.ul
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-y-auto rounded-xl border border-border-glass bg-surface-elevated shadow-lg"
                    >
                      {searchResults.map((s, idx) => (
                        <motion.li
                          key={s.id}
                          initial={{ opacity: 0, x: -6 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.035, duration: 0.2 }}
                        >
                          <button
                            onClick={() => addSong(s)}
                            className="w-full px-4 py-2 text-left text-sm hover:bg-surface-raised transition-colors cursor-pointer"
                          >
                            <span className="font-medium text-text-primary">{s.title}</span>
                            <span className="ml-2 text-xs text-text-secondary">{s.artist}</span>
                          </button>
                        </motion.li>
                      ))}
                    </motion.ul>
                  )}
                </AnimatePresence>
              </div>
            );
          }

          if (isFuture) {
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

      {/* Hint */}
      <p className="text-[10px] text-text-tertiary text-center">
        YouTube, SoundCloud, Spotify oder Apple Music URLs einfügen — oder nach Titel/Artist suchen.
      </p>

      {/* Error */}
      {error && (
        <p className="text-xs text-error">{error}</p>
      )}

      {/* Submit button */}
      <motion.button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="relative w-full overflow-hidden rounded-xl bg-amber/20 px-5 py-3 text-sm font-medium text-amber-light transition-colors hover:bg-amber/30 disabled:cursor-not-allowed disabled:opacity-50"
        whileTap={canSubmit ? { scale: 0.98 } : undefined}
      >
        {/* Animated shimmer stripe when loading */}
        <AnimatePresence>
          {loading && (
            <motion.div
              className="absolute inset-0 -translate-x-full"
              animate={{ translateX: ["−100%", "200%"] }}
              transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
              style={{
                background: "linear-gradient(90deg, transparent, rgba(251,191,36,0.15), transparent)",
              }}
            />
          )}
        </AnimatePresence>
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <Spinner />
            Suche...
          </span>
        ) : (
          config.cta
        )}
      </motion.button>

      {/* Hint for blend results */}
      {mode === "blend" && selectedSongs.length === 2 && (
        <p className="text-[10px] text-text-tertiary text-center">
          Findet Songs in der N\u00e4he beider Tracks — nicht unbedingt eine klangliche Mischung.
        </p>
      )}
    </motion.div>
  );
}
