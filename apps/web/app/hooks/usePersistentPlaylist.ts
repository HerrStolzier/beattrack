"use client";

import { useEffect, useState } from "react";

import type { Song } from "@/lib/api";

const PLAYLIST_STORAGE_KEY = "beattrack-playlist";

function loadPlaylist(): Song[] {
  if (typeof window === "undefined") return [];
  try {
    const saved = localStorage.getItem(PLAYLIST_STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

export function usePersistentPlaylist() {
  const [playlist, setPlaylist] = useState<Song[]>(loadPlaylist);

  useEffect(() => {
    try {
      localStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(playlist));
    } catch {
      /* ignore */
    }
  }, [playlist]);

  return [playlist, setPlaylist] as const;
}
