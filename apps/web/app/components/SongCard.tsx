"use client";

import { type Song } from "@/lib/api";

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
    <div
      className={`glass-raised flex flex-col gap-1 rounded-xl border p-4 transition-all duration-300 ${
        isSelected
          ? "border-amber/50 glow-md"
          : "border-border-subtle hover:border-amber/30 hover:glow-sm"
      }`}
    >
      <p className="truncate text-sm font-semibold text-text-primary">{song.title}</p>
      <p className="truncate text-xs text-text-secondary">{song.artist}</p>
      {song.album && (
        <p className="truncate text-xs text-text-tertiary">{song.album}</p>
      )}
      <div className="mt-2 flex items-center gap-3 text-xs text-text-tertiary">
        {song.bpm !== null && (
          <span className="rounded bg-amber-dim px-2 py-0.5 font-mono text-amber-light">
            {Math.round(song.bpm)} BPM
          </span>
        )}
        {song.musical_key && (
          <span className="rounded bg-amber-dim px-2 py-0.5 font-mono text-amber-light">
            {song.musical_key}
          </span>
        )}
        <span className="ml-auto">{formatDuration(song.duration_sec)}</span>
      </div>
      <button
        onClick={() => onFindSimilar(song)}
        className="mt-3 rounded-lg bg-amber/20 px-3 py-1.5 text-xs font-medium text-amber-light transition hover:bg-amber/30 active:bg-amber/40"
      >
        Find Similar
      </button>
    </div>
  );
}
