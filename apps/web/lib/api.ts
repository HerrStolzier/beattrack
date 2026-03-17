const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Custom error types
// ---------------------------------------------------------------------------

export class NetworkError extends Error {
  constructor(message = "Network error") {
    super(message);
    this.name = "NetworkError";
  }
}

export class TimeoutError extends Error {
  constructor(message = "Request timed out") {
    super(message);
    this.name = "TimeoutError";
  }
}

export class ApiError extends Error {
  constructor(
    public readonly detail: string,
    public readonly status: number
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// fetchWithRetry
// ---------------------------------------------------------------------------

const RETRYABLE_STATUSES = new Set([502, 503, 504]);

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithRetry(
  url: string,
  opts: RequestInit = {},
  config: { retries?: number; backoff?: number; timeout?: number } = {}
): Promise<Response> {
  const { retries = 3, backoff = 1000, timeout = 15000 } = config;

  let lastError: Error = new NetworkError();

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    try {
      const res = await fetch(url, { ...opts, signal: controller.signal });
      clearTimeout(timer);

      if (RETRYABLE_STATUSES.has(res.status) && attempt < retries) {
        lastError = new ApiError(`Server-Fehler (${res.status})`, res.status);
        await delay(backoff * Math.pow(2, attempt));
        continue;
      }

      return res;
    } catch (err) {
      clearTimeout(timer);

      if (err instanceof DOMException && err.name === "AbortError") {
        throw new TimeoutError();
      }

      lastError = new NetworkError();
      if (attempt < retries) {
        await delay(backoff * Math.pow(2, attempt));
        continue;
      }
    }
  }

  throw lastError;
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

export async function pingHealth(): Promise<boolean> {
  try {
    const res = await fetchWithRetry(
      `${API_URL}/health`,
      {},
      { retries: 0, timeout: 10000 }
    );
    if (!res.ok) return false;
    const data = await res.json();
    return data?.status === "ok";
  } catch {
    return false;
  }
}

export type Song = {
  id: string;
  title: string;
  artist: string;
  album: string | null;
  bpm: number | null;
  musical_key: string | null;
  duration_sec: number | null;
  genre: string | null;
  deezer_id: number | null;
};

export type SimilarSong = Song & { similarity: number };

export type RadarFeatures = {
  timbre: number;
  harmony: number;
  rhythm: number;
  brightness: number;
  intensity: number;
};

export async function getSongFeatures(songId: string): Promise<RadarFeatures> {
  const res = await fetchWithRetry(`${API_URL}/songs/${songId}/features`);
  if (!res.ok) throw new ApiError(`getSongFeatures failed`, res.status);
  return res.json();
}

export type BatchFeaturesItem = { song_id: string; features: RadarFeatures };

export async function getBatchFeatures(songIds: string[]): Promise<BatchFeaturesItem[]> {
  const res = await fetchWithRetry(`${API_URL}/songs/features/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ song_ids: songIds }),
  });
  if (!res.ok) throw new ApiError(`getBatchFeatures failed`, res.status);
  return res.json();
}

export async function getSongCount(): Promise<number> {
  const res = await fetchWithRetry(`${API_URL}/songs/count/total`);
  if (!res.ok) throw new ApiError(`getSongCount failed`, res.status);
  const data = await res.json();
  return data.count;
}

export async function searchSongs(
  q: string,
  opts?: { limit?: number; genre?: string; signal?: AbortSignal },
): Promise<Song[]> {
  const params = new URLSearchParams({ q });
  if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts?.genre) params.set("genre", opts.genre);
  const res = await fetchWithRetry(`${API_URL}/songs?${params}`, {
    signal: opts?.signal,
  });
  if (!res.ok) throw new ApiError(`searchSongs failed`, res.status);
  return res.json();
}

export async function getGenres(): Promise<string[]> {
  const res = await fetchWithRetry(`${API_URL}/songs/genres`);
  if (!res.ok) throw new ApiError(`getGenres failed`, res.status);
  return res.json();
}

export async function getSong(id: string): Promise<Song> {
  const res = await fetchWithRetry(`${API_URL}/songs/${id}`);
  if (!res.ok) throw new ApiError(`getSong failed`, res.status);
  return res.json();
}

export type FocusCategory = "timbre" | "harmony" | "rhythm" | "brightness" | "intensity";

export async function findSimilar(
  songId: string,
  opts?: { limit?: number; minBpm?: number; maxBpm?: number; excludeIds?: string[]; focus?: FocusCategory }
): Promise<SimilarSong[]> {
  const body: Record<string, unknown> = { song_id: songId };
  if (opts?.limit !== undefined) body.limit = opts.limit;
  if (opts?.minBpm !== undefined) body.min_bpm = opts.minBpm;
  if (opts?.maxBpm !== undefined) body.max_bpm = opts.maxBpm;
  if (opts?.excludeIds?.length) body.exclude_ids = opts.excludeIds;
  if (opts?.focus) body.focus = opts.focus;
  const res = await fetchWithRetry(`${API_URL}/similar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(`findSimilar failed`, res.status);
  return res.json();
}

export async function findBlend(
  songIdA: string,
  songIdB: string,
  opts?: { limit?: number }
): Promise<SimilarSong[]> {
  const body: Record<string, unknown> = { song_id_a: songIdA, song_id_b: songIdB };
  if (opts?.limit !== undefined) body.limit = opts.limit;
  const res = await fetchWithRetry(`${API_URL}/similar/blend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(`findBlend failed`, res.status);
  return res.json();
}

export async function findVibe(
  songIds: string[],
  opts?: { limit?: number }
): Promise<SimilarSong[]> {
  const body: Record<string, unknown> = { song_ids: songIds };
  if (opts?.limit !== undefined) body.limit = opts.limit;
  const res = await fetchWithRetry(`${API_URL}/similar/vibe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(`findVibe failed`, res.status);
  return res.json();
}

export async function submitFeedback(
  querySongId: string,
  resultSongId: string,
  rating: 1 | -1
): Promise<void> {
  const res = await fetchWithRetry(`${API_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query_song_id: querySongId,
      result_song_id: resultSongId,
      rating,
    }),
  });
  if (!res.ok) throw new ApiError(`submitFeedback failed`, res.status);
}

// ---------------------------------------------------------------------------
// Upload & Analysis
// ---------------------------------------------------------------------------

export type AnalyzeResponse = {
  job_id: string;
  status: string;
};

export type JobStatus = {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  result?: AnalysisResult | null;
  error?: string | null;
};

export type AnalysisResult = {
  song_id: string;
  bpm: number;
  key: string;
  duration: number;
  similar_songs: SimilarSong[];
};

export async function uploadAudio(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetchWithRetry(
    `${API_URL}/analyze`,
    { method: "POST", body: form },
    { retries: 1, timeout: 60000 }
  );
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: undefined }));
    throw new ApiError(data?.detail || `Upload failed`, res.status);
  }
  return res.json();
}

export async function getJobResults(jobId: string): Promise<JobStatus> {
  const res = await fetchWithRetry(`${API_URL}/analyze/${jobId}/results`);
  if (!res.ok) throw new ApiError(`getJobResults failed`, res.status);
  return res.json();
}

export type SSECallback = (event: {
  status: string;
  progress: number;
  result?: AnalysisResult | null;
  error?: string;
}) => void;

export function streamProgress(
  jobId: string,
  onUpdate: SSECallback,
  onError: (err: Error) => void
): () => void {
  const url = `${API_URL}/analyze/${jobId}/stream`;
  let es: EventSource | null = null;
  let closed = false;
  let retries = 0;
  const maxRetries = 5;

  function connect() {
    if (closed) return;
    es = new EventSource(url);

    es.addEventListener("status", (e) => {
      retries = 0;
      try {
        const data = JSON.parse(e.data);
        onUpdate(data);
        if (data.status === "completed" || data.status === "failed") {
          es?.close();
          closed = true;
        }
      } catch {
        // ignore parse errors
      }
    });

    es.addEventListener("heartbeat", () => {
      retries = 0;
    });

    function handleConnectionError() {
      es?.close();
      if (!closed && retries < maxRetries) {
        retries++;
        setTimeout(connect, 1000 * Math.min(retries, 5));
      } else if (!closed) {
        onError(new Error("Connection lost. Retries exhausted."));
        closed = true;
      }
    }

    es.addEventListener("error", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        onError(new Error(data.detail || "SSE error"));
      } catch {
        // Connection error — retry
      }
      handleConnectionError();
    });

    es.onerror = handleConnectionError;
  }

  connect();

  return () => {
    closed = true;
    es?.close();
  };
}

// ---------------------------------------------------------------------------
// URL Identify (YouTube, SoundCloud, Spotify, Apple Music)
// ---------------------------------------------------------------------------

export type IdentifyResponse = {
  matched: boolean;
  song: Song | null;
  parsed_artist: string | null;
  parsed_title: string | null;
  message: string;
  ingesting?: boolean;
};

type Platform = "youtube" | "soundcloud" | "spotify" | "apple_music" | null;

export function detectPlatform(url: string): Platform {
  if (/youtube\.com|youtu\.be/.test(url)) return "youtube";
  if (/soundcloud\.com|on\.soundcloud\.com/.test(url)) return "soundcloud";
  if (/open\.spotify\.com\/track/.test(url)) return "spotify";
  if (/music\.apple\.com\/.+\/(album|song)/.test(url)) return "apple_music";
  return null;
}

async function identifyPlatform(platform: string, url: string): Promise<IdentifyResponse> {
  const res = await fetchWithRetry(`${API_URL}/identify/${platform}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: undefined }));
    throw new ApiError(data?.detail || `Identify failed`, res.status);
  }
  return res.json();
}

export async function identifyUrl(url: string): Promise<IdentifyResponse> {
  const platform = detectPlatform(url);
  if (!platform) {
    throw new ApiError("Ungültige URL. Unterstützt: YouTube, SoundCloud, Spotify, Apple Music.", 400);
  }
  return identifyPlatform(platform, url);
}
