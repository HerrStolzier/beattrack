"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { type Song } from "@/lib/api";
import { getGenreColor } from "./GenreFilter";

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
  const [isHovered, setIsHovered] = useState(false);
  const genreColor = getGenreColor(song.genre);

  return (
    <motion.div
      className="group relative cursor-pointer"
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={() => onFindSimilar(song)}
      whileHover={{ y: -6, transition: { type: "spring", stiffness: 400, damping: 25 } }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Animated genre-colored glow behind card */}
      <motion.div
        className="absolute -inset-px rounded-2xl opacity-0 blur-xl"
        style={{ background: genreColor }}
        animate={{
          opacity: isSelected ? 0.2 : isHovered ? 0.12 : 0,
        }}
        transition={{ duration: 0.4 }}
      />

      {/* Animated border gradient */}
      <motion.div
        className="absolute -inset-px rounded-2xl"
        style={{
          background: `linear-gradient(135deg, ${genreColor}, var(--color-violet), ${genreColor})`,
          backgroundSize: "200% 200%",
        }}
        animate={{
          opacity: isSelected ? 0.6 : isHovered ? 0.4 : 0,
          backgroundPosition: isHovered ? "100% 100%" : "0% 0%",
        }}
        transition={{ duration: 0.6, ease: "easeInOut" }}
      >
        <div className="absolute inset-px rounded-[15px] bg-surface" />
      </motion.div>

      {/* Card body */}
      <div
        className={`relative overflow-hidden rounded-2xl p-5 transition-colors duration-300 ${
          isSelected
            ? "bg-surface-elevated"
            : "bg-surface-glass"
        }`}
        style={{
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          boxShadow: isSelected
            ? `inset 0 1px 0 rgba(255,255,255,0.12), 0 8px 32px rgba(0,0,0,0.4), 0 0 24px color-mix(in srgb, ${genreColor} 20%, transparent)`
            : "inset 0 1px 0 rgba(255,255,255,0.08), 0 4px 16px rgba(0,0,0,0.2)",
        }}
      >
        {/* Top genre accent stripe */}
        <motion.div
          className="absolute inset-x-0 top-0 h-px"
          style={{
            background: `linear-gradient(90deg, transparent, ${genreColor}, transparent)`,
          }}
          animate={{ opacity: isSelected ? 1 : isHovered ? 0.8 : 0.3 }}
          transition={{ duration: 0.3 }}
        />

        {/* Inner content */}
        <div className="relative flex flex-col gap-3">
          {/* Title + Artist block */}
          <div className="min-w-0">
            <h3 className="truncate font-display text-[15px] font-bold tracking-tight text-text-primary">
              {song.title}
            </h3>
            <p className="mt-0.5 truncate font-sans text-xs font-medium text-text-secondary">
              {song.artist}
            </p>
            {song.album && (
              <p className="mt-0.5 truncate font-sans text-[11px] text-text-tertiary">
                {song.album}
              </p>
            )}
          </div>

          {/* Metadata row */}
          <div className="flex items-center gap-1.5">
            {song.bpm !== null && (
              <span className="inline-flex items-center rounded-md bg-surface-raised px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide text-amber-light ring-1 ring-inset ring-amber/10">
                {Math.round(song.bpm)} BPM
              </span>
            )}
            {song.musical_key && (
              <span className="inline-flex items-center rounded-md bg-surface-raised px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide text-violet ring-1 ring-inset ring-violet/10">
                {song.musical_key}
              </span>
            )}
            <span className="ml-auto font-mono text-[10px] tabular-nums text-text-tertiary">
              {formatDuration(song.duration_sec)}
            </span>
          </div>

          {/* Bottom row: Genre + Action */}
          <div className="flex items-center justify-between gap-2">
            {song.genre ? (
              <span
                className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
                style={{
                  color: genreColor,
                  background: `color-mix(in srgb, ${genreColor} 12%, transparent)`,
                  boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${genreColor} 20%, transparent)`,
                }}
              >
                {song.genre}
              </span>
            ) : (
              <span />
            )}

            {/* Action indicator — reveals on hover */}
            <motion.div
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium"
              style={{
                color: genreColor,
                background: `color-mix(in srgb, ${genreColor} 8%, transparent)`,
              }}
              animate={{
                opacity: isHovered || isSelected ? 1 : 0.4,
                x: isHovered ? 0 : 4,
              }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <span>Ähnliche finden</span>
              <motion.svg
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2.5}
                stroke="currentColor"
                animate={{ x: isHovered ? 2 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </motion.svg>
            </motion.div>
          </div>
        </div>

        {/* Subtle inner glow on hover */}
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-2xl"
          style={{
            background: `radial-gradient(ellipse at 50% 0%, color-mix(in srgb, ${genreColor} 10%, transparent), transparent 70%)`,
          }}
          animate={{ opacity: isHovered || isSelected ? 1 : 0 }}
          transition={{ duration: 0.4 }}
        />
      </div>
    </motion.div>
  );
}
