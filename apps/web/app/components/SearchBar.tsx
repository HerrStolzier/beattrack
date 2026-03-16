"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { searchSongs, type Song } from "@/lib/api";

interface SearchBarProps {
  onResults: (songs: Song[]) => void;
  genre?: string | null;
  resultCount?: number;
}

export default function SearchBar({ onResults, genre, resultCount }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      // Cancel any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      setError(false);
      try {
        const results = await searchSongs(query, {
          genre: genre ?? undefined,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          onResults(results);
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (!controller.signal.aborted) setError(true);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 300);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, genre, onResults]);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  return (
    <div className="relative w-full group">
      {/* Search icon */}
      <svg
        className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-text-tertiary transition-colors group-focus-within:text-amber-light"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={2}
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
      </svg>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Songs durchsuchen..."
        autoFocus
        className="glass-premium w-full rounded-xl border-0 pl-11 pr-12 py-3.5 text-text-primary placeholder:text-text-tertiary outline-none transition-all duration-300 focus:glow-amber focus:ring-1 focus:ring-amber/30"
      />

      {/* Loading dots + result count */}
      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
        <AnimatePresence>
          {loading && (
            <motion.div
              className="flex gap-1"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-amber-light"
                  animate={{ scale: [1, 1.4, 1], opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
        {!loading && resultCount != null && (
          <motion.span
            className="text-[11px] font-mono text-text-tertiary"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            key={resultCount}
          >
            {resultCount}
          </motion.span>
        )}
      </div>

      {error && (
        <motion.p
          className="mt-2 text-xs text-red-400"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Suche fehlgeschlagen. Erneut versuchen.
        </motion.p>
      )}
    </div>
  );
}
