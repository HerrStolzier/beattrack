"""Read-only, bounded capture; run in an already configured API environment.

Usage: python capture.py UUID [UUID ...] > snapshot.json
Only SELECT and the existing read-only similarity RPC are used. No ingestion.
"""
import hashlib
import json
import argparse
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
from uuid import UUID

from app.db import get_supabase


def preview_seed(track_id):
    """Analyze one official preview in a temporary directory, never ingest it."""
    from app.services.features import extract_features_safe
    with urllib.request.urlopen(f"https://api.deezer.com/track/{track_id}", timeout=20) as response:
        track = json.load(response)
    if track.get("id") != track_id:
        raise ValueError("Deezer returned a different recording")
    preview = track.get("preview", "")
    parsed = urlparse(preview)
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".dzcdn.net"):
        raise ValueError("No official HTTPS preview available")
    with tempfile.TemporaryDirectory(prefix="beattrack_listening_") as directory:
        path = Path(directory) / "preview.mp3"
        with urllib.request.urlopen(preview, timeout=20) as response:
            audio = response.read(5_000_001)
        if len(audio) > 5_000_000:
            raise ValueError("Preview exceeds experiment size limit")
        path.write_bytes(audio)
        audio_hash = hashlib.sha256(audio).hexdigest()
        features = extract_features_safe(str(path), timeout=120)
    return {"id": f"deezer:{track_id}", "deezer_id": track_id,
            "title": track["title"], "artist": track["artist"]["name"],
            "album": track.get("album", {}).get("title"),
            "learned_embedding": features["learned"],
            "handcrafted_raw": features["handcrafted"],
            "handcrafted_norm": None, "mert_embedding": None,
            "preview_sha256": audio_hash, "analysis_duration": features.get("duration"),
            "catalogue_member": False}


def capture(song_ids, allow_preview=False):
    if not 1 <= len(song_ids) <= 10 or len(set(song_ids)) != len(song_ids):
        raise ValueError("Supply 1–10 distinct song UUIDs")
    for song_id in song_ids:
        if song_id.startswith("deezer:"):
            if not allow_preview or not song_id[7:].isdigit():
                raise ValueError("Preview analysis requires explicit --allow-preview-analysis")
        else:
            UUID(song_id)
    sb = get_supabase()
    fields = "id,title,artist,album,deezer_id,learned_embedding,handcrafted_raw,handcrafted_norm,mert_embedding,genre"
    cases = []
    for song_id in song_ids:
        external = song_id.startswith("deezer:")
        seed = (preview_seed(int(song_id[7:])) if external else
                sb.table("songs").select(fields).eq("id", song_id).single().execute().data)
        if not seed or not seed.get("learned_embedding"):
            raise ValueError("Reference has no learned embedding")
        params = {
            "query_embedding": str(seed["learned_embedding"]),
            "match_count": 30,
        }
        if not external:
            params["exclude_id"] = song_id
        candidates = sb.rpc("find_similar_songs", params).execute().data or []
        ids = [str(row["id"]) for row in candidates]
        vectors = sb.table("songs").select(fields).in_("id", ids).execute().data if ids else []
        cases.append({"seed": seed, "candidates": candidates, "vectors": vectors})
    stats = sb.table("config").select("key,value").in_(
        "key", ["normalization_stats", "handcrafted_norm_stats"],
    ).execute().data
    stats_hash = hashlib.sha256(json.dumps(stats, sort_keys=True).encode()).hexdigest()
    return {"schema": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "configured PostgREST catalogue", "stats_sha256": stats_hash,
            "normalization_configs": stats, "candidate_count": 30, "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song_ids", nargs="+")
    parser.add_argument("--allow-preview-analysis", action="store_true")
    args = parser.parse_args()
    print(json.dumps(capture(args.song_ids, args.allow_preview_analysis), allow_nan=False))
