"use client";

import { motion } from "framer-motion";

interface GenreFilterProps {
  genres: string[];
  selected: string | null;
  onSelect: (genre: string | null) => void;
}

const GENRE_COLORS: Record<string, string> = {
  Techno: "var(--color-genre-techno)",
  House: "var(--color-genre-house)",
  Ambient: "var(--color-genre-ambient)",
  "Drum & Bass": "var(--color-genre-drum-n-bass)",
  Trance: "var(--color-genre-trance)",
  IDM: "var(--color-genre-idm)",
  Dubstep: "var(--color-genre-dubstep)",
  "Minimal Electronic": "var(--color-genre-minimal)",
  Downtempo: "var(--color-genre-downtempo)",
  "Chill-out": "var(--color-genre-chill-out)",
  Dance: "var(--color-genre-dance)",
  Breakbeat: "var(--color-genre-breakbeat)",
  Electronic: "var(--color-genre-electronic)",
};

export function getGenreColor(genre: string | null | undefined): string {
  if (!genre) return "var(--color-text-tertiary)";
  return GENRE_COLORS[genre] ?? "var(--color-amber)";
}

export default function GenreFilter({ genres, selected, onSelect }: GenreFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {/* "Alle" chip */}
      <button
        onClick={() => onSelect(null)}
        className="relative rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
        style={{
          color: selected === null ? "var(--color-surface)" : "var(--color-text-secondary)",
          background: selected === null ? "var(--color-amber)" : "var(--color-surface-glass)",
        }}
      >
        {selected === null && (
          <motion.div
            layoutId="genre-pill"
            className="absolute inset-0 rounded-full bg-amber"
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            style={{ zIndex: -1 }}
          />
        )}
        Alle
      </button>

      {genres.map((genre) => {
        const isActive = selected === genre;
        const color = getGenreColor(genre);

        return (
          <button
            key={genre}
            onClick={() => onSelect(isActive ? null : genre)}
            className="relative rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200"
            style={{
              color: isActive ? "var(--color-surface)" : color,
              background: isActive ? color : "var(--color-surface-glass)",
              borderColor: isActive ? "transparent" : color,
              border: `1px solid ${isActive ? "transparent" : `color-mix(in srgb, ${color} 30%, transparent)`}`,
            }}
          >
            {isActive && (
              <motion.div
                layoutId="genre-pill"
                className="absolute inset-0 rounded-full"
                style={{ background: color, zIndex: -1 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            {genre}
          </button>
        );
      })}
    </div>
  );
}
