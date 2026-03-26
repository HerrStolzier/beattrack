"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  uploadAudio,
  findSimilar,
  identifyUrl,
  detectPlatform,
  searchSongsForIngest,
  NetworkError,
  TimeoutError,
  ApiError,
  type AnalysisResult,
  type IdentifyResponse,
  type SimilarSong,
  type Song,
  type FocusCategory,
} from "@/lib/api";

export type AnalyzePhase =
  | "idle"
  | "uploading"
  | "processing"
  | "results"
  | "error"
  | "youtube-result"
  | "journey"
  | "blend"
  | "vibe";

export interface AnalyzeState {
  phase: AnalyzePhase;
  jobId: string | null;
  error: string | null;
  result: AnalysisResult | null;
  ytResult: IdentifyResponse | null;
  uploadedFileName: string;
  focus: FocusCategory | null;
  focusLoading: boolean;
  multiLabel: string;
  visitedIds: string[];
  playlist: Song[];
  playlistOpen: boolean;
  querySong: Song | null;

  handleFileSelected: (file: File) => Promise<void>;
  handleComplete: (analysisResult: AnalysisResult) => void;
  handleError: (errMsg: string) => void;
  handleYouTubeMatch: (identifyResult: IdentifyResponse) => Promise<void>;
  handleReset: () => void;
  handleFocusChange: (newFocus: FocusCategory | null) => Promise<void>;
  handleAddToPlaylist: (song: Song) => void;
  handleMultiResults: (results: SimilarSong[], label: string) => void;
  setPhase: (phase: AnalyzePhase) => void;
  setPlaylist: React.Dispatch<React.SetStateAction<Song[]>>;
  setPlaylistOpen: (open: boolean) => void;
}

