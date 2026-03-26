"use client";

import ProgressTracker from "../ProgressTracker";
import type { AnalysisResult } from "@/lib/api";

interface ProcessingPhaseProps {
  phase: "uploading" | "processing";
  jobId: string | null;
  uploadedFileName: string;
  onComplete: (result: AnalysisResult) => void;
  onError: (errMsg: string) => void;
}

export default function ProcessingPhase({
  phase,
  jobId,
  uploadedFileName,
  onComplete,
  onError,
}: ProcessingPhaseProps) {
  if (phase === "uploading") {
    return (
      <div className="glass-premium rounded-xl p-8 text-center">
        <svg className="mx-auto mb-3 h-8 w-8 animate-spin text-amber" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
          <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
        </svg>
        <p className="text-sm text-text-secondary">
          Lade <span className="font-medium text-text-primary">{uploadedFileName}</span> hoch...
        </p>
      </div>
    );
  }

  if (phase === "processing" && jobId) {
    return (
      <ProgressTracker jobId={jobId} onComplete={onComplete} onError={onError} />
    );
  }

  return null;
}
