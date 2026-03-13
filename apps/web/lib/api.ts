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
  const res = await fetch(`${API_URL}/songs/search?${params}`);
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
  const params = new URLSearchParams();
  if (opts?.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts?.minBpm !== undefined) params.set("min_bpm", String(opts.minBpm));
  if (opts?.maxBpm !== undefined) params.set("max_bpm", String(opts.maxBpm));
  const query = params.toString() ? `?${params}` : "";
  const res = await fetch(`${API_URL}/songs/${songId}/similar${query}`);
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