export function useAnalyzeState(initialUrl?: string | null): AnalyzeState {
  const [phase, setPhase] = useState<AnalyzePhase>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [ytResult, setYtResult] = useState<IdentifyResponse | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>("");
  const [focus, setFocus] = useState<FocusCategory | null>(null);
  const [focusLoading, setFocusLoading] = useState(false);
  const [multiLabel, setMultiLabel] = useState<string>("");
  const [visitedIds, setVisitedIds] = useState<string[]>([]);
  const [playlist, setPlaylist] = useState<Song[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const saved = localStorage.getItem("beattrack-playlist");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [playlistOpen, setPlaylistOpen] = useState(false);

  // Persist playlist to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("beattrack-playlist", JSON.stringify(playlist));
    } catch {
      /* ignore */
    }
  }, [playlist]);

  // Auto-trigger identify when initialUrl is provided (deep-link)
  const deepLinkTriggered = useRef(false);
  useEffect(() => {
    if (!initialUrl || deepLinkTriggered.current) return;
    const platform = detectPlatform(initialUrl);
    if (!platform) {
      setError(
        "Diese URL wird nicht unterstützt. Unterstützt: YouTube, SoundCloud, Spotify, Apple Music."
      );
      setPhase("error");
      return;
    }
    deepLinkTriggered.current = true;
    setPhase("uploading"); // reuse uploading phase for loading state
    identifyUrl(initialUrl)
      .then((res) => {
        handleYouTubeMatch(res);
        // Clean up URL bar
        window.history.replaceState({}, "", "/");
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "URL-Identifikation fehlgeschlagen."
        );
        setPhase("error");
      });
  }, [initialUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileSelected = useCallback(async (file: File) => {
    setPhase("uploading");
    setError(null);
    setResult(null);
    setYtResult(null);
    setUploadedFileName(file.name);

    try {
      const response = await uploadAudio(file);
      setJobId(response.job_id);
      setPhase("processing");
    } catch (err) {
      if (err instanceof TimeoutError) {
        setError(
          "Das Backend braucht gerade etwas länger. Bitte warte kurz und versuche es erneut."
        );
      } else if (err instanceof NetworkError) {
        setError("Keine Verbindung zum Server. Prüfe deine Internetverbindung.");
      } else if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Ein unerwarteter Fehler ist aufgetreten.");
      }
      setPhase("error");
    }
  }, []);

  const handleComplete = useCallback((analysisResult: AnalysisResult) => {
    setResult(analysisResult);
    setPhase("results");
  }, []);

  const handleError = useCallback((errMsg: string) => {
    setError(errMsg);
    setPhase("error");
  }, []);

  const ingestRetryRef = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined
  );
  const ingestRetryCount = useRef(0);

  const handleYouTubeMatch = useCallback(
    async (identifyResult: IdentifyResponse) => {
      setYtResult(identifyResult);
      setPhase("youtube-result");

      // If we got a match, find similar songs for it
      if (identifyResult.matched && identifyResult.song) {
        ingestRetryCount.current = 0;
        try {
          setVisitedIds((prev) =>
            prev.includes(identifyResult.song!.id)
              ? prev
              : [...prev, identifyResult.song!.id]
          );
          const similar = await findSimilar(identifyResult.song.id, {
            excludeIds: visitedIds,
          });
          setResult({
            song_id: identifyResult.song.id,
            bpm: identifyResult.song.bpm || 0,
            key: identifyResult.song.musical_key || "",
            duration: identifyResult.song.duration_sec || 0,
            similar_songs: similar,
          });
          // Track result song IDs as visited
          setVisitedIds((prev) => {
            const newIds = similar
              .map((s) => s.id)
              .filter((id) => !prev.includes(id));
            return [...prev, ...newIds].slice(-200);
          });
        } catch {
          // Similar search failed, but YouTube match still valid
        }
        return;
      }

      // Auto-retry if ingesting (backend is adding the song)
      if (
        identifyResult.ingesting &&
        identifyResult.parsed_artist &&
        identifyResult.parsed_title
      ) {
        ingestRetryCount.current += 1;
        if (ingestRetryCount.current <= 4) {
          // Clear any existing retry
          if (ingestRetryRef.current) clearTimeout(ingestRetryRef.current);
          ingestRetryRef.current = setTimeout(async () => {
            try {
              const q = `${identifyResult.parsed_artist} ${identifyResult.parsed_title}`;
              const song = await searchSongsForIngest(q);
              if (song) {
                // Found it! Treat as a match
                const matchResult: IdentifyResponse = {
                  matched: true,
                  song,
                  parsed_artist: identifyResult.parsed_artist,
                  parsed_title: identifyResult.parsed_title,
                  message: `Match: ${song.artist} — ${song.title}`,
                };
                handleYouTubeMatch(matchResult);
                return;
              }
              // Not yet — retry again
              if (ingestRetryCount.current < 4) {
                handleYouTubeMatch(identifyResult);
              } else {
                // Give up auto-retry, show manual option
                setYtResult({ ...identifyResult, ingesting: false });
              }
            } catch {
              // Retry failed, show manual option
              setYtResult({ ...identifyResult, ingesting: false });
            }
          }, 15_000); // 15s between retries
        }
      }
    },
    [visitedIds]
  );

  // Cleanup ingest retry on unmount
  useEffect(() => {
    return () => {
      if (ingestRetryRef.current) clearTimeout(ingestRetryRef.current);
    };
  }, []);

  const handleReset = useCallback(() => {
    if (ingestRetryRef.current) clearTimeout(ingestRetryRef.current);
    ingestRetryCount.current = 0;
    setPhase("idle");
    setJobId(null);
    setError(null);
    setResult(null);
    setYtResult(null);
    setUploadedFileName("");
    setFocus(null);
    setVisitedIds([]);
  }, []);

  const handleFocusChange = useCallback(
    async (newFocus: FocusCategory | null) => {
      if (!result) return;
      setFocus(newFocus);
      setFocusLoading(true);
      try {
        const similar = await findSimilar(result.song_id, {
          focus: newFocus ?? undefined,
          excludeIds: visitedIds,
        });
        setResult((prev) =>
          prev ? { ...prev, similar_songs: similar } : prev
        );
      } catch {
        // Keep existing results on error
      } finally {
        setFocusLoading(false);
      }
    },
    [result, visitedIds]
  );

  const handleAddToPlaylist = useCallback((song: Song) => {
    setPlaylist((prev) => {
      if (prev.some((s) => s.id === song.id)) return prev;
      return [...prev, song];
    });
  }, []);

  const handleMultiResults = useCallback(
    (results: SimilarSong[], label: string) => {
      setMultiLabel(label);
      setResult({
        song_id: "multi",
        bpm: 0,
        key: "",
        duration: 0,
        similar_songs: results,
      });
      setPhase("results");
    },
    []
  );

  // Build a Song object from the result for SimilarResults query display
  const querySong: Song | null = result
    ? {
        id: result.song_id,
        title:
          multiLabel ||
          ytResult?.parsed_title ||
          uploadedFileName ||
          `Upload ${result.song_id.slice(0, 8)}`,
        artist: multiLabel ? "" : ytResult?.parsed_artist || "Unbekannt",
        album: null,
        bpm: result.bpm,
        musical_key: result.key,
        duration_sec: result.duration,
        genre: null,
        deezer_id: null,
      }
    : ytResult?.song || null;

  return {
    phase,
    jobId,
    error,
    result,
    ytResult,
    uploadedFileName,
    focus,
    focusLoading,
    multiLabel,
    visitedIds,
    playlist,
    playlistOpen,
    querySong,

    handleFileSelected,
    handleComplete,
    handleError,
    handleYouTubeMatch,
    handleReset,
    handleFocusChange,
    handleAddToPlaylist,
    handleMultiResults,
    setPhase,
    setPlaylist,
    setPlaylistOpen,
  };
}
