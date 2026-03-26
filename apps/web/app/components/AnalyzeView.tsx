"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAnalyzeState } from "@/app/hooks/useAnalyzeState";
import { useSessionHistory } from "@/app/hooks/useSessionHistory";
import IdlePhase from "./analyze/IdlePhase";
import ProcessingPhase from "./analyze/ProcessingPhase";
import ResultsPhase from "./analyze/ResultsPhase";
import PlaylistPanel from "./analyze/PlaylistPanel";
import Button from "./Button";
import MultiSongSearch from "./MultiSongSearch";
import JourneyView from "./JourneyView";
import UrlInput from "./UrlInput";
import UploadZone from "./UploadZone";

const phaseVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

type AnalyzeViewProps = {
  initialUrl?: string | null;
};

export default function AnalyzeView({ initialUrl }: AnalyzeViewProps) {
  const state = useAnalyzeState(initialUrl);
  const { history, addEntry, clearHistory } = useSessionHistory();

  // Track when a result comes in — save to session history
  const prevPhase = useRef(state.phase);
  useEffect(() => {
    const enteredResults =
      prevPhase.current !== "results" && state.phase === "results";
    const enteredYtMatch =
      prevPhase.current !== "youtube-result" &&
      state.phase === "youtube-result" &&
      state.ytResult?.matched;
    prevPhase.current = state.phase;

    if ((enteredResults || enteredYtMatch) && state.result) {
      const topResult = state.result.similar_songs[0];
      const queryLabel =
        state.querySong?.title ||
        state.ytResult?.parsed_title ||
        state.uploadedFileName ||
        "Unbekannt";
      const entryType =
        state.result.song_id === "multi"
          ? state.multiLabel.includes("Blend") ? "blend" : "vibe"
          : state.ytResult
          ? "url"
          : "upload";
      addEntry({
        type: entryType as "upload" | "url" | "blend" | "vibe",
        query: queryLabel,
        resultCount: state.result.similar_songs.length,
        topResult: topResult
          ? { title: topResult.title, artist: topResult.artist }
          : undefined,
      });
    }
  }, [state.phase]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      <AnimatePresence mode="wait">
        {/* Idle — upload zone + URL input + Blend/Vibe */}
        {state.phase === "idle" && (
          <motion.div
            key="idle"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <IdlePhase
              onMatch={state.handleYouTubeMatch}
              onFileSelected={state.handleFileSelected}
              setPhase={state.setPhase}
              history={history}
              onClearHistory={clearHistory}
            />
          </motion.div>
        )}

        {/* Uploading / Processing */}
        {(state.phase === "uploading" || state.phase === "processing") && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
          >
            <ProcessingPhase
              phase={state.phase}
              jobId={state.jobId}
              uploadedFileName={state.uploadedFileName}
              onComplete={state.handleComplete}
              onError={state.handleError}
            />
          </motion.div>
        )}

        {/* Error */}
        {state.phase === "error" && (
          <motion.div
            key="error"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
            className="rounded-xl border border-error/30 bg-error-dim p-6"
          >
            <p className="text-sm text-error">{state.error}</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                state.setPhase("idle");
              }}
              className="mt-4"
            >
              Nochmal versuchen
            </Button>
          </motion.div>
        )}

        {/* YouTube result — no match (with auto-ingest support) */}
        {state.phase === "youtube-result" && state.ytResult && !state.ytResult.matched && (
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
                    {state.ytResult.parsed_artist} — {state.ytResult.parsed_title}
                  </p>
                  {state.ytResult.ingesting ? (
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
                  onClick={state.handleReset}
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
            {!state.ytResult.ingesting && (
              <>
                <UrlInput onMatch={state.handleYouTubeMatch} />
                <div className="flex items-center gap-3">
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent to-border-subtle" />
                  <span className="text-xs text-text-tertiary font-medium">oder</span>
                  <div className="h-px flex-1 bg-gradient-to-l from-transparent to-border-subtle" />
                </div>
                <UploadZone onFileSelected={state.handleFileSelected} />
              </>
            )}
          </motion.div>
        )}

        {/* Results — from upload or YouTube match */}
        {(state.phase === "results" ||
          (state.phase === "youtube-result" && state.ytResult?.matched)) &&
          state.result &&
          state.querySong && (
            <motion.div
              key="results"
              variants={phaseVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.3 }}
            >
              <ResultsPhase
                result={state.result}
                querySong={state.querySong}
                ytResult={state.ytResult}
                focus={state.focus}
                focusLoading={state.focusLoading}
                onFocusChange={state.handleFocusChange}
                onAddToPlaylist={state.handleAddToPlaylist}
                onReset={state.handleReset}
                setPhase={state.setPhase}
              />
            </motion.div>
          )}

        {/* Blend mode */}
        {state.phase === "blend" && (
          <motion.div
            key="blend"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <MultiSongSearch
              mode="blend"
              onResults={state.handleMultiResults}
              onCancel={state.handleReset}
            />
          </motion.div>
        )}

        {/* Vibe mode */}
        {state.phase === "vibe" && (
          <motion.div
            key="vibe"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <MultiSongSearch
              mode="vibe"
              onResults={state.handleMultiResults}
              onCancel={state.handleReset}
            />
          </motion.div>
        )}

        {/* Journey mode */}
        {state.phase === "journey" && state.querySong && (
          <motion.div
            key="journey"
            variants={phaseVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.3 }}
          >
            <JourneyView startSong={state.querySong} onExit={state.handleReset} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Playlist FAB + Panel */}
      <PlaylistPanel
        playlist={state.playlist}
        playlistOpen={state.playlistOpen}
        setPlaylist={state.setPlaylist}
        setPlaylistOpen={state.setPlaylistOpen}
      />
    </div>
  );
}
