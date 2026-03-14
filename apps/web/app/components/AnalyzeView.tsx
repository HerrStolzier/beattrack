"use client";

import { useCallback, useState } from "react";
import { uploadAudio, findSimilar, NetworkError, TimeoutError, ApiError, type AnalysisResult, type IdentifyResponse, type SimilarSong, type Song } from "@/lib/api";
import UploadZone from "./UploadZone";
import ProgressTracker from "./ProgressTracker";
import UrlInput from "./UrlInput";
import SimilarResults from "./SimilarResults";

type AnalyzePhase = "idle" | "uploading" | "processing" | "results" | "error" | "youtube-result";

export default function AnalyzeView() {
  const [phase, setPhase] = useState<AnalyzePhase>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [ytResult, setYtResult] = useState<IdentifyResponse | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>("");

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
      }
    : ytResult?.song || null;

  return (
    <div className="space-y-6">
      {/* Upload Zone — only show in idle */}
      {phase === "idle" && (
        <>
          <UploadZone onFileSelected={handleFileSelected} />

          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border-subtle" />
            <span className="text-xs text-text-tertiary">oder</span>
            <div className="h-px flex-1 bg-border-subtle" />
          </div>

          <UrlInput onMatch={handleYouTubeMatch} />
        </>
      )}

      {/* Uploading */}
      {phase === "uploading" && (
        <div className="glass animate-fade-in-up rounded-xl p-6 text-center">
          <svg className="mx-auto mb-3 h-8 w-8 animate-spin text-amber" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
            <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
          </svg>
          <p className="text-sm text-text-secondary">
            Lade <span className="font-medium text-text-primary">{uploadedFileName}</span> hoch...
          </p>
        </div>
      )}

      {/* Processing — SSE Progress */}
      {phase === "processing" && jobId && (
        <ProgressTracker jobId={jobId} onComplete={handleComplete} onError={handleError} />
      )}

      {/* Error */}
      {phase === "error" && (
        <div className="animate-fade-in-up rounded-xl border border-red-900/50 bg-red-950/30 p-6">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={() => {
              setPhase("idle");
              setError(null);
              setUploadedFileName("");
            }}
            className="mt-3 rounded-lg bg-amber/20 px-4 py-2 text-xs text-amber-light transition-colors hover:bg-amber/30"
          >
            Nochmal versuchen
          </button>
        </div>
      )}

      {/* YouTube result — no match */}
      {phase === "youtube-result" && ytResult && !ytResult.matched && (
        <div className="glass animate-fade-in-up rounded-xl p-6">
          <p className="text-sm text-text-primary">
            <span className="font-medium">{ytResult.parsed_artist}</span>
            {" — "}
            <span className="font-medium">{ytResult.parsed_title}</span>
          </p>
          <p className="mt-2 text-sm text-text-tertiary">{ytResult.message}</p>
          <button
            onClick={handleReset}
            className="mt-3 text-xs text-amber-light underline hover:text-amber"
          >
            Audio-Datei hochladen
          </button>
        </div>
      )}

      {/* Results — from upload or YouTube match */}
      {(phase === "results" || (phase === "youtube-result" && ytResult?.matched)) &&
        result &&
        querySong && (
          <div className="animate-fade-in-up space-y-4">
            {/* Song info header */}
            <div className="glass rounded-xl p-4">
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

            <button
              onClick={handleReset}
              className="text-xs text-text-secondary underline hover:text-text-primary"
            >
              Neue Analyse starten
            </button>
          </div>
        )}
    </div>
  );
}
