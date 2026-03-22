'use client';

import { useEffect, useRef } from 'react';

export default function LensDistortion() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mousePos = useRef({ x: 0, y: 0 });
  const smoothPos = useRef({ x: 0, y: 0 });
  const animationFrameId = useRef<number | undefined>(undefined);
  const timeRef = useRef(0);

  useEffect(() => {
    if (
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const updateSize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      ctx.scale(dpr, dpr);
    };
    updateSize();

    const handleMouseMove = (e: MouseEvent) => {
      mousePos.current = { x: e.clientX, y: e.clientY };
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        mousePos.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    };

    const animate = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;

      // Smooth cursor follow
      smoothPos.current.x += (mousePos.current.x - smoothPos.current.x) * 0.06;
      smoothPos.current.y += (mousePos.current.y - smoothPos.current.y) * 0.06;

      timeRef.current += 0.003;

      ctx.clearRect(0, 0, w, h);

      const cx = smoothPos.current.x;
      const cy = smoothPos.current.y;

      // Chromatic aberration: offset colored radial gradients around cursor
      const radius = 300 + Math.sin(timeRef.current * 0.5) * 40;
      const offset = 12 + Math.sin(timeRef.current * 0.3) * 6;

      ctx.globalCompositeOperation = 'screen';

      // Red/amber channel — shifted right
      const redGrad = ctx.createRadialGradient(cx + offset, cy, 0, cx + offset, cy, radius);
      redGrad.addColorStop(0, 'rgba(245, 158, 11, 0.25)');
      redGrad.addColorStop(0.3, 'rgba(245, 80, 20, 0.12)');
      redGrad.addColorStop(0.7, 'rgba(245, 80, 20, 0.03)');
      redGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = redGrad;
      ctx.fillRect(0, 0, w, h);

      // Blue/violet channel — shifted left
      const blueGrad = ctx.createRadialGradient(cx - offset, cy, 0, cx - offset, cy, radius);
      blueGrad.addColorStop(0, 'rgba(167, 139, 250, 0.2)');
      blueGrad.addColorStop(0.3, 'rgba(34, 211, 238, 0.08)');
      blueGrad.addColorStop(0.7, 'rgba(34, 211, 238, 0.02)');
      blueGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = blueGrad;
      ctx.fillRect(0, 0, w, h);

      // Center amber glow
      const centerGrad = ctx.createRadialGradient(cx, cy - offset * 0.3, 0, cx, cy - offset * 0.3, radius * 0.6);
      centerGrad.addColorStop(0, 'rgba(240, 165, 0, 0.15)');
      centerGrad.addColorStop(0.5, 'rgba(240, 165, 0, 0.04)');
      centerGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = centerGrad;
      ctx.fillRect(0, 0, w, h);

      ctx.globalCompositeOperation = 'source-over';

      animationFrameId.current = requestAnimationFrame(animate);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('touchmove', handleTouchMove);
    window.addEventListener('resize', updateSize);

    animationFrameId.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('resize', updateSize);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{
        zIndex: 1,
        mixBlendMode: 'screen',
        width: '100%',
        height: '100%',
      }}
    />
  );
}
