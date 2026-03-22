'use client';

import { useEffect, useRef } from 'react';

export default function LensDistortion() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mousePos = useRef({ x: 0, y: 0 });
  const smoothPos = useRef({ x: 0, y: 0 });
  const animationFrameId = useRef<number | undefined>(undefined);
  const timeRef = useRef(0);
  const prefersReducedMotion = useRef(false);
  const dimensionsRef = useRef({ w: 1024, h: 768 });

  useEffect(() => {
    // Check for prefers-reduced-motion
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefersReducedMotion.current = mediaQuery.matches;

    if (prefersReducedMotion.current) {
      return;
    }

    const handleMouseMove = (e: MouseEvent) => {
      mousePos.current = { x: e.clientX, y: e.clientY };
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        mousePos.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
    };

    const animate = () => {
      const svg = svgRef.current;
      if (!svg) {
        animationFrameId.current = requestAnimationFrame(animate);
        return;
      }

      // Smooth interpolation of mouse position
      smoothPos.current.x += (mousePos.current.x - smoothPos.current.x) * 0.08;
      smoothPos.current.y += (mousePos.current.y - smoothPos.current.y) * 0.08;

      // Increment time for animation
      timeRef.current += 0.004;

      // Animate the distortion filter turbulence
      const turbulence = svg.querySelector('#lensTurbulence') as SVGFETurbulenceElement;
      if (turbulence) {
        const baseFreq = 0.02 + Math.sin(timeRef.current * 0.2) * 0.003;
        turbulence.setAttribute('baseFrequency', baseFreq.toString());
      }

      const displacement = svg.querySelector('#lensDisplacement') as SVGFEDisplacementMapElement;
      if (displacement) {
        const scale = 20 + Math.sin(timeRef.current * 0.5) * 5;
        displacement.setAttribute('scale', scale.toString());
      }

      // Update the radial gradient center to follow cursor
      const radialGradient = svg.querySelector('#lensGradient') as SVGRadialGradientElement;
      if (radialGradient) {
        const cx = (smoothPos.current.x / window.innerWidth) * 100;
        const cy = (smoothPos.current.y / window.innerHeight) * 100;
        radialGradient.setAttribute('cx', `${cx}%`);
        radialGradient.setAttribute('cy', `${cy}%`);
      }

      animationFrameId.current = requestAnimationFrame(animate);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('touchmove', handleTouchMove);

    animationFrameId.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('touchmove', handleTouchMove);
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, []);

  // Update dimensions on mount and resize
  useEffect(() => {
    const update = () => {
      dimensionsRef.current = { w: window.innerWidth, h: window.innerHeight };
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 pointer-events-none"
      style={{
        opacity: 0.15,
        zIndex: 1,
        mixBlendMode: "soft-light",
      }}
    >
      <svg
        ref={svgRef}
        className="w-full h-full"
        preserveAspectRatio="none"
        viewBox="0 0 1024 768"
      >
        <defs>
          {/* Radial gradient centered on cursor for focus */}
          <radialGradient id="lensGradient" r="30%">
            <stop offset="0%" stopColor="rgba(245, 158, 11, 0.8)" stopOpacity="0.8" />
            <stop offset="50%" stopColor="rgba(167, 139, 250, 0.4)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="rgba(34, 211, 238, 0)" stopOpacity="0" />
          </radialGradient>

          {/* Filter for chromatic aberration effect */}
          <filter id="chromaticAberration">
            {/* Red channel with slight positive offset */}
            <feOffset in="SourceGraphic" dx="2" dy="0" result="redOffset" />
            <feComponentTransfer in="redOffset" result="redChannel">
              <feFuncR type="linear" slope="1" />
              <feFuncG type="linear" slope="0" />
              <feFuncB type="linear" slope="0" />
            </feComponentTransfer>

            {/* Blue channel with slight negative offset */}
            <feOffset in="SourceGraphic" dx="-2" dy="0" result="blueOffset" />
            <feComponentTransfer in="blueOffset" result="blueChannel">
              <feFuncR type="linear" slope="0" />
              <feFuncG type="linear" slope="0" />
              <feFuncB type="linear" slope="1" />
            </feComponentTransfer>

            {/* Green channel unchanged */}
            <feComponentTransfer in="SourceGraphic" result="greenChannel">
              <feFuncR type="linear" slope="0" />
              <feFuncG type="linear" slope="1" />
              <feFuncB type="linear" slope="0" />
            </feComponentTransfer>

            {/* Combine all channels */}
            <feMerge>
              <feMergeNode in="redChannel" />
              <feMergeNode in="greenChannel" />
              <feMergeNode in="blueChannel" />
            </feMerge>
          </filter>

          {/* Main distortion filter */}
          <filter id="lensDistortion">
            <feTurbulence
              id="lensTurbulence"
              type="fractalNoise"
              baseFrequency="0.02"
              numOctaves="4"
              result="noise"
              seed="1"
            />
            <feDisplacementMap
              id="lensDisplacement"
              in="SourceGraphic"
              in2="noise"
              scale="20"
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>

        {/* Base overlay rectangle with lens gradient and distortion */}
        <rect
          width="100%"
          height="100%"
          fill="url(#lensGradient)"
          filter="url(#lensDistortion)"
          opacity="0.9"
        />

        {/* Subtle vignette with chromatic aberration for depth */}
        <defs>
          <radialGradient id="vignetteGradient" r="60%">
            <stop offset="0%" stopColor="rgba(0, 0, 0, 0)" stopOpacity="0" />
            <stop offset="100%" stopColor="rgba(0, 0, 0, 0.15)" stopOpacity="0.15" />
          </radialGradient>
        </defs>
        <rect
          width="100%"
          height="100%"
          fill="url(#vignetteGradient)"
          filter="url(#chromaticAberration)"
          opacity="0.5"
        />
      </svg>
    </div>
  );
};
