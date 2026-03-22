'use client';

import { useEffect, useRef, useState } from 'react';

export default function LensDistortion() {
  const [pos, setPos] = useState({ x: 50, y: 50 });
  const rafRef = useRef<number | undefined>(undefined);
  const mouseRef = useRef({ x: 50, y: 50 });
  const smoothRef = useRef({ x: 50, y: 50 });

  useEffect(() => {
    if (
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return;
    }

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = {
        x: (e.clientX / window.innerWidth) * 100,
        y: (e.clientY / window.innerHeight) * 100,
      };
    };

    const animate = () => {
      smoothRef.current.x += (mouseRef.current.x - smoothRef.current.x) * 0.06;
      smoothRef.current.y += (mouseRef.current.y - smoothRef.current.y) * 0.06;

      setPos({
        x: Math.round(smoothRef.current.x * 10) / 10,
        y: Math.round(smoothRef.current.y * 10) / 10,
      });

      rafRef.current = requestAnimationFrame(animate);
    };

    window.addEventListener('mousemove', handleMouseMove);
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div
      className="fixed inset-0 pointer-events-none hidden sm:block"
      style={{
        zIndex: 2,
        background: [
          `radial-gradient(ellipse 600px 500px at calc(${pos.x}% + 18px) ${pos.y}%, rgba(245, 158, 11, 0.18), rgba(245, 80, 20, 0.06) 50%, transparent 80%)`,
          `radial-gradient(ellipse 600px 500px at calc(${pos.x}% - 18px) ${pos.y}%, rgba(167, 139, 250, 0.12), rgba(34, 211, 238, 0.04) 50%, transparent 80%)`,
          `radial-gradient(ellipse 400px 350px at ${pos.x}% calc(${pos.y}% - 8px), rgba(240, 165, 0, 0.1), transparent 65%)`,
        ].join(', '),
      }}
    />
  );
}
