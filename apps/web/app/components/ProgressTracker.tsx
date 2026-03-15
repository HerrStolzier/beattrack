"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { streamProgress, getJobResults, type AnalysisResult } from "@/lib/api";

type ProgressTrackerProps = {
  jobId: string;
  onComplete: (result: AnalysisResult) => void;
  onError: (error: string) => void;
};

const COLD_START_THRESHOLD_MS = 20_000;

export default function ProgressTracker({ jobId, onComplete, onError }: ProgressTrackerProps) {
  const [status, setStatus] = useState<string>("queued");
  const [progress, setProgress] = useState(0);
  const [showColdStart, setShowColdStart] = useState(false);
  const [sseConnected, setSseConnected] = useState(true);
  const startTime = useRef(Date.now());
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    // Cold-start timer: show message if no progress after threshold
    const timer = setTimeout(() => {
      setShowColdStart(true);
    }, COLD_START_THRESHOLD_MS);

    // Start SSE stream
    const cleanup = streamProgress(
      jobId,
      (event) => {
        setStatus(event.status);
        setProgress(event.progress);
        // Hide cold-start message once we get progress
        if (event.progress > 0) setShowColdStart(false);

        if (event.status === "completed" && event.result) {
          onComplete(event.result);
        } else if (event.status === "failed") {
          onError(event.error || "Analyse fehlgeschlagen");
        }
      },
      (err) => {
        setSseConnected(false);
        // Fallback to polling
        pollResults();
      }
    );

    cleanupRef.current = cleanup;

    return () => {
      clearTimeout(timer);
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  async function pollResults() {
    const maxAttempts = 60;
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const job = await getJobResults(jobId);
        setStatus(job.status);
        setProgress(job.progress);

        if (job.status === "completed" && job.result) {
          onComplete(job.result);
          return;
        }
        if (job.status === "failed") {
          onError(job.error || "Analyse fehlgeschlagen");
          return;
        }
      } catch {
        // ignore polling errors
      }
      await new Promise((r) => setTimeout(r, 3000));
    }
    onError("Timeout — keine Ergebnisse nach 3 Minuten.");
  }

  const pct = Math.round(progress * 100);
  const elapsed = Math.round((Date.now() - startTime.current) / 1000);

  const statusText = {
    queued: "In der Warteschlange...",
    processing: "Analyse läuft...",
    completed: "Fertig!",
    failed: "Fehler",
  }[status] || status;

  return (
    <motion.div
      className="glass-premium rounded-xl p-6"
      data-testid="progress-tracker"
      animate={
        status === "processing"
          ? {
              boxShadow: [
                "0 0 20px rgba(245,158,11,0.1)",
                "0 0 40px rgba(245,158,11,0.2)",
                "0 0 20px rgba(245,158,11,0.1)",
              ],
            }
          : {}
      }
      transition={{ duration: 2, repeat: Infinity }}
    >
      <div className="mb-4 flex items-center justify-between">
        <motion.span
          key={statusText}
          className="text-sm font-medium text-text-secondary"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {statusText}
        </motion.span>
        <span className="text-xs font-display text-amber-light">{pct}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-2 overflow-hidden rounded-full bg-surface-raised">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-amber via-gold to-amber-light relative overflow-hidden"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 50, damping: 15 }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {/* Shimmer overlay */}
          <div className="absolute inset-0 shimmer opacity-30" />
        </motion.div>
      </div>

      {/* Cold-start message */}
      {showColdStart && status === "queued" && (
        <p className="mt-3 flex items-center text-xs text-amber" data-testid="cold-start-message">
          <span className="inline-block w-2 h-2 rounded-full bg-amber animate-pulse mr-2" aria-hidden="true" />
          Server wacht gerade auf... Das kann beim ersten Start 30-90 Sekunden dauern.
        </p>
      )}

      {/* SSE fallback notice */}
      {!sseConnected && (
        <p className="mt-2 text-xs text-amber/80">
          Live-Verbindung unterbrochen. Status wird per Polling aktualisiert.
        </p>
      )}

      {/* Elapsed time */}
      {status !== "completed" && status !== "failed" && (
        <p className="mt-2 text-xs text-text-tertiary">{elapsed}s vergangen</p>
      )}
    </motion.div>
  );
}
