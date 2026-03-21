"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadAudio, findSimilar, identifyUrl, detectPlatform, NetworkError, TimeoutError, ApiError, type AnalysisResult, type IdentifyResponse, type SimilarSong, type Song, type FocusCategory } from "@/lib/api";
import UploadZone from "./UploadZone";
import ProgressTracker from "./ProgressTracker";
import UrlInput from "./UrlInput";
import SimilarResults from "./SimilarResults";
import JourneyView from "./JourneyView";
import MultiSongSearch from "./MultiSongSearch";
import PlaylistBuilder from "./PlaylistBuilder";
import Button from "./Button";

type AnalyzePhase = "idle" | "uploading" | "processing" | "results" | "error" | "youtube-result" | "journey" | "blend" | "vibe";

const phaseVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

type AnalyzeViewProps = {
  initialUrl?: string | null;
};

export default function AnalyzeView({ initialUrl }: AnalyzeViewProps) {
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
    } catch { return []; }
  });
  const [playlistOpen, setPlaylistOpen] = useState(false);

  // Persist playlist to localStorage
  useEffect(() => {
    try { localStorage.setItem("beattrack-playlist", JSON.stringify(playlist)); }
    catch { /* ignore */ }
  }, [playlist]);

  // Auto-trigger identify when initialUrl is provided (deep-link)
  const deepLinkTriggered = useRef(false);
  useEffect(() => {
    if (!initialUrl || deepLinkTriggered.current) return;
    const platform = detectPlatform(initialUrl);
    if (!platform) {
      setError("Diese URL wird nicht unterstützt. Unterstützt: YouTube, SoundCloud, Spotify, Apple Music.");
      setPhase("error");
      return;
    }
    deepLinkTriggered.current = true;
    setPhase("uploading"); // reuse uploading phase for loading state
    identifyUrl(initialUrl)
      .then((result) => {
        handleYouTubeMatch(result);
        // Clean up URL bar
        window.history.replaceState({}, "", "/");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "URL-Identifikation fehlgeschlagen.");
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
        setError("Das Backend braucht gerade etwas länger. Bitte warte kurz und versuche es erneut.");
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

  const ingestRetryRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const ingestRetryCount = useRef(0);

  const handleYouTubeMatch = useCallback(async (identifyResult: IdentifyResponse) => {
    setYtResult(identifyResult);
    setPhase("youtube-result");

    // If we got a match, find similar songs for it
    if (identifyResult.matched && identifyResult.song) {
      ingestRetryCount.current = 0;
      try {
        setVisitedIds((prev) => prev.includes(identifyResult.song!.id) ? prev : [...prev, identifyResult.song!.id]);
        const similar = await findSimilar(identifyResult.song.id, { excludeIds: visitedIds });
        setResult({
          song_id: identifyResult.song.id,
          bpm: identifyResult.song.bpm || 0,
          key: identifyResult.song.musical_key || "",
          duration: identifyResult.song.duration_sec || 0,
          similar_songs: similar,
        });
        // Track result song IDs as visited
        setVisitedIds((prev) => {
          const newIds = similar.map((s) => s.id).filter((id) => !prev.includes(id));
          return [...prev, ...newIds].slice(-200);
        });
      } catch {
        // Similar search failed, but YouTube match still valid
      }
      return;
    }

    // Auto-retry if ingesting (backend is adding the song)
    if (identifyResult.ingesting && identifyResult.parsed_artist && identifyResult.parsed_title) {
      ingestRetryCount.current += 1;
      if (ingestRetryCount.current <= 4) {
        // Clear any existing retry
        if (ingestRetryRef.current) clearTimeout(ingestRetryRef.current);
        ingestRetryRef.current = setTimeout(async () => {
          try {
            // Re-search by artist+title via the songs endpoint
            const q = `${identifyResult.parsed_artist} ${identifyResult.parsed_title}`;
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/songs?q=${encodeURIComponent(q)}&limit=5`);
            if (res.ok) {
              const songs = await res.json();
              if (songs.length > 0) {
                // Found it! Treat as a match
                const song = songs[0];
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
  }, [visitedIds]);

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

  const handleFocusChange = useCallback(async (newFocus: FocusCategory | null) => {
    if (!result) return;
    setFocus(newFocus);
    setFocusLoading(true);
    try {
      const similar = await findSimilar(result.song_id, {
        focus: newFocus ?? undefined,
        excludeIds: visitedIds,
      });
      setResult((prev) => prev ? { ...prev, similar_songs: similar } : prev);
    } catch {
      // Keep existing results on error
    } finally {
      setFocusLoading(false);
    }
  }, [result, visitedIds]);

  const handleAddToPlaylist = useCallback((song: Song) => {
    setPlaylist((prev) => {
      if (prev.some((s) => s.id === song.id)) return prev;
      return [...prev, song];
    });
  }, []);

  const handleMultiResults = useCallback((results: SimilarSong[], label: string) => {
    setMultiLabel(label);
    setResult({
      song_id: "multi",
      bpm: 0,
      key: "",
      duration: 0,
      similar_songs: results,
    });
    setPhase("results");
  }, []);

  // Build a Song object from the result for SimilarResults query display
  const querySong: Song | null = result
    ? {
        id: result.song_id,
        title: multiLabel || ytResult?.parsed_title || uploadedFileName || `Upload ${result.song_id.slice(0, 8)}`,
        artist: multiLabel ? "" : (ytResult?.parsed_artist || "Unbekannt"),
        album: null,
        bpm: result.bpm,
        musical_key: result.key,
        duration_sec: result.duration,
        genre: null,
        deezer_id: null,
      }
    : ytResult?.song || null;

  return (
    <div className="space-y-6">
      <AnimatePresence mode="wait">
        {/* Idle — upload zone + URL input */}
        {phase === "idle" && (
          <motion.div
            key="idle"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <UrlInput onMatch={handleYouTubeMatch} />
            <div className="flex items-center gap-3 my-6">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent to-border-subtle" />
              <span className="text-xs text-text-tertiary font-medium">oder</span>
              <div className="h-px flex-1 bg-gradient-to-l from-transparent to-border-subtle" />
            </div>
            <UploadZone onFileSelected={handleFileSelected} />

            {/* Blend + Vibe buttons */}
            <div className="flex items-center gap-3 mt-6">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent to-border-subtle" />
              <span className="text-xs text-text-tertiary font-medium">oder</span>
              <div className="h-px flex-1 bg-gradient-to-l from-transparent to-border-subtle" />
            </div>
            <div className="flex gap-2 mt-4">
              <motion.button
                onClick={() => setPhase("blend")}
                className="relative flex-1 overflow-hidden glass rounded-xl px-4 py-3 text-sm font-medium text-text-secondary"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
                style={{ originX: 0.5, originY: 0.5 }}
              >
                {/* Hover glow overlay */}
                <motion.div
                  className="pointer-events-none absolute inset-0 rounded-xl"
                  initial={{ opacity: 0 }}
                  whileHover={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                  style={{
                    background: "radial-gradient(ellipse at 50% 100%, rgba(245,158,11,0.12), transparent 70%)",
                    boxShadow: "inset 0 0 0 1px rgba(245,158,11,0.25)",
                  }}
                />
                {/* Animated indicator dot */}
                <motion.span
                  className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-amber/60"
                  animate={{ opacity: [0.4, 1, 0.4], scale: [0.8, 1.1, 0.8] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                />
                <span className="relative block text-text-primary">Sonic Blend</span>
                <span className="relative block text-[10px] text-text-tertiary font-normal mt-0.5">Zwischen zwei Songs</span>
              </motion.button>
              <motion.button
                onClick={() => setPhase("vibe")}
                className="relative flex-1 overflow-hidden glass rounded-xl px-4 py-3 text-sm font-medium text-text-secondary"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 25 }}
                style={{ originX: 0.5, originY: 0.5 }}
              >
                {/* Hover glow overlay */}
                <motion.div
                  className="pointer-events-none absolute inset-0 rounded-xl"
                  initial={{ opacity: 0 }}
                  whileHover={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                  style={{
                    background: "radial-gradient(ellipse at 50% 100%, rgba(167,139,250,0.12), transparent 70%)",
                    boxShadow: "inset 0 0 0 1px rgba(167,139,250,0.2)",
                  }}
                />
                {/* Animated indicator dot */}
                <motion.span
                  className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-violet/60"
                  animate={{ opacity: [0.4, 1, 0.4], scale: [0.8, 1.1, 0.8] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
                />
                <span className="relative block text-text-primary">Vibe definieren</span>
                <span className="relative block text-[10px] text-text-tertiary font-normal mt-0.5">2-5 Songs kombinieren</span>
              </motion.button>
            </div>
          </motion.div>
        )}

        {/* Uploading */}
        {phase === "uploading" && (
          <motion.div
            key="uploading"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="glass-premium rounded-xl p-8 text-center"
          >
            <svg className="mx-auto mb-3 h-8 w-8 animate-spin text-amber" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
            </svg>
            <p className="text-sm text-text-secondary">
              Lade <span className="font-medium text-text-primary">{uploadedFileName}</span> hoch...
            </p>
          </motion.div>
        )}

        {/* Processing — SSE Progress */}
        {phase === "processing" && jobId && (
          <motion.div
            key="processing"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <ProgressTracker jobId={jobId} onComplete={handleComplete} onError={handleError} />
          </motion.div>
        )}

        {/* Error */}
        {phase === "error" && (
          <motion.div
            key="error"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
            className="rounded-xl border border-error/30 bg-error-dim p-6"
          >
            <p className="text-sm text-error">{error}</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setPhase("idle");
                setError(null);
                setUploadedFileName("");
              }}
              className="mt-4"
            >
              Nochmal versuchen
            </Button>
          </motion.div>
        )}

        {/* YouTube result — no match (with auto-ingest support) */}
        {phase === "youtube-result" && ytResult && !ytResult.matched && (
          <motion.div
            key="youtube-no-match"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            {/* Identified song info */}
            <div className="glass-premium rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-text-primary">
                    {ytResult.parsed_artist} — {ytResult.parsed_title}
                  </p>
                  {ytResult.ingesting ? (
                    <div className="mt-2 flex items-center gap-2">
                      <svg className="h-4 w-4 animate-spin text-amber" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                        <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                      </svg>
                      <p className="text-xs text-amber-light">
                        Wird gerade analysiert und zur Datenbank hinzugefügt...
                      </p>
                    </div>
                  ) : (
                    <p className="mt-1 text-xs text-text-tertiary">
                      Nicht im Katalog und nicht auf Deezer gefunden — lade die Audio-Datei hoch oder probier eine andere URL.
                    </p>
                  )}
                </div>
                <button
                  onClick={handleReset}
                  className="shrink-0 rounded-lg border border-border-glass p-1.5 text-text-tertiary transition-colors hover:bg-surface-elevated hover:text-text-primary"
                  title="Schließen"
                  aria-label="Schließen"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Show inputs again so user can try another URL or upload */}
            {!ytResult.ingesting && (
              <>
                <UrlInput onMatch={handleYouTubeMatch} />
                <div className="flex items-center gap-3">
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent to-border-subtle" />
                  <span className="text-xs text-text-tertiary font-medium">oder</span>
                  <div className="h-px flex-1 bg-gradient-to-l from-transparent to-border-subtle" />
                </div>
                <UploadZone onFileSelected={handleFileSelected} />
              </>
            )}
          </motion.div>
        )}

        {/* Results — from upload or YouTube match */}
        {(phase === "results" || (phase === "youtube-result" && ytResult?.matched)) &&
          result &&
          querySong && (
            <motion.div
              key="results"
              variants={phaseVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.3 }}
              className="space-y-4"
            >
              {/* Song info header */}
              <div className="glass-premium rounded-xl p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="font-display text-sm font-medium text-text-primary">
                      {querySong.artist} — {querySong.title}
                    </h3>
                    <div className="mt-1 flex gap-3 text-xs text-text-tertiary">
                      {result.bpm > 0 && <span>{Math.round(result.bpm)} BPM</span>}
                      {result.key && <span>{result.key}</span>}
                      {result.duration > 0 && (
                        <span>{Math.floor(result.duration / 60)}:{String(Math.floor(result.duration % 60)).padStart(2, "0")}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => setPhase("journey")}
                      className="rounded-lg border border-cyan/30 bg-cyan/10 px-3 py-1.5 text-xs font-medium text-cyan transition-colors hover:bg-cyan/20"
                      title="Sonic Journey starten"
                    >
                      Sonic Journey
                    </button>
                    <button
                      onClick={handleReset}
                      className="rounded-lg border border-border-glass px-3 py-1.5 text-xs font-medium text-amber-light transition-colors hover:bg-amber-dim hover:text-amber"
                      title="Neue Analyse starten"
                    >
                      Neue Suche
                    </button>
                  </div>
                </div>
              </div>

              {/* Similar songs */}
              {result.similar_songs.length > 0 ? (
                <SimilarResults
                  results={result.similar_songs}
                  querySong={querySong}
                  onFeedback={(qId, rId, rating) => {
                    console.log(`Feedback: ${rating} for ${qId} → ${rId}`);
                  }}
                  focus={focus}
                  onFocusChange={handleFocusChange}
                  focusLoading={focusLoading}
                  onAddToPlaylist={handleAddToPlaylist}
                />
              ) : (
                <p className="text-sm text-text-tertiary">Keine ähnlichen Songs gefunden.</p>
              )}

            </motion.div>
          )}
        {/* Blend mode */}
        {phase === "blend" && (
          <motion.div
            key="blend"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <MultiSongSearch mode="blend" onResults={handleMultiResults} onCancel={handleReset} />
          </motion.div>
        )}

        {/* Vibe mode */}
        {phase === "vibe" && (
          <motion.div
            key="vibe"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <MultiSongSearch mode="vibe" onResults={handleMultiResults} onCancel={handleReset} />
          </motion.div>
        )}

        {/* Journey mode */}
        {phase === "journey" && querySong && (
          <motion.div
            key="journey"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <JourneyView startSong={querySong} onExit={handleReset} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Playlist FAB + Panel */}
      {playlist.length > 0 && (
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
      )}
    </div>
  );
}
