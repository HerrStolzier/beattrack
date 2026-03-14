const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Song = {
  id: string;
  title: string;
  artist: string;
  album: string | null;
  bpm: number | null;
  musical_key: string | null;
  duration_sec: number | null;
};

export type SimilarSong = Song & { similarity: number };

export async function searchSongs(q: string, limit?: number): Promise<Song[]> {
  const params = new URLSearchParams({ q });
  if (limit !== undefined) params.set("limit", String(limit));
  const res = await fetch(`${API_URL}/songs?${params}`);
  if (!res.ok) throw new Error(`searchSongs failed: ${res.status}`);
  return res.json();
}

export async function getSong(id: string): Promise<Song> {
  const res = await fetch(`${API_URL}/songs/${id}`);
  if (!res.ok) throw new Error(`getSong failed: ${res.status}`);
  return res.json();
}

export async function findSimilar(
  songId: string,
  opts?: { limit?: number; minBpm?: number; maxBpm?: number }
): Promise<SimilarSong[]> {
  const body: Record<string, unknown> = { song_id: songId };
  if (opts?.limit !== undefined) body.limit = opts.limit;
  if (opts?.minBpm !== undefined) body.min_bpm = opts.minBpm;
  if (opts?.maxBpm !== undefined) body.max_bpm = opts.maxBpm;
  const res = await fetch(`${API_URL}/similar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`findSimilar failed: ${res.status}`);
  return res.json();
}

export async function submitFeedback(
  querySongId: string,
  resultSongId: string,
  rating: 1 | -1
): Promise<void> {
  const res = await fetch(`${API_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query_song_id: querySongId,
      result_song_id: resultSongId,
      rating,
    }),
  });
  if (!res.ok) throw new Error(`submitFeedback failed: ${res.status}`);
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
  const res = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: `Upload failed: ${res.status}` }));
    throw new Error(detail.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function getJobResults(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_URL}/analyze/${jobId}/results`);
  if (!res.ok) throw new Error(`getJobResults failed: ${res.status}`);
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

    es.addEventListener("error", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        onError(new Error(data.detail || "SSE error"));
      } catch {
        // Connection error — retry
      }
      es?.close();
      if (!closed && retries < maxRetries) {
        retries++;
        setTimeout(connect, 1000 * Math.min(retries, 5));
      } else if (!closed) {
        onError(new Error("Connection lost. Retries exhausted."));
        closed = true;
      }
    });

    es.onerror = () => {
      es?.close();
      if (!closed && retries < maxRetries) {
        retries++;
        setTimeout(connect, 1000 * Math.min(retries, 5));
      } else if (!closed) {
        onError(new Error("Connection lost. Retries exhausted."));
        closed = true;
      }
    };
  }

  connect();

  return () => {
    closed = true;
    es?.close();
  };
}

// ---------------------------------------------------------------------------
// YouTube Identify
// ---------------------------------------------------------------------------

export type IdentifyResponse = {
  matched: boolean;
  song: Song | null;
  parsed_artist: string | null;
  parsed_title: string | null;
  message: string;
};

export async function identifyYouTube(url: string): Promise<IdentifyResponse> {
  const res = await fetch(`${API_URL}/identify/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: `Identify failed: ${res.status}` }));
    throw new Error(detail.detail || `Identify failed: ${res.status}`);
  }
  return res.json();
}
