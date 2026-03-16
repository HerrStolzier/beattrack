"use client";

import { motion } from "framer-motion";
import { type Song } from "@/lib/api";
import { getGenreColor } from "./GenreFilter";
import Button from "./Button";

interface SongCardProps {
  song: Song;
  onFindSimilar: (song: Song) => void;
  isSelected: boolean;
}

function formatDuration(sec: number | null): string {
  if (sec === null) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function SongCard({ song, onFindSimilar, isSelected }: SongCardProps) {
  return (
    <motion.div
      className={`group flex flex-col gap-2 rounded-xl p-5 transition-colors duration-200
        ${isSelected
          ? "border border-amber/50 bg-amber-dim/30 shadow-[0_0_24px_var(--color-amber-dim)]"
          : "glass border border-border-glass hover:border-amber/20 hover:bg-surface-elevated"
        }`}
      whileHover={{ y: -4, transition: { type: "spring", stiffness: 400, damping: 30 } }}
    >
      {/* Title row + Genre badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-text-primary">
            {song.title}
          </p>
          <p className="truncate text-xs text-text-secondary mt-0.5">{song.artist}</p>
        </div>
        {song.genre && (
          <span
            className="genre-badge shrink-0"
            style={{
              color: getGenreColor(song.genre),
              background: `color-mix(in srgb, ${getGenreColor(song.genre)} 15%, transparent)`,
            }}
          >
            {song.genre}
          </span>
        )}
      </div>

      {song.album && (
        <p className="truncate text-xs text-text-tertiary">{song.album}</p>
      )}

      {/* Metadata tags */}
      <div className="flex items-center gap-2 text-xs text-text-tertiary">
        {song.bpm !== null && (
          <span className="rounded-full bg-amber-dim px-2.5 py-0.5 font-mono text-[10px] text-amber-light">
            {Math.round(song.bpm)} BPM
          </span>
        )}
        {song.musical_key && (
          <span className="rounded-full bg-violet-dim px-2.5 py-0.5 font-mono text-[10px] text-violet">
            {song.musical_key}
          </span>
        )}
        <span className="ml-auto font-mono text-[10px]">{formatDuration(song.duration_sec)}</span>
      </div>

      <Button
        variant="primary"
        size="sm"
        onClick={() => onFindSimilar(song)}
        className="mt-1 w-full"
      >
        Ähnliche finden
      </Button>
    </motion.div>
  );
}
