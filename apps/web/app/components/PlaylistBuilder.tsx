"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getBatchFeatures, type Song, type RadarFeatures } from "@/lib/api";

interface PlaylistBuilderProps {
  songs: Song[];
  onRemove: (songId: string) => void;
  onReorder: (songs: Song[]) => void;
  onClear: () => void;
}

// Sonic Flow Chart — renders BPM + Intensity lines
function SonicFlowChart({ songs, features }: { songs: Song[]; features: Map<string, RadarFeatures> }) {
  if (songs.length < 2) return null;

  const W = 300;
  const H = 80;
  const PAD = 20;
  const plotW = W - PAD * 2;
  const plotH = H - PAD;

  const bpms = songs.map((s) => s.bpm ?? 0);
  const intensities = songs.map((s) => features.get(s.id)?.intensity ?? 0);

  const maxBpm = Math.max(...bpms, 1);
  const minBpm = Math.min(...bpms.filter((b) => b > 0), maxBpm);
  const bpmRange = Math.max(maxBpm - minBpm, 10);

  function toX(i: number) { return PAD + (i / (songs.length - 1)) * plotW; }
  function bpmToY(bpm: number) { return PAD + (1 - (bpm - minBpm) / bpmRange) * plotH; }
  function intToY(val: number) { return PAD + (1 - val) * plotH; }

  const bpmPath = songs.map((_, i) => `${i === 0 ? "M" : "L"}${toX(i)},${bpmToY(bpms[i])}`).join(" ");
  const intPath = songs.map((_, i) => `${i === 0 ? "M" : "L"}${toX(i)},${intToY(intensities[i])}`).join(" ");

  return (
    <div className="glass-premium-noise rounded-xl p-3 mt-3">
      <p className="text-[10px] text-text-tertiary mb-1">Sonic Flow</p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-16">
        {/* BPM line */}
        <path d={bpmPath} fill="none" stroke="#f59e0b" strokeWidth="1.5" opacity="0.8" />
        {songs.map((_, i) => (
          <circle key={`b${i}`} cx={toX(i)} cy={bpmToY(bpms[i])} r="2.5" fill="#f59e0b" />
        ))}
        {/* Intensity line */}
        <path d={intPath} fill="none" stroke="#22d3ee" strokeWidth="1.5" opacity="0.8" />
        {songs.map((_, i) => (
          <circle key={`i${i}`} cx={toX(i)} cy={intToY(intensities[i])} r="2.5" fill="#22d3ee" />
        ))}
      </svg>
      <div className="flex gap-3 text-[9px] text-text-tertiary">
        <span className="flex items-center gap-1">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" /> BPM
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-400" /> Intensität
        </span>
      </div>
    </div>
  );
}

export default function PlaylistBuilder({ songs, onRemove, onReorder, onClear }: PlaylistBuilderProps) {
  const [features, setFeatures] = useState<Map<string, RadarFeatures>>(new Map());
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  // Fetch features for all songs
  useEffect(() => {
    if (songs.length === 0) return;
    const ids = songs.map((s) => s.id).filter((id) => !features.has(id));
    if (ids.length === 0) return;

    getBatchFeatures(ids).then((items) => {
      setFeatures((prev) => {
        const next = new Map(prev);
        for (const item of items) {
          next.set(item.song_id, item.features);
        }
        return next;
      });
    }).catch(() => {/* ignore */});
  }, [songs]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDragStart = useCallback((idx: number) => {
    setDragIdx(idx);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === idx) return;
    const newSongs = [...songs];
    const [moved] = newSongs.splice(dragIdx, 1);
    newSongs.splice(idx, 0, moved);
    onReorder(newSongs);
    setDragIdx(idx);
  }, [dragIdx, songs, onReorder]);

  const handleCopy = useCallback(() => {
    const text = songs
      .map((s, i) => {
        const parts = [`${i + 1}. ${s.artist} — ${s.title}`];
        if (s.bpm) parts.push(`${Math.round(s.bpm)} BPM`);
        if (s.musical_key) parts.push(s.musical_key);
        return parts.join(" | ");
      })
      .join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [songs]);

  if (songs.length === 0) {
    return (
      <div className="glass-premium-noise rounded-xl p-4 text-center">
        <p className="text-xs text-text-tertiary">
          Noch keine Songs in der Playlist. Klicke bei Ergebnissen auf &ldquo;+&rdquo;, um Songs hinzuzufügen.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-text-secondary">
          Playlist <span className="text-text-tertiary font-normal">({songs.length})</span>
        </h3>
        <div className="flex gap-1.5">
          <motion.button
            onClick={handleCopy}
            whileTap={{ scale: 0.95 }}
            className="rounded-lg px-2.5 py-1 text-[10px] font-medium text-text-secondary transition-colors hover:bg-surface-elevated hover:text-text-primary"
          >
            {copied ? "Kopiert!" : "Liste kopieren"}
          </motion.button>
          <motion.button
            onClick={onClear}
            whileTap={{ scale: 0.95 }}
            className="rounded-lg px-2.5 py-1 text-[10px] font-medium text-error/70 transition-colors hover:bg-error-dim hover:text-error"
          >
            Leeren
          </motion.button>
        </div>
      </div>

      {/* Song list with drag & drop */}
      <ul className="flex flex-col gap-1">
        {songs.map((song, idx) => (
          <li
            key={song.id}
            draggable
            onDragStart={() => handleDragStart(idx)}
            onDragOver={(e) => handleDragOver(e, idx)}
            onDragEnd={() => setDragIdx(null)}
            className={`relative overflow-hidden group flex items-center gap-2 rounded-lg px-3 py-2 text-xs transition-colors cursor-grab active:cursor-grabbing ${
              dragIdx === idx ? "bg-amber/10 border border-amber/30" : "glass-premium-noise hover:bg-surface-elevated"
            }`}
          >
            <div className="absolute inset-x-0 bottom-0 h-[1px] bg-gradient-to-r from-transparent via-amber/0 to-transparent transition-all duration-300 group-hover:via-amber/30" />
            <span className="shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-surface-elevated font-mono text-[10px] font-bold text-text-secondary">
              {idx + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-text-primary font-medium">{song.title}</p>
              <p className="truncate text-[10px] text-text-secondary">{song.artist}</p>
            </div>
            {song.bpm != null && (
              <span className="shrink-0 rounded-md bg-amber/8 px-1.5 py-0.5 font-mono tabular-nums text-[10px] text-amber-light">
                {Math.round(song.bpm)}
              </span>
            )}
            <button
              onClick={() => onRemove(song.id)}
              className="shrink-0 rounded-full w-5 h-5 flex items-center justify-center text-text-tertiary hover:text-error transition-colors"
              aria-label={`${song.title} entfernen`}
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      {/* Sonic Flow Chart */}
      <SonicFlowChart songs={songs} features={features} />
    </div>
  );
}
