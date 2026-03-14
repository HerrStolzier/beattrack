"use client";

import { useEffect, useRef, useState } from "react";
import { searchSongs, type Song } from "@/lib/api";

interface SearchBarProps {
  onResults: (songs: Song[]) => void;
}

export default function SearchBar({ onResults }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setLoading(true);
      setError(false);
      try {
        const results = await searchSongs(query);
        onResults(results);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, onResults]);

  return (
    <div className="relative w-full">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search songs..."
        className="glass w-full rounded-xl border border-border-glass px-4 py-3 text-text-primary placeholder:text-text-tertiary outline-none transition focus:border-amber/50 focus:ring-1 focus:ring-amber/30"
      />
      {loading && (
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
          Searching…
        </span>
      )}
      {error && (
        <p className="mt-1 text-xs text-red-400">Search failed. Try again.</p>
      )}
    </div>
  );
}
