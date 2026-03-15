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
      className={`glass-interactive group flex flex-col gap-1 rounded-xl p-4 ${
        isSelected
          ? "border-amber/50 glow-md !bg-amber-dim/30"
          : ""
      }`}
    >
      <p className="truncate text-sm font-semibold text-text-primary group-hover:text-amber-light transition-colors">{song.title}</p>
      <p className="truncate text-xs text-text-secondary">{song.artist}</p>
      {song.album && (
        <p className="truncate text-xs text-text-tertiary">{song.album}</p>
      )}
      <div className="mt-2 flex items-center gap-2 text-xs text-text-tertiary">
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
      <button
        onClick={() => onFindSimilar(song)}
        className="gradient-border mt-3 rounded-lg bg-surface-raised px-3 py-1.5 text-xs font-medium text-text-primary transition-all hover:text-amber-light hover:bg-amber-dim active:scale-95"
      >
        Find Similar
      </button>
    </div>
  );
}
