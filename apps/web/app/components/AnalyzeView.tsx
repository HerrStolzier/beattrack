"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadAudio, findSimilar, identifyUrl, detectPlatform, NetworkError, TimeoutError, ApiError, type AnalysisResult, type IdentifyResponse, type SimilarSong, type Song } from "@/lib/api";
import UploadZone from "./UploadZone";
import ProgressTracker from "./ProgressTracker";
import UrlInput from "./UrlInput";
import SimilarResults from "./SimilarResults";
import JourneyView from "./JourneyView";
import Button from "./Button";

type AnalyzePhase = "idle" | "uploading" | "processing" | "results" | "error" | "youtube-result" | "journey";

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

  const handleYouTubeMatch = useCallback(async (identifyResult: IdentifyResponse) => {
    setYtResult(identifyResult);
    setPhase("youtube-result");

    // If we got a match, find similar songs for it
    if (identifyResult.matched && identifyResult.song) {
      try {
        const similar = await findSimilar(identifyResult.song.id);
        setResult({
          song_id: identifyResult.song.id,
          bpm: identifyResult.song.bpm || 0,
          key: identifyResult.song.musical_key || "",
          duration: identifyResult.song.duration_sec || 0,
          similar_songs: similar,
        });
      } catch {
        // Similar search failed, but YouTube match still valid
      }
    }
  }, []);

  const handleReset = useCallback(() => {
    setPhase("idle");
    setJobId(null);
    setError(null);
    setResult(null);
    setYtResult(null);
    setUploadedFileName("");
  }, []);

  // Build a Song object from the result for SimilarResults query display
  const querySong: Song | null = result
    ? {
        id: result.song_id,
        title: ytResult?.parsed_title || uploadedFileName || `Upload ${result.song_id.slice(0, 8)}`,
        artist: ytResult?.parsed_artist || "Unbekannt",
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

        {/* YouTube result — no match */}
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
                  <p className="mt-1 text-xs text-text-tertiary">
                    Nicht im Katalog — lade die Audio-Datei hoch oder probier eine andere URL.
                  </p>
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
            <UrlInput onMatch={handleYouTubeMatch} />
            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent to-border-subtle" />
              <span className="text-xs text-text-tertiary font-medium">oder</span>
              <div className="h-px flex-1 bg-gradient-to-l from-transparent to-border-subtle" />
            </div>
            <UploadZone onFileSelected={handleFileSelected} />
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
                />
              ) : (
                <p className="text-sm text-text-tertiary">Keine ähnlichen Songs gefunden.</p>
              )}

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
    </div>
  );
}
