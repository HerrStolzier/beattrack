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
      {/* Supported platforms */}
      <div className="flex items-center gap-2 pt-1">
        <span className="text-xs text-text-tertiary">Unterstützt:</span>
        {(["youtube", "soundcloud", "spotify"] as const).map((p) => (
          <span
            key={p}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium transition-colors ${
              detected === p
                ? `${platformLabels[p].bg} ${platformLabels[p].color}`
                : "bg-white/5 text-text-tertiary hover:bg-white/10 hover:text-text-secondary"
            }`}
          >
            {p === "youtube" && (
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31.4 31.4 0 0 0 0 12a31.4 31.4 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8ZM9.5 15.6V8.4l6.3 3.6-6.3 3.6Z"/></svg>
            )}
            {p === "soundcloud" && (
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M1.2 14.3a.2.2 0 0 0-.2.2v3a.2.2 0 0 0 .4 0v-3a.2.2 0 0 0-.2-.2Zm1.5-1.2a.2.2 0 0 0-.2.2v4.4a.2.2 0 0 0 .4 0v-4.4a.2.2 0 0 0-.2-.2Zm1.5-1a.2.2 0 0 0-.2.2v5.4a.2.2 0 0 0 .4 0v-5.4a.2.2 0 0 0-.2-.2Zm1.5-.5a.2.2 0 0 0-.2.2v6.4a.2.2 0 0 0 .4 0V12a.2.2 0 0 0-.2-.2v-.2Zm1.5-1.5a.2.2 0 0 0-.2.2v8.4a.2.2 0 0 0 .4 0V10.5a.2.2 0 0 0-.2-.2v-.2Zm1.5-.4a.2.2 0 0 0-.2.2v8.8a.2.2 0 0 0 .4 0V10a.2.2 0 0 0-.2-.2v-.1Zm1.5-1.3a.2.2 0 0 0-.2.2v10.2a.2.2 0 0 0 .4 0V8.8a.2.2 0 0 0-.2-.2v-.2Zm1.5-.6a.2.2 0 0 0-.2.2v10.8a.2.2 0 0 0 .4 0V8.2a.2.2 0 0 0-.2-.2Zm3 .3c-.6 0-1.1.1-1.6.4A5.4 5.4 0 0 0 13 8c-.1 0-.2.1-.2.2v10.5a.2.2 0 0 0 .2.2h5.2a3.1 3.1 0 0 0 0-6.2Z"/></svg>
            )}
            {p === "spotify" && (
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0a12 12 0 1 0 0 24 12 12 0 0 0 0-24Zm5.5 17.3a.7.7 0 0 1-1 .3c-2.8-1.7-6.3-2.1-10.4-1.1a.7.7 0 1 1-.4-1.4c4.5-1 8.4-.6 11.5 1.3a.7.7 0 0 1 .3 1Zm1.5-3.3a.9.9 0 0 1-1.3.3c-3.2-2-8.1-2.5-11.8-1.4a.9.9 0 1 1-.5-1.8c4.3-1.3 9.6-.7 13.3 1.6a.9.9 0 0 1 .3 1.3Zm.1-3.4C15.5 8.4 9 8.2 5.3 9.3a1.1 1.1 0 1 1-.6-2.1C9 5.9 16.2 6.1 20.4 8.7a1.1 1.1 0 0 1-1.3 1.9Z"/></svg>
            )}
            {platformLabels[p].name}
          </span>
        ))}
      </div>
    </form>
  );
}
