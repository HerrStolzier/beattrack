"use client";

import type { RadarFeatures } from "@/lib/api";

interface FeatureExplanationProps {
  queryFeatures: RadarFeatures;
  resultFeatures: RadarFeatures;
}

type Category = {
  key: keyof RadarFeatures;
  label: string;
};

const CATEGORIES: Category[] = [
  { key: "timbre", label: "Klangfarbe" },
  { key: "harmony", label: "Harmonie" },
  { key: "rhythm", label: "Rhythmus" },
  { key: "brightness", label: "Helligkeit" },
  { key: "intensity", label: "Intensität" },
];

function similarityColor(diff: number): string {
  if (diff < 0.15) return "bg-emerald/70";
  if (diff < 0.35) return "bg-amber/60";
  return "bg-surface-elevated";
}

function similarityTitle(diff: number): string {
  if (diff < 0.15) return "Sehr ähnlich";
  if (diff < 0.35) return "Mittel ähnlich";
  return "Weniger ähnlich";
}

export default function FeatureExplanation({ queryFeatures, resultFeatures }: FeatureExplanationProps) {
  const similar = CATEGORIES.filter((c) => Math.abs(queryFeatures[c.key] - resultFeatures[c.key]) < 0.15);

  return (
    <div className="mt-1.5 flex items-center gap-1" title={similar.length > 0 ? `Ähnlich bei: ${similar.map((c) => c.label).join(", ")}` : "Wenige Gemeinsamkeiten"}>
      {CATEGORIES.map((c) => {
        const diff = Math.abs(queryFeatures[c.key] - resultFeatures[c.key]);
        return (
          <span
            key={c.key}
            className={`inline-block h-2 w-2 rounded-full ${similarityColor(diff)}`}
            title={`${c.label}: ${similarityTitle(diff)}`}
          />
        );
      })}
      {similar.length > 0 && (
        <span className="text-[10px] text-text-tertiary ml-1">
          {similar.map((c) => c.label).join(", ")}
        </span>
      )}
    </div>
  );
}
