"use client";

import { useEffect, useRef } from "react";

interface Blob {
  x: number;
  y: number;
  vx: number;
  vy: number;
  targetX: number;
  targetY: number;
  radius: number;
  color: string;
  phase: number;
  phaseSpeed: number;
}

const COLORS = ["#f59e0b", "#a78bfa", "#22d3ee", "#fb7185", "#f0a500"];
const BLOB_COUNT = 6;
const MOUSE_INFLUENCE_RADIUS = 250;
const MOUSE_INFLUENCE_STRENGTH = 0.3;
const DRIFT_SPEED = 0.4;
const OPACITY = 0.12;

export default function MeshGradient() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const blobsRef = useRef<Blob[]>([]);
  const mouseRef = useRef({ x: 0, y: 0 });
  const animationIdRef = useRef<number | undefined>(undefined);
  const prefersReducedMotionRef = useRef(false);

  // Initialize blobs
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const width = canvas.width;
    const height = canvas.height;

    blobsRef.current = Array.from({ length: BLOB_COUNT }, (_, i) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      targetX: Math.random() * width,
      targetY: Math.random() * height,
      radius: 80 + Math.random() * 60,
      color: COLORS[i % COLORS.length],
      phase: Math.random() * Math.PI * 2,
      phaseSpeed: 0.01 + Math.random() * 0.01,
    }));
  }, []);

  // Check for prefers-reduced-motion
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    prefersReducedMotionRef.current = mediaQuery.matches;

    const handleChange = (e: MediaQueryListEvent) => {
      prefersReducedMotionRef.current = e.matches;
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // Mouse tracking
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // Handle resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const updateSize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        const dpr = window.devicePixelRatio || 1;
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;

        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.scale(dpr, dpr);
        }
      }
    };

    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const animate = () => {
      const width = canvas.width;
      const height = canvas.height;

      // Clear canvas
      ctx.fillStyle = "rgba(0, 0, 0, 0)";
      ctx.clearRect(0, 0, width, height);

      const blobs = blobsRef.current;
      const mouseX = mouseRef.current.x;
      const mouseY = mouseRef.current.y;
      const prefersReducedMotion = prefersReducedMotionRef.current;

      blobs.forEach((blob) => {
        if (!prefersReducedMotion) {
          // Update phase for sinusoidal motion
          blob.phase += blob.phaseSpeed;

          // Calculate target position with sinusoidal drift
          const driftX = Math.sin(blob.phase) * 100;
          const driftY = Math.cos(blob.phase * 0.7) * 100;

          blob.targetX = Math.sin(blob.phase * 0.3) * (width * 0.3) + width * 0.5;
          blob.targetY = Math.cos(blob.phase * 0.25) * (height * 0.3) + height * 0.5;

          // Apply mouse influence (repulsion)
          const dx = blob.x - mouseX;
          const dy = blob.y - mouseY;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < MOUSE_INFLUENCE_RADIUS && distance > 0) {
            const angle = Math.atan2(dy, dx);
            const influence =
              (1 - distance / MOUSE_INFLUENCE_RADIUS) *
              MOUSE_INFLUENCE_STRENGTH;
            blob.vx += Math.cos(angle) * influence;
            blob.vy += Math.sin(angle) * influence;
          }

          // Apply damping and drift toward target
          blob.vx *= 0.98;
          blob.vy *= 0.98;
          blob.vx += (blob.targetX - blob.x) * DRIFT_SPEED * 0.0001;
          blob.vy += (blob.targetY - blob.y) * DRIFT_SPEED * 0.0001;

          // Update position
          blob.x += blob.vx;
          blob.y += blob.vy;

          // Wrap around edges
          if (blob.x < -blob.radius) blob.x = width + blob.radius;
          if (blob.x > width + blob.radius) blob.x = -blob.radius;
          if (blob.y < -blob.radius) blob.y = height + blob.radius;
          if (blob.y > height + blob.radius) blob.y = -blob.radius;
        }

        // Draw blob with radial gradient
        const gradient = ctx.createRadialGradient(
          blob.x,
          blob.y,
          0,
          blob.x,
          blob.y,
          blob.radius
        );

        // Parse color and convert to RGBA with opacity
        const rgb = parseInt(blob.color.slice(1), 16);
        const r = (rgb >> 16) & 255;
        const g = (rgb >> 8) & 255;
        const b = rgb & 255;

        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${OPACITY})`);
        gradient.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${OPACITY * 0.5})`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);

        ctx.fillStyle = gradient;
        ctx.globalCompositeOperation = "lighter";
        ctx.fillRect(0, 0, width, height);
      });

      animationIdRef.current = requestAnimationFrame(animate);
    };

    animationIdRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="pointer-events-none fixed inset-0 overflow-hidden"
      aria-hidden="true"
      style={{ zIndex: -1 }}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        style={{
          filter: "blur(60px)",
          width: "100%",
          height: "100%",
        }}
      />
    </div>
  );
}
