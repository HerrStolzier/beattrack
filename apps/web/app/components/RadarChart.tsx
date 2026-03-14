"use client";

import { useEffect, useState } from "react";
import { getSongFeatures, type RadarFeatures } from "@/lib/api";

type RadarChartProps = {
  querySongId: string;
  resultSongId: string;
};

const CATEGORIES = ["Klangfarbe", "Harmonie", "Rhythmus", "Helligkeit", "Intensität"] as const;
const KEYS: (keyof RadarFeatures)[] = ["timbre", "harmony", "rhythm", "brightness", "intensity"];

const SIZE = 160;
const CENTER = SIZE / 2;
const RADIUS = 60;
const LEVELS = 4;

function polarToCartesian(angle: number, r: number): [number, number] {
  // Start from top (subtract 90deg)
  const rad = ((angle - 90) * Math.PI) / 180;
  return [CENTER + r * Math.cos(rad), CENTER + r * Math.sin(rad)];
}

function polygonPoints(values: number[]): string {
  const n = values.length;
  return values
    .map((v, i) => {
      const angle = (360 / n) * i;
      const [x, y] = polarToCartesian(angle, v * RADIUS);
      return `${x},${y}`;
    })
    .join(" ");
}

export default function RadarChart({ querySongId, resultSongId }: RadarChartProps) {
  const [queryFeatures, setQueryFeatures] = useState<RadarFeatures | null>(null);
  const [resultFeatures, setResultFeatures] = useState<RadarFeatures | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);

    Promise.all([
      getSongFeatures(querySongId).catch(() => null),
      getSongFeatures(resultSongId).catch(() => null),
    ]).then(([q, r]) => {
      if (q) setQueryFeatures(q);
      if (r) setResultFeatures(r);
      if (!q && !r) setError(true);
      setLoading(false);
    });
  }, [querySongId, resultSongId]);

  if (loading) {
    return <p className="text-center text-xs text-zinc-500">Lade Features...</p>;
  }

  if (error || (!queryFeatures && !resultFeatures)) {
    return <p className="text-center text-xs text-zinc-600">Keine Feature-Daten verfügbar.</p>;
  }

  const n = CATEGORIES.length;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="h-40 w-40">
        {/* Grid levels */}
        {Array.from({ length: LEVELS }, (_, lvl) => {
          const r = ((lvl + 1) / LEVELS) * RADIUS;
          const pts = Array.from({ length: n }, (_, i) => {
            const angle = (360 / n) * i;
            const [x, y] = polarToCartesian(angle, r);
            return `${x},${y}`;
          }).join(" ");
          return (
            <polygon
              key={lvl}
              points={pts}
              fill="none"
              stroke="rgb(63 63 70)"
              strokeWidth="0.5"
            />
          );
        })}

        {/* Axis lines */}
        {Array.from({ length: n }, (_, i) => {
          const angle = (360 / n) * i;
          const [x, y] = polarToCartesian(angle, RADIUS);
          return (
            <line
              key={i}
              x1={CENTER}
              y1={CENTER}
              x2={x}
              y2={y}
              stroke="rgb(63 63 70)"
              strokeWidth="0.5"
            />
          );
        })}

        {/* Query song polygon */}
        {queryFeatures && (
          <polygon
            points={polygonPoints(KEYS.map((k) => queryFeatures[k]))}
            fill="rgba(59, 130, 246, 0.15)"
            stroke="rgb(59, 130, 246)"
            strokeWidth="1.5"
          />
        )}

        {/* Result song polygon */}
        {resultFeatures && (
          <polygon
            points={polygonPoints(KEYS.map((k) => resultFeatures[k]))}
            fill="rgba(234, 179, 8, 0.15)"
            stroke="rgb(234, 179, 8)"
            strokeWidth="1.5"
          />
        )}

        {/* Labels */}
        {CATEGORIES.map((label, i) => {
          const angle = (360 / n) * i;
          const [x, y] = polarToCartesian(angle, RADIUS + 14);
          return (
            <text
              key={label}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="central"
              className="fill-zinc-500 text-[7px]"
            >
              {label}
            </text>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-3 text-[10px]">
        {queryFeatures && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-500" />
            Query
          </span>
        )}
        {resultFeatures && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-yellow-500" />
            Ergebnis
          </span>
        )}
      </div>
    </div>
  );
}
