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

type ViewMode = "compare" | "query" | "result";

export default function RadarChart({ querySongId, resultSongId }: RadarChartProps) {
  const [queryFeatures, setQueryFeatures] = useState<RadarFeatures | null>(null);
  const [resultFeatures, setResultFeatures] = useState<RadarFeatures | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("compare");

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
    return <p className="text-center text-xs text-text-tertiary">Lade Features...</p>;
  }

  if (error || (!queryFeatures && !resultFeatures)) {
    return <p className="text-center text-xs text-text-tertiary">Keine Feature-Daten verfügbar.</p>;
  }

  const n = CATEGORIES.length;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="h-48 w-48">
        <defs>
          <filter id="glow-amber" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feFlood floodColor="#f59e0b" floodOpacity="0.3" result="color" />
            <feComposite in="color" in2="blur" operator="in" result="glow" />
            <feMerge>
              <feMergeNode in="glow" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feFlood floodColor="#22d3ee" floodOpacity="0.3" result="color" />
            <feComposite in="color" in2="blur" operator="in" result="glow" />
            <feMerge>
              <feMergeNode in="glow" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <radialGradient id="center-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(245,158,11,0.08)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>

        {/* Center ambient glow */}
        <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="url(#center-glow)" />

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
              stroke="rgba(255,255,255,0.08)"
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
              stroke="rgba(255,255,255,0.12)"
              strokeWidth="0.5"
            />
          );
        })}

        {/* Query song polygon */}
        {queryFeatures && (viewMode === "compare" || viewMode === "query") && (
          <polygon
            points={polygonPoints(KEYS.map((k) => queryFeatures[k]))}
            fill="rgba(245,158,11,0.2)"
            stroke="#f59e0b"
            strokeWidth="1.5"
            filter="url(#glow-amber)"
            strokeDasharray="200"
            className="animate-draw-in"
            style={{ transition: "opacity 0.3s" }}
          />
        )}

        {/* Result song polygon */}
        {resultFeatures && (viewMode === "compare" || viewMode === "result") && (
          <polygon
            points={polygonPoints(KEYS.map((k) => resultFeatures[k]))}
            fill="rgba(34,211,238,0.2)"
            stroke="#22d3ee"
            strokeWidth="1.5"
            filter="url(#glow-cyan)"
            strokeDasharray="200"
            className="animate-draw-in stagger-3"
            style={{ transition: "opacity 0.3s" }}
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
              fill="rgba(161,161,170,1)"
              fontSize="7"
            >
              {label}
            </text>
          );
        })}
      </svg>

      {/* A/B Toggle */}
      <div className="flex items-center gap-1 rounded-lg bg-surface-raised p-0.5 text-[10px]">
        <button
          onClick={() => setViewMode("compare")}
          className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
            viewMode === "compare" ? "bg-surface-elevated text-text-primary" : "text-text-tertiary hover:text-text-secondary"
          }`}
        >
          Vergleich
        </button>
        {queryFeatures && (
          <button
            onClick={() => setViewMode("query")}
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors ${
              viewMode === "query" ? "bg-amber/15 text-amber-light" : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
            Query
          </button>
        )}
        {resultFeatures && (
          <button
            onClick={() => setViewMode("result")}
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors ${
              viewMode === "result" ? "bg-cyan/15 text-cyan" : "text-text-tertiary hover:text-text-secondary"
            }`}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-400" />
            Result
          </button>
        )}
      </div>
    </div>
  );
}
