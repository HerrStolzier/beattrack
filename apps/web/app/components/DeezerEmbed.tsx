"use client";

import { useRef, useEffect, useState } from "react";

interface DeezerEmbedProps {
  deezerId: number;
  compact?: boolean;
  autoplay?: boolean;
}

export default function DeezerEmbed({ deezerId, compact = true, autoplay = false }: DeezerEmbedProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className="mt-2">
      {isVisible ? (
        <iframe
          src={`https://widget.deezer.com/widget/dark/track/${deezerId}?autoplay=${autoplay}&radius=true&tracklist=false`}
          width="100%"
          height={80}
          style={{ border: 0, borderRadius: 12 }}
          allow="autoplay; encrypted-media"
          loading="lazy"
          title="Deezer Preview"
        />
      ) : (
        <div className="h-[80px] rounded-xl bg-surface-raised animate-pulse" />
      )}
      {!compact && (
        <a
          href={`https://www.deezer.com/track/${deezerId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-flex items-center gap-1 text-[10px] text-text-tertiary hover:text-text-secondary transition-colors"
        >
          Auf Deezer anhören →
        </a>
      )}
    </div>
  );
}
