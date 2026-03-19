"use client";

import { toCamelot, getHarmonicCompatibility, getBpmMatch, getBpmDiff } from "@/lib/harmonic";

interface HarmonicBadgeProps {
  queryKey: string | null | undefined;
  queryBpm: number | null | undefined;
  resultKey: string | null | undefined;
  resultBpm: number | null | undefined;
}

const COMPAT_STYLES = {
  perfect: { dot: "bg-emerald-400", text: "text-emerald-400", label: "Harmonisch" },
  compatible: { dot: "bg-amber-400", text: "text-amber-400", label: "Geht" },
  incompatible: { dot: "bg-text-tertiary", text: "text-text-tertiary", label: "Clash" },
} as const;

export default function HarmonicBadge({ queryKey, queryBpm, resultKey, resultBpm }: HarmonicBadgeProps) {
  const camelot = toCamelot(resultKey);
  const compat = getHarmonicCompatibility(queryKey, resultKey);
  const bpmMatch = getBpmMatch(queryBpm, resultBpm);
  const bpmDiff = getBpmDiff(queryBpm, resultBpm);

  if (!camelot && bpmDiff == null) return null;

  const style = compat ? COMPAT_STYLES[compat] : null;

  return (
    <div className="flex items-center gap-1.5 text-[10px]">
      {/* Camelot code + compatibility dot */}
      {camelot && style ? (
        <span className={`flex items-center gap-1 rounded-full bg-surface-raised px-2 py-0.5 font-mono ${style.text}`}>
          <span className={`inline-block h-1.5 w-1.5 rounded-full ${style.dot}`} />
          {camelot}
        </span>
      ) : camelot ? (
        <span className="rounded-full bg-surface-raised px-2 py-0.5 font-mono text-text-tertiary">
          {camelot}
        </span>
      ) : null}

      {/* BPM diff */}
      {bpmDiff != null && bpmDiff !== 0 && (
        <span className={`flex items-center gap-1 rounded-full bg-surface-raised px-2 py-0.5 font-mono ${
          bpmMatch === "exact" ? "text-emerald-400" :
          bpmMatch === "close" ? "text-amber-400" :
          "text-text-tertiary"
        }`}>
          {bpmDiff > 0 ? "+" : ""}{bpmDiff}
          <span className="text-[8px] font-normal opacity-60">BPM</span>
        </span>
      )}
    </div>
  );
}
