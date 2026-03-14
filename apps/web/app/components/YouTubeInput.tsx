"use client";

import { useCallback, useState } from "react";
import { identifyYouTube, type IdentifyResponse } from "@/lib/api";

type YouTubeInputProps = {
  onMatch: (result: IdentifyResponse) => void;
  disabled?: boolean;
};

const YT_REGEX = /^https?:\/\/(www\.)?(youtube\.com\/(watch|shorts|embed)|youtu\.be\/)/;

export default function YouTubeInput({ onMatch, disabled }: YouTubeInputProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);

      const trimmed = url.trim();
      if (!trimmed) return;

      if (!YT_REGEX.test(trimmed)) {
        setError("Bitte eine gültige YouTube-URL eingeben.");
        return;
      }

      setLoading(true);
      try {
        const result = await identifyYouTube(trimmed);
        onMatch(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Identifikation fehlgeschlagen.");
      } finally {
        setLoading(false);
      }
    },
    [url, onMatch]
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/watch?v=..."
          disabled={disabled || loading}
          className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-blue-500"
          data-testid="youtube-input"
        />
        <button
          type="submit"
          disabled={disabled || loading || !url.trim()}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid="youtube-submit"
        >
          {loading ? (
            <span className="inline-flex items-center gap-1">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
              </svg>
              Suche...
            </span>
          ) : (
            "Identifizieren"
          )}
        </button>
      </div>
      {error && (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
