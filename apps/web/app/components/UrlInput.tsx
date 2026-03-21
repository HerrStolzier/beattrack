"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { identifyUrl, detectPlatform, type IdentifyResponse } from "@/lib/api";

type UrlInputProps = {
  onMatch: (result: IdentifyResponse) => void;
  disabled?: boolean;
};

const platformLabels: Record<
  string,
  { name: string; color: string; bg: string; brandColor: string }
> = {
  youtube: {
    name: "YouTube",
    color: "text-red-400",
    bg: "bg-red-500/20",
    brandColor: "#FF0000",
  },
  soundcloud: {
    name: "SoundCloud",
    color: "text-orange-400",
    bg: "bg-orange-500/20",
    brandColor: "#FF5500",
  },
  spotify: {
    name: "Spotify",
    color: "text-emerald-400",
    bg: "bg-emerald-500/20",
    brandColor: "#1DB954",
  },
  apple_music: {
    name: "Apple Music",
    color: "text-pink-400",
    bg: "bg-pink-500/20",
    brandColor: "#FC3C44",
  },
  deezer: {
    name: "Deezer",
    color: "text-purple-400",
    bg: "bg-purple-500/20",
    brandColor: "#A238FF",
  },
};

export default function UrlInput({ onMatch, disabled }: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  const detected = url.trim() ? detectPlatform(url.trim()) : null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    if (!detected) {
      setError("Bitte eine YouTube, SoundCloud, Spotify, Apple Music oder Deezer URL eingeben.");
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
        {/* Animated input container */}
        <motion.div
          className="relative flex-1 rounded-xl"
          animate={
            isFocused
              ? {
                  boxShadow: "0 0 20px rgba(245, 158, 11, 0.12), 0 0 40px rgba(245, 158, 11, 0.04)",
                }
              : {
                  boxShadow: "0 0 0px rgba(245, 158, 11, 0)",
                }
          }
          transition={{ duration: 0.3 }}
          whileHover={
            !isFocused && !disabled
              ? { boxShadow: "0 0 10px rgba(245, 158, 11, 0.08), 0 0 0 1px rgba(255,255,255,0.18)" }
              : {}
          }
        >
          <input
            type="url"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setError(null);
            }}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="YouTube, SoundCloud, Spotify, Apple Music oder Deezer URL..."
            className="glass w-full rounded-xl border border-border-glass px-4 py-3 text-sm text-text-primary placeholder-text-tertiary outline-none transition-colors duration-300 focus:border-amber/30"
            disabled={disabled || loading}
            data-testid="url-input"
          />
          {/* Platform badge with brand color */}
          {detected && (
            <span
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded px-1.5 py-0.5 text-xs font-medium transition-transform duration-200 hover:-translate-y-[calc(50%+2px)]"
              style={{
                backgroundColor: `${platformLabels[detected].brandColor}22`,
                color: platformLabels[detected].brandColor,
                border: `1px solid ${platformLabels[detected].brandColor}44`,
              }}
              data-testid="platform-badge"
            >
              {platformLabels[detected].name}
            </span>
          )}
        </motion.div>

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
                <path
                  d="M4 12a8 8 0 018-8"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  className="opacity-75"
                />
              </svg>
              Suche...
            </span>
          ) : (
            "Suchen"
          )}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-400" data-testid="url-error">
          {error}
        </p>
      )}

      {/* Supported platforms */}
      <div className="flex items-center gap-2 pt-1">
        <span className="text-xs text-text-tertiary">Unterstützt:</span>
        {(["youtube", "soundcloud", "spotify", "apple_music", "deezer"] as const).map((p) => {
          const isActive = detected === p;
          return (
            <motion.span
              key={p}
              className="inline-flex cursor-default items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium"
              style={
                isActive
                  ? {
                      backgroundColor: `${platformLabels[p].brandColor}22`,
                      color: platformLabels[p].brandColor,
                      border: `1px solid ${platformLabels[p].brandColor}44`,
                    }
                  : {
                      backgroundColor: "rgba(255,255,255,0.05)",
                      color: "var(--color-text-tertiary)",
                      border: "1px solid transparent",
                    }
              }
              whileHover={{
                y: -2,
                backgroundColor: isActive
                  ? `${platformLabels[p].brandColor}33`
                  : "rgba(255,255,255,0.1)",
                color: isActive ? platformLabels[p].brandColor : "var(--color-text-secondary)",
              }}
              transition={{ duration: 0.15 }}
            >
              {p === "youtube" && (
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31.4 31.4 0 0 0 0 12a31.4 31.4 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8ZM9.5 15.6V8.4l6.3 3.6-6.3 3.6Z" />
                </svg>
              )}
              {p === "soundcloud" && (
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M1.2 14.3a.2.2 0 0 0-.2.2v3a.2.2 0 0 0 .4 0v-3a.2.2 0 0 0-.2-.2Zm1.5-1.2a.2.2 0 0 0-.2.2v4.4a.2.2 0 0 0 .4 0v-4.4a.2.2 0 0 0-.2-.2Zm1.5-1a.2.2 0 0 0-.2.2v5.4a.2.2 0 0 0 .4 0v-5.4a.2.2 0 0 0-.2-.2Zm1.5-.5a.2.2 0 0 0-.2.2v6.4a.2.2 0 0 0 .4 0V12a.2.2 0 0 0-.2-.2v-.2Zm1.5-1.5a.2.2 0 0 0-.2.2v8.4a.2.2 0 0 0 .4 0V10.5a.2.2 0 0 0-.2-.2v-.2Zm1.5-.4a.2.2 0 0 0-.2.2v8.8a.2.2 0 0 0 .4 0V10a.2.2 0 0 0-.2-.2v-.1Zm1.5-1.3a.2.2 0 0 0-.2.2v10.2a.2.2 0 0 0 .4 0V8.8a.2.2 0 0 0-.2-.2v-.2Zm1.5-.6a.2.2 0 0 0-.2.2v10.8a.2.2 0 0 0 .4 0V8.2a.2.2 0 0 0-.2-.2Zm3 .3c-.6 0-1.1.1-1.6.4A5.4 5.4 0 0 0 13 8c-.1 0-.2.1-.2.2v10.5a.2.2 0 0 0 .2.2h5.2a3.1 3.1 0 0 0 0-6.2Z" />
                </svg>
              )}
              {p === "spotify" && (
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0a12 12 0 1 0 0 24 12 12 0 0 0 0-24Zm5.5 17.3a.7.7 0 0 1-1 .3c-2.8-1.7-6.3-2.1-10.4-1.1a.7.7 0 1 1-.4-1.4c4.5-1 8.4-.6 11.5 1.3a.7.7 0 0 1 .3 1Zm1.5-3.3a.9.9 0 0 1-1.3.3c-3.2-2-8.1-2.5-11.8-1.4a.9.9 0 1 1-.5-1.8c4.3-1.3 9.6-.7 13.3 1.6a.9.9 0 0 1 .3 1.3Zm.1-3.4C15.5 8.4 9 8.2 5.3 9.3a1.1 1.1 0 1 1-.6-2.1C9 5.9 16.2 6.1 20.4 8.7a1.1 1.1 0 0 1-1.3 1.9Z" />
                </svg>
              )}
              {p === "apple_music" && (
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.994 6.124a9.23 9.23 0 0 0-.24-2.19c-.317-1.31-1.062-2.31-2.18-3.043a5.022 5.022 0 0 0-1.877-.726 10.496 10.496 0 0 0-1.564-.15c-.073-.004-.148-.01-.224-.013H6.09c-.076.003-.152.01-.228.013-.487.04-.98.112-1.46.258C3.25.633 2.37 1.29 1.717 2.31A5.006 5.006 0 0 0 .972 3.89a9.334 9.334 0 0 0-.218 1.768c-.004.078-.01.15-.014.224V18.12c.004.074.01.148.014.224.035.498.103.99.246 1.47.318 1.07.893 1.95 1.76 2.63.482.378 1.024.66 1.616.826.44.124.89.19 1.347.224.238.02.478.03.716.03h11.15c.238 0 .476-.01.712-.03.484-.035.958-.112 1.422-.27.944-.322 1.72-.89 2.31-1.69.358-.48.62-1.014.79-1.592.124-.44.19-.89.223-1.345.017-.23.028-.462.03-.694V6.124Zm-6.29 5.01c-.006 3.442-.007 6.884.004 10.326 0 .356-.045.704-.18 1.033-.232.564-.637.893-1.228 1.023-.263.058-.53.088-.8.098-.426.016-.855.005-1.264-.12-.626-.19-1.02-.59-1.148-1.236-.108-.54-.033-1.06.26-1.52.333-.524.828-.813 1.416-.947.326-.074.66-.11.994-.136.388-.03.777-.046 1.156-.122.275-.054.465-.2.56-.47.058-.164.08-.338.08-.514V8.676c0-.12-.023-.237-.08-.347-.086-.166-.222-.26-.403-.288-.125-.02-.252-.022-.378-.004-.252.036-.503.084-.753.132l-4.14.814c-.357.07-.712.146-1.067.222-.168.036-.302.123-.385.282-.055.105-.082.22-.085.34-.01.33-.005.66-.005.99v7.5c.003.392-.003.785.005 1.177.008.404-.037.8-.186 1.178-.225.572-.636.904-1.228 1.04-.264.06-.532.093-.803.103-.425.015-.855.01-1.264-.113-.633-.188-1.034-.59-1.163-1.242-.1-.497-.045-.98.198-1.43.31-.575.827-.878 1.44-1.02.32-.074.647-.112.975-.136.392-.028.785-.044 1.168-.122.296-.06.494-.218.586-.512.046-.145.063-.3.063-.455V7.298c0-.254.055-.49.228-.687.14-.16.317-.252.516-.3.146-.035.294-.063.442-.09l5.346-1.057c.39-.076.78-.157 1.172-.228.23-.042.463-.058.696-.016.353.064.587.275.656.633.027.14.036.285.036.428.001 1.72 0 3.44-.002 5.16Z" />
                </svg>
              )}
              {p === "deezer" && (
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.81 4.16v3.03H24V4.16h-5.19zM6.27 8.38v3.027h5.19V8.38H6.27zm12.54 0v3.027H24V8.38h-5.19zM6.27 12.594v3.027h5.19v-3.027H6.27zm6.27 0v3.027h5.19v-3.027h-5.19zm6.27 0v3.027H24v-3.027h-5.19zM0 16.81v3.029h5.19v-3.03H0zm6.27 0v3.029h5.19v-3.03H6.27zm6.27 0v3.029h5.19v-3.03h-5.19zm6.27 0v3.029H24v-3.03h-5.19z" />
                </svg>
              )}
              {platformLabels[p].name}
            </motion.span>
          );
        })}
      </div>
    </form>
  );
}
