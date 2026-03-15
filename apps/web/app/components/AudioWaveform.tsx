"use client";

import { useEffect, useState } from "react";

// Deterministic pseudo-random based on index
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

const BARS = Array.from({ length: 40 }, (_, i) => ({
  duration: Math.round((1.2 + seededRandom(i) * 0.8) * 100) / 100,
  height: Math.round(20 + seededRandom(i + 100) * 60),
  delay: Math.round(i * 0.05 * 100) / 100,
}));

export default function AudioWaveform({ className = "" }: { className?: string }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return <div className={`h-12 ${className}`} aria-hidden="true" />;

  return (
    <div className={`flex items-end gap-[2px] h-12 opacity-20 ${className}`} aria-hidden="true">
      {BARS.map((bar, i) => (
        <div
          key={i}
          className="w-[3px] rounded-full bg-gradient-to-t from-amber/60 via-violet/40 to-neon-cyan/30"
          style={{
            animationName: "waveform",
            animationDuration: `${bar.duration}s`,
            animationTimingFunction: "ease-in-out",
            animationIterationCount: "infinite",
            animationDelay: `${bar.delay}s`,
            height: `${bar.height}%`,
          }}
        />
      ))}
    </div>
  );
}
