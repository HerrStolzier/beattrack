"use client";

import { useEffect, useRef, useState } from "react";
import { pingHealth } from "../../lib/api";

type ApiState = "checking" | "healthy" | "warming" | "down";

const RETRY_INTERVAL_MS = 10_000;
const DOWN_THRESHOLD_MS = 60_000;

export default function ApiStatus() {
  const [state, setState] = useState<ApiState>("checking");
  const startRef = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      const ok = await pingHealth();
      if (cancelled) return;

      if (ok) {
        setState("healthy");
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        return;
      }

      const elapsed = Date.now() - startRef.current;
      setState(elapsed >= DOWN_THRESHOLD_MS ? "down" : "warming");
    }

    // Initial check
    check();

    // Retry every 10s
    timerRef.current = setInterval(check, RETRY_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  if (state === "checking" || state === "healthy") return null;

  if (state === "warming") {
    return (
      <div className="mb-4 flex items-center gap-3 rounded-xl border border-yellow-500/20 bg-zinc-900 p-3">
        <span className="inline-block h-2 w-2 flex-shrink-0 animate-pulse rounded-full bg-yellow-500" />
        <p className="text-sm text-yellow-500">Backend startet gerade...</p>
      </div>
    );
  }

  // "down"
  return (
    <div className="mb-4 flex items-center gap-3 rounded-xl border border-red-500/20 bg-zinc-900 p-3">
      <span className="inline-block h-2 w-2 flex-shrink-0 rounded-full bg-red-400" />
      <p className="text-sm text-red-400">
        Backend nicht erreichbar. Bitte später erneut versuchen.
      </p>
    </div>
  );
}
