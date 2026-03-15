"use client";

import { useEffect, useRef } from "react";

export default function MouseGlow() {
  const glowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (glowRef.current) {
        glowRef.current.style.setProperty("--mouse-x", `${e.clientX}px`);
        glowRef.current.style.setProperty("--mouse-y", `${e.clientY}px`);
      }
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <div
      ref={glowRef}
      className="pointer-events-none fixed inset-0 transition-opacity duration-500"
      style={{
        zIndex: -1,
        background: `
          radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%),
            rgba(245, 158, 11, 0.06) 0%,
            rgba(167, 139, 250, 0.03) 30%,
            transparent 70%
          )
        `,
      }}
    />
  );
}
