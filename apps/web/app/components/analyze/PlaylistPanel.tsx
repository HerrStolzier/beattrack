"use client";

import { motion, AnimatePresence } from "framer-motion";
import PlaylistBuilder from "../PlaylistBuilder";
import type { Song } from "@/lib/api";

interface PlaylistPanelProps {
  playlist: Song[];
  playlistOpen: boolean;
  setPlaylist: React.Dispatch<React.SetStateAction<Song[]>>;
  setPlaylistOpen: (open: boolean) => void;
}

export default function PlaylistPanel({
  playlist,
  playlistOpen,
  setPlaylist,
  setPlaylistOpen,
}: PlaylistPanelProps) {
  if (playlist.length === 0) return null;

  return (
    <>
      {/* Floating action button */}
      {!playlistOpen && (
        <motion.button
          onClick={() => setPlaylistOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber to-gold text-bg-primary shadow-[0_4px_24px_rgba(245,158,11,0.3)] transition-all hover:shadow-[0_4px_32px_rgba(245,158,11,0.5)]"
          title="Playlist öffnen"
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.95 }}
        >
          <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" fill="currentColor" stroke="none" />
            <circle cx="18" cy="16" r="3" fill="currentColor" stroke="none" />
          </svg>
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-neon-cyan text-[10px] font-bold text-bg-primary shadow-[0_0_8px_var(--color-neon-cyan-dim)]">
            {playlist.length}
          </span>
        </motion.button>
      )}

      {/* Slide-in panel */}
      <AnimatePresence>
        {playlistOpen && (
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed right-0 top-0 z-50 h-full w-80 overflow-y-auto border-l border-border-glass bg-bg-primary p-4 shadow-2xl"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-sm font-semibold text-text-primary">Playlist</h2>
              <button
                onClick={() => setPlaylistOpen(false)}
                className="rounded-lg border border-border-glass p-1.5 text-text-tertiary transition-colors hover:bg-surface-elevated hover:text-text-primary"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <PlaylistBuilder
              songs={playlist}
              onRemove={(id) => setPlaylist((prev) => prev.filter((s) => s.id !== id))}
              onReorder={setPlaylist}
              onClear={() => setPlaylist([])}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
