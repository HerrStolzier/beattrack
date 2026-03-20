"use client";

import { useEffect, useRef, useState } from "react";
import { pingHealth } from "../../lib/api";

type ApiState = "checking" | "healthy" | "warming" | "down";

const RETRY_INTERVAL_MS = 10_000;
const DOWN_THRESHOLD_MS = 60_000;

export default function ApiStatus() {
  const [state, setState] = useState<ApiState>("checking");
  const startRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    startRef.current = Date.now();
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

    check();
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
      <div className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-text-tertiary">
        <span className="inline-block h-1.5 w-1.5 flex-shrink-0 animate-pulse rounded-full bg-amber" />
        Backend wird aufgeweckt — gleich gehts los
      </div>
    );
  }

  return (
    <div className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-red-400">
      <span className="inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full bg-red-500" />
      Backend nicht erreichbar
    </div>
  );
}
