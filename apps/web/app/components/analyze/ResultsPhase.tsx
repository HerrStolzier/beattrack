"use client";

import SimilarResults from "../SimilarResults";
import Button from "../Button";
import type { AnalysisResult, IdentifyResponse, Song, FocusCategory } from "@/lib/api";
import type { AnalyzePhase } from "@/app/hooks/useAnalyzeState";

interface ResultsPhaseProps {
  result: AnalysisResult;
  querySong: Song;
  ytResult: IdentifyResponse | null;
  focus: FocusCategory | null;
  focusLoading: boolean;
  onFocusChange: (focus: FocusCategory | null) => Promise<void>;
  onAddToPlaylist: (song: Song) => void;
  onReset: () => void;
  setPhase: (phase: AnalyzePhase) => void;
}

export default function ResultsPhase({
  result,
  querySong,
  focus,
  focusLoading,
  onFocusChange,
  onAddToPlaylist,
  onReset,
  setPhase,
}: ResultsPhaseProps) {
  return (
    <div className="space-y-4">
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
                <span>
                  {Math.floor(result.duration / 60)}:
                  {String(Math.floor(result.duration % 60)).padStart(2, "0")}
                </span>
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
              onClick={onReset}
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
          onFocusChange={onFocusChange}
          focusLoading={focusLoading}
          onAddToPlaylist={onAddToPlaylist}
        />
      ) : (
        <p className="text-sm text-text-tertiary">Keine ähnlichen Songs gefunden.</p>
      )}
    </div>
  );
}
