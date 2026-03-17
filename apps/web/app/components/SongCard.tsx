"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { type Song } from "@/lib/api";
import DeezerEmbed from "./DeezerEmbed";

interface SongCardProps {
  song: Song;
  onFindSimilar: (song: Song) => void;
  isSelected: boolean;
}

const ACCENT = "var(--color-amber)";

export default function SongCard({ song, onFindSimilar, isSelected }: SongCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      className="group relative cursor-pointer"
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={() => onFindSimilar(song)}
      whileHover={{ y: -4, transition: { type: "spring", stiffness: 400, damping: 25 } }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Glow behind card */}
      <motion.div
        className="absolute -inset-px rounded-2xl opacity-0 blur-xl"
        style={{ background: ACCENT }}
        animate={{ opacity: isSelected ? 0.15 : isHovered ? 0.08 : 0 }}
        transition={{ duration: 0.4 }}
      />

      {/* Border gradient */}
      <motion.div
        className="absolute -inset-px rounded-2xl"
        style={{ background: `linear-gradient(135deg, ${ACCENT}, var(--color-violet), ${ACCENT})`, backgroundSize: "200% 200%" }}
        animate={{
          opacity: isSelected ? 0.5 : isHovered ? 0.3 : 0,
          backgroundPosition: isHovered ? "100% 100%" : "0% 0%",
        }}
        transition={{ duration: 0.6, ease: "easeInOut" }}
      >
        <div className="absolute inset-px rounded-[15px] bg-surface" />
      </motion.div>

      {/* Card body */}
      <div
        className={`relative overflow-hidden rounded-2xl px-5 py-4 transition-colors duration-300 ${
          isSelected ? "bg-surface-elevated" : "bg-surface-glass"
        }`}
        style={{
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          boxShadow: isSelected
            ? "inset 0 1px 0 rgba(255,255,255,0.12), 0 8px 32px rgba(0,0,0,0.4)"
            : "inset 0 1px 0 rgba(255,255,255,0.08), 0 4px 16px rgba(0,0,0,0.2)",
        }}
      >
        {/* Top accent stripe */}
        <motion.div
          className="absolute inset-x-0 top-0 h-px"
          style={{ background: `linear-gradient(90deg, transparent, ${ACCENT}, transparent)` }}
          animate={{ opacity: isSelected ? 1 : isHovered ? 0.8 : 0.3 }}
          transition={{ duration: 0.3 }}
        />

        {/* Content */}
        <div className="relative flex items-center gap-3">
          {/* Title + Artist */}
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-display text-[15px] font-bold tracking-tight text-text-primary">
              {song.title}
            </h3>
            <p className="mt-0.5 truncate font-sans text-xs font-medium text-text-secondary">
              {song.artist}
            </p>
          </div>

          {/* BPM badge */}
          {song.bpm !== null && (
            <span className="shrink-0 rounded-md bg-surface-raised px-2 py-0.5 font-mono text-[10px] font-medium tracking-wide text-amber-light ring-1 ring-inset ring-amber/10">
              {Math.round(song.bpm)}
            </span>
          )}
        </div>

        {/* Deezer preview widget */}
        {song.deezer_id && (
          <div className="relative mt-2" onClick={(e) => e.stopPropagation()}>
            <DeezerEmbed deezerId={song.deezer_id} compact />
          </div>
        )}

        {/* Action indicator */}
        <motion.div
          className="relative mt-3 flex items-center gap-1.5 text-[11px] font-medium text-amber-light/60"
          animate={{
            opacity: isHovered || isSelected ? 1 : 0,
            y: isHovered || isSelected ? 0 : 4,
          }}
          transition={{ duration: 0.2, ease: "easeOut" }}
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

        {/* Inner glow on hover */}
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-2xl"
          style={{ background: `radial-gradient(ellipse at 50% 0%, color-mix(in srgb, ${ACCENT} 8%, transparent), transparent 70%)` }}
          animate={{ opacity: isHovered || isSelected ? 1 : 0 }}
          transition={{ duration: 0.4 }}
        />
      </div>
    </motion.div>
  );
}
