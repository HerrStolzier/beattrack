"use client";

import { useCallback, useSyncExternalStore } from "react";

export interface HistoryEntry {
  id: string;
  timestamp: number;
  type: "upload" | "url" | "blend" | "vibe";
  query: string;
  resultCount: number;
  topResult?: { title: string; artist: string };
}

const STORAGE_KEY = "beattrack-history";
const MAX_ENTRIES = 20;

// ---------------------------------------------------------------------------
// External store backed by localStorage — SSR-safe via useSyncExternalStore
// ---------------------------------------------------------------------------

let _cache: HistoryEntry[] | null = null;
const _listeners = new Set<() => void>();

function notifyListeners() {
  for (const l of _listeners) l();
}

function getSnapshot(): HistoryEntry[] {
  if (_cache !== null) return _cache;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    _cache = raw ? JSON.parse(raw) : [];
  } catch {
    _cache = [];
  }
  return _cache!;
}

function getServerSnapshot(): HistoryEntry[] {
  return [];
}

function subscribe(listener: () => void): () => void {
  _listeners.add(listener);
  return () => _listeners.delete(listener);
}

function writeHistory(entries: HistoryEntry[]): void {
  _cache = entries;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    /* ignore */
  }
  notifyListeners();
}

export interface SessionHistoryHook {
  history: HistoryEntry[];
  addEntry: (entry: Omit<HistoryEntry, "id" | "timestamp">) => void;
  clearHistory: () => void;
}

export function useSessionHistory(): SessionHistoryHook {
  const history = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const addEntry = useCallback((entry: Omit<HistoryEntry, "id" | "timestamp">) => {
    const current = getSnapshot();
    const newEntry: HistoryEntry = {
      ...entry,
      id: crypto.randomUUID(),
      timestamp: Date.now(),
    };
    writeHistory([newEntry, ...current].slice(0, MAX_ENTRIES));
  }, []);

  const clearHistory = useCallback(() => {
    writeHistory([]);
  }, []);

  return { history, addEntry, clearHistory };
}
