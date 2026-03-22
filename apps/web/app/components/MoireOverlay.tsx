"use client";

import type { ReactElement } from "react";

interface MoireOverlayProps {
  isActive: boolean;
  mouseX: number;
  mouseY: number;
  color?: string;
}

export default function MoireOverlay({
  isActive,
  mouseX,
  mouseY,
  color = "rgb(245, 158, 11)",
}: MoireOverlayProps) {
  // Extract RGB values from color string
  const getRGBValues = (colorStr: string): [number, number, number] => {
    if (colorStr.startsWith("rgb")) {
      const match = colorStr.match(/\d+/g);
      return match ? ([parseInt(match[0]), parseInt(match[1]), parseInt(match[2])] as [number, number, number]) : [245, 158, 11];
    }
    return [245, 158, 11];
  };

  const [r, g, b] = getRGBValues(color);

  // Check for reduced motion preference
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Pattern spacing and stroke width
  const spacing = 5;
  const strokeWidth = 0.75;

  // Generate concentric circles for pattern
  const generateCircles = (maxRadius: number) => {
    const circles: ReactElement[] = [];
    for (let r = spacing; r <= maxRadius; r += spacing) {
      circles.push(
        <circle
          key={`circle-${r}`}
          cx="50%"
          cy="50%"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          vectorEffect="non-scaling-stroke"
        />
      );
    }
    return circles;
  };

  const maxRadius = 150;

  return (
    <div
      className="pointer-events-none absolute inset-0 rounded-2xl overflow-hidden"
      style={{
        opacity: isActive ? 0.6 : 0,
        transition: "opacity 0.3s ease-out",
      }}
    >
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{
          mixBlendMode: "overlay",
        }}
      >
        <defs>
          {/* Static pattern - concentric circles at center */}
          <pattern
            id="moire-static"
            patternUnits="userSpaceOnUse"
            patternContentUnits="userSpaceOnUse"
            x="0"
            y="0"
            width="100"
            height="100"
          >
            <g
              style={{
                color: `rgba(${r}, ${g}, ${b}, 0.1)`,
              }}
            >
              {generateCircles(maxRadius)}
            </g>
          </pattern>

          {/* Dynamic pattern - offset by mouse position */}
          <pattern
            id="moire-dynamic"
            patternUnits="userSpaceOnUse"
            patternContentUnits="userSpaceOnUse"
            x={prefersReducedMotion ? "0" : `${mouseX - 50}`}
            y={prefersReducedMotion ? "0" : `${mouseY - 50}`}
            width="100"
            height="100"
          >
            <g
              style={{
                color: `rgba(${r}, ${g}, ${b}, 0.08)`,
              }}
            >
              {generateCircles(maxRadius)}
            </g>
          </pattern>
        </defs>

        {/* Layer 1: Static pattern */}
        <rect
          x="0"
          y="0"
          width="100"
          height="100"
          fill="url(#moire-static)"
          vectorEffect="non-scaling-stroke"
        />

        {/* Layer 2: Dynamic pattern for interference */}
        <rect
          x="0"
          y="0"
          width="100"
          height="100"
          fill="url(#moire-dynamic)"
          vectorEffect="non-scaling-stroke"
          style={{
            transition: prefersReducedMotion
              ? "none"
              : "all 0.05s linear",
          }}
        />
      </svg>
    </div>
  );
}
