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
      className={`flex flex-col gap-1 rounded-xl border p-4 transition ${
        isSelected
          ? "border-zinc-500 bg-zinc-800"
          : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
      }`}
    >
      <p className="truncate text-sm font-semibold text-zinc-100">{song.title}</p>
      <p className="truncate text-xs text-zinc-400">{song.artist}</p>
      {song.album && (
        <p className="truncate text-xs text-zinc-500">{song.album}</p>
      )}
      <div className="mt-2 flex items-center gap-3 text-xs text-zinc-500">
        {song.bpm !== null && (
          <span className="rounded bg-zinc-800 px-2 py-0.5 font-mono">
            {Math.round(song.bpm)} BPM
          </span>
        )}
        {song.musical_key && (
          <span className="rounded bg-zinc-800 px-2 py-0.5 font-mono">
            {song.musical_key}
          </span>
        )}
        <span className="ml-auto">{formatDuration(song.duration_sec)}</span>
      </div>
      <button
        onClick={() => onFindSimilar(song)}
        className="mt-3 rounded-lg bg-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-100 transition hover:bg-zinc-600 active:bg-zinc-500"
      >
        Find Similar
      </button>
    </div>
  );
}
