"use client";
import { useEffect, useRef } from "react";

interface InkDrop {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  opacity: number;
  color: string;
  birthTime: number;
  lifetime: number;
}

const COLORS = [
  "rgba(245, 158, 11, {opacity})", // amber
  "rgba(167, 139, 250, {opacity})", // violet
  "rgba(34, 211, 238, {opacity})", // cyan
  "rgba(251, 113, 133, {opacity})", // rose
];

const DROP_SPAWN_INTERVAL = 80; // ms
const MIN_DISTANCE_THRESHOLD = 15; // pixels
const MAX_DROPS = 40;
const DROP_LIFETIME = 1200; // ms
const INITIAL_RADIUS = 8;
const MAX_RADIUS = 120;
const INITIAL_OPACITY = 0.12;

export default function MouseGlow() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dropsRef = useRef<InkDrop[]>([]);
  const mouseRef = useRef({ x: 0, y: 0 });
  const lastSpawnTimeRef = useRef(0);
  const lastMousePosRef = useRef({ x: 0, y: 0 });
  const animationIdRef = useRef<number | undefined>(undefined);
  const colorIndexRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Set canvas size
    const updateCanvasSize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    updateCanvasSize();

    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };

      // Spawn new drop if enough time has passed and mouse moved enough distance
      const now = performance.now();
      const timeSinceLastSpawn = now - lastSpawnTimeRef.current;
      const distanceMoved = Math.hypot(
        e.clientX - lastMousePosRef.current.x,
        e.clientY - lastMousePosRef.current.y
      );

      if (
        timeSinceLastSpawn > DROP_SPAWN_INTERVAL &&
        distanceMoved > MIN_DISTANCE_THRESHOLD
      ) {
        if (!prefersReducedMotion && dropsRef.current.length < MAX_DROPS) {
          const colorTemplate = COLORS[colorIndexRef.current % COLORS.length];
          colorIndexRef.current++;

          dropsRef.current.push({
            x: e.clientX,
            y: e.clientY,
            radius: INITIAL_RADIUS,
            maxRadius: MAX_RADIUS,
            opacity: INITIAL_OPACITY,
            color: colorTemplate,
            birthTime: now,
            lifetime: DROP_LIFETIME,
          });
        }
        lastSpawnTimeRef.current = now;
        lastMousePosRef.current = { x: e.clientX, y: e.clientY };
      }
    };

    const animate = () => {
      const now = performance.now();

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (prefersReducedMotion) {
        // Fallback: simple static radial gradient
        const gradient = ctx.createRadialGradient(
          mouseRef.current.x,
          mouseRef.current.y,
          0,
          mouseRef.current.x,
          mouseRef.current.y,
          400
        );
        gradient.addColorStop(0, "rgba(245, 158, 11, 0.08)");
        gradient.addColorStop(0.5, "rgba(167, 139, 250, 0.04)");
        gradient.addColorStop(1, "rgba(34, 211, 238, 0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        animationIdRef.current = requestAnimationFrame(animate);
        return;
      }

      // Update and render drops
      ctx.globalCompositeOperation = "screen";

      dropsRef.current = dropsRef.current.filter((drop) => {
        const elapsed = now - drop.birthTime;
        const progress = Math.min(elapsed / drop.lifetime, 1);

        // Fade out opacity
        drop.opacity = INITIAL_OPACITY * (1 - progress);

        // Expand radius
        drop.radius = INITIAL_RADIUS + (drop.maxRadius - INITIAL_RADIUS) * progress;

        if (drop.opacity <= 0.001) {
          return false;
        }

        // Create radial gradient for soft edges
        const gradient = ctx.createRadialGradient(
          drop.x,
          drop.y,
          0,
          drop.x,
          drop.y,
          drop.radius
        );

        const colorWithOpacity = drop.color.replace(
          "{opacity}",
          String(drop.opacity)
        );

        gradient.addColorStop(0, colorWithOpacity);
        gradient.addColorStop(0.7, colorWithOpacity.replace(/[\d.]+\)$/, `${drop.opacity * 0.5})`));
        gradient.addColorStop(1, colorWithOpacity.replace(/[\d.]+\)$/, "0)"));

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(drop.x, drop.y, drop.radius, 0, Math.PI * 2);
        ctx.fill();

        return true;
      });

      ctx.globalCompositeOperation = "source-over";
      animationIdRef.current = requestAnimationFrame(animate);
    };

    // Apply blur filter to canvas
    canvas.style.filter = "blur(40px)";

    window.addEventListener("mousemove", handleMouseMove);
    const resizeObserver = new ResizeObserver(updateCanvasSize);
    resizeObserver.observe(document.body);

    // Start animation loop
    animationIdRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      resizeObserver.disconnect();
      if (animationIdRef.current !== undefined) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0"
      style={{ zIndex: -1 }}
    />
  );
}
