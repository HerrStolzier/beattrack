"use client";

import { useState } from "react";
import { identifyUrl, detectPlatform, type IdentifyResponse } from "@/lib/api";

type UrlInputProps = {
  onMatch: (result: IdentifyResponse) => void;
  disabled?: boolean;
};

const platformLabels: Record<string, { name: string; color: string; bg: string }> = {
  youtube: { name: "YouTube", color: "text-red-400", bg: "bg-red-500/20" },
  soundcloud: { name: "SoundCloud", color: "text-orange-400", bg: "bg-orange-500/20" },
  spotify: { name: "Spotify", color: "text-emerald-400", bg: "bg-emerald-500/20" },
};

export default function UrlInput({ onMatch, disabled }: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const detected = url.trim() ? detectPlatform(url.trim()) : null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    if (!detected) {
      setError("Ungültige URL. Unterstützt: YouTube, SoundCloud, Spotify.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await identifyUrl(trimmed);
      onMatch(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Identifikation fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="url"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setError(null);
            }}
            placeholder="YouTube, SoundCloud oder Spotify URL..."
            className="glass w-full rounded-xl border border-border-glass px-4 py-3 text-sm text-text-primary placeholder-text-tertiary outline-none transition focus:border-amber/50 focus:ring-1 focus:ring-amber/30"
            disabled={disabled || loading}
            data-testid="url-input"
          />
          {/* Platform badge */}
          {detected && (
            <span
              className={`absolute right-3 top-1/2 -translate-y-1/2 rounded px-1.5 py-0.5 text-xs font-medium ${platformLabels[detected].bg} ${platformLabels[detected].color}`}
              data-testid="platform-badge"
            >
              {platformLabels[detected].name}
            </span>
          )}
        </div>
        <button
          type="submit"
          disabled={!url.trim() || loading || disabled}
          className="rounded-xl bg-amber/20 px-5 py-3 text-sm font-medium text-amber-light transition-colors hover:bg-amber/30 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid="url-submit"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 animate-spin text-amber" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
              </svg>
              Suche...
            </span>
          ) : (
            "Suchen"
          )}
        </button>
      </div>
      {error && (
        <p className="text-xs text-red-400" data-testid="url-error">{error}</p>
      )}
    </form>
  );
}
