"use client";

import { useState } from "react";
import { type Song, type SimilarSong } from "@/lib/api";
import FeedbackButtons from "./FeedbackButtons";
import RadarChart from "./RadarChart";

interface SimilarResultsProps {
  results: SimilarSong[];
  querySong: Song;
  onFeedback?: (querySongId: string, resultSongId: string, rating: 1 | -1) => void;
}

function similarityColor(score: number): string {
  if (score >= 0.7) return "from-amber to-gold";
  if (score >= 0.4) return "from-amber-light to-amber";
  return "from-red-500 to-red-400";
}

function formatDuration(sec: number | null | undefined): string {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function searchUrl(platform: "spotify" | "youtube", artist: string, title: string): string {
  const q = encodeURIComponent(`${artist} ${title}`);
  if (platform === "spotify") {
    return `https://open.spotify.com/search/${q}`;
  }
  return `https://www.youtube.com/results?search_query=${q}`;
}

export default function SimilarResults({ results, querySong, onFeedback }: SimilarResultsProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-text-secondary">
        Similar to{" "}
        <span className="text-text-primary">{querySong.title}</span>
      </h2>

      {results.length === 0 && (
        <p className="text-xs text-text-secondary">No similar songs found.</p>
      )}

      <ul className="flex flex-col gap-3">
        {results.map((song) => {
          const pct = Math.round(song.similarity * 100);
          const isExpanded = expandedId === song.id;

          return (
            <li
              key={song.id}
              className="rounded-xl border border-border-subtle bg-surface-raised p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-text-primary">
                    {song.title}
                  </p>
                  <p className="truncate text-xs text-text-secondary">{song.artist}</p>
                </div>
                <span className={`shrink-0 text-xs font-semibold ${song.similarity >= 0.4 ? "text-amber-light" : "text-text-secondary"}`}>
                  {pct}%
                </span>
              </div>

              {/* Metadata tags */}
              <div className="mt-1.5 flex flex-wrap gap-1.5 text-[10px]">
                {song.bpm != null && (
                  <span className="rounded bg-amber-dim px-1.5 py-0.5 font-mono text-amber-light">
                    {Math.round(song.bpm)} BPM
                  </span>
                )}
                {song.musical_key && (
                  <span className="rounded bg-amber-dim px-1.5 py-0.5 font-mono text-amber-light">
                    {song.musical_key}
                  </span>
                )}
                {song.duration_sec != null && song.duration_sec > 0 && (
                  <span className="rounded bg-amber-dim px-1.5 py-0.5 font-mono text-amber-light">
                    {formatDuration(song.duration_sec)}
                  </span>
                )}
              </div>

              {/* Similarity bar */}
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${similarityColor(song.similarity)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              {/* Low score explanation */}
              {song.similarity < 0.3 && (
                <p className="mt-1 text-[10px] text-text-tertiary">
                  Niedrige Ähnlichkeit — der Katalog enthält möglicherweise keine engeren Matches.
                </p>
              )}

              {/* Actions row */}
              <div className="mt-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {/* Search links */}
                  <a
                    href={searchUrl("spotify", song.artist, song.title)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded px-1.5 py-0.5 text-[10px] text-emerald-400 transition hover:bg-emerald-400/10"
                    title="Auf Spotify suchen"
                  >
                    Spotify
                  </a>
                  <a
                    href={searchUrl("youtube", song.artist, song.title)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded px-1.5 py-0.5 text-[10px] text-red-400 transition hover:bg-red-400/10"
                    title="Auf YouTube suchen"
                  >
                    YouTube
                  </a>
                  {/* Radar toggle */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : song.id)}
                    className="rounded px-1.5 py-0.5 text-[10px] text-text-tertiary transition hover:text-text-secondary"
                  >
                    {isExpanded ? "Radar -" : "Radar +"}
                  </button>
                </div>
                <FeedbackButtons
                  querySongId={querySong.id}
                  resultSongId={song.id}
                  onFeedback={(rating) => onFeedback?.(querySong.id, song.id, rating)}
                />
              </div>

              {/* Radar chart (expanded) */}
              {isExpanded && (
                <div className="mt-3 border-t border-border-subtle pt-3">
                  <RadarChart querySongId={querySong.id} resultSongId={song.id} />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
