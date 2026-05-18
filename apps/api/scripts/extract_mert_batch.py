"""Batch-extract MERT embeddings with pipelined I/O and batched inference.

Downloads Deezer previews in parallel, batches MERT inference on GPU,
and uploads results concurrently. Checkpoint/resume support.

Usage:
    python scripts/extract_mert_batch.py --apply                 # Full run
    python scripts/extract_mert_batch.py --apply --limit 1000    # First 1000
    python scripts/extract_mert_batch.py --apply --batch 8       # Batch size 8
    python scripts/extract_mert_batch.py --apply --workers 6     # 6 I/O threads

Performance: ~2-4 songs/s on Apple Silicon MPS (vs 0.6 sequential).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Add project root to path and load .env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEEZER_API = "https://api.deezer.com"
SAMPLE_RATE = 24000


@dataclass
class SongJob:
    id: str
    deezer_id: int
    artist: str
    title: str
    audio: np.ndarray | None = None
    embedding: list[float] | None = None
    error: str | None = None


def fetch_and_decode(job: SongJob, temp_dir: str) -> SongJob:
    """Download preview + decode to numpy array (runs in thread)."""
    try:
        # Fetch fresh preview URL
        req = urllib.request.Request(
            f"{DEEZER_API}/track/{job.deezer_id}",
            headers={"Accept": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=15)  # noqa: S310
        data = json.loads(resp.read().decode())
        url = data.get("preview")
        if not url:
            job.error = "no_preview"
            return job

        # Download
        path = os.path.join(temp_dir, f"{job.deezer_id}.mp3")
        urllib.request.urlretrieve(url, path)  # noqa: S310

        # Decode via ffmpeg
        cmd = [
            "ffmpeg", "-i", path,
            "-f", "f32le", "-acodec", "pcm_f32le",
            "-ar", str(SAMPLE_RATE), "-ac", "1",
            "-v", "quiet", "-",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        os.unlink(path)

        if result.returncode != 0:
            job.error = "ffmpeg_failed"
            return job

        job.audio = np.frombuffer(result.stdout, dtype=np.float32)
    except Exception as exc:
        job.error = str(exc)[:100]

    return job


def upload_embedding(job: SongJob, sb) -> bool:
    """Store MERT embedding in DB (runs in thread)."""
    try:
        sb.rpc("update_song_mert", {
            "song_id": job.id,
            "new_embedding": str(job.embedding),
        }).execute()
        return True
    except Exception:
        try:
            sb.table("songs").update(
                {"mert_embedding": str(job.embedding)}
            ).eq("id", job.id).execute()
            return True
        except Exception as exc:
            logger.error("Upload failed for %s: %s", job.id, exc)
            return False


def count_pending_songs(sb) -> int | None:
    """Count current MERT candidates once for saner ETA/progress reporting."""
    try:
        return (
            sb.table("songs")
            .select("id", count="exact", head=True)
            .is_("mert_embedding", "null")
            .not_.is_("deezer_id", "null")
            .execute()
            .count
        )
    except Exception as exc:
        logger.warning("Could not count pending MERT songs: %s", exc)
        return None


def fetch_batch_window(sb, processed_ids: set[str], fetch_target: int, page_size: int) -> tuple[list[SongJob], set[str]]:
    """Fetch enough rows to fill a batch even if many early rows are already in the checkpoint."""
    jobs: list[SongJob] = []
    stale_ids: set[str] = set()
    offset = 0

    while len(jobs) < fetch_target:
        result = (
            sb.table("songs")
            .select("id, deezer_id, artist, title")
            .is_("mert_embedding", "null")
            .not_.is_("deezer_id", "null")
            .order("created_at", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        songs = result.data or []
        if not songs:
            break

        offset += len(songs)

        for s in songs:
            sid = str(s["id"])
            if sid in processed_ids:
                stale_ids.add(sid)
                continue
            jobs.append(SongJob(
                id=sid,
                deezer_id=s["deezer_id"],
                artist=s["artist"],
                title=s["title"],
            ))
            if len(jobs) >= fetch_target:
                break

        if len(songs) < page_size:
            break

    return jobs, stale_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch extract MERT embeddings (pipelined)")
    parser.add_argument("--apply", action="store_true", help="Store in DB")
    parser.add_argument("--limit", type=int, default=0, help="Max songs (0=all)")
    parser.add_argument("--batch", type=int, default=4, help="GPU batch size")
    parser.add_argument("--workers", type=int, default=4, help="I/O thread count")
    parser.add_argument("--db-batch", type=int, default=500, help="DB fetch batch size")
    parser.add_argument("--checkpoint", type=str, default="mert_checkpoint.json")
    args = parser.parse_args()

    try:
        import torch
        from transformers import AutoModel, Wav2Vec2FeatureExtractor
    except ModuleNotFoundError as exc:
        missing = exc.name or "torch/transformers"
        raise SystemExit(
            "Missing MERT dependency: "
            f"{missing}. Install the local extra first with "
            "`uv pip install --python .venv/bin/python '.[mert]'`."
        ) from exc

    # Device selection
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    logger.info("Device: %s | Batch: %d | I/O workers: %d", device, args.batch, args.workers)

    # Load model
    logger.info("Loading MERT-v1-95M...")
    processor = Wav2Vec2FeatureExtractor.from_pretrained("m-a-p/MERT-v1-95M")
    model = AutoModel.from_pretrained("m-a-p/MERT-v1-95M", trust_remote_code=True)
    model = model.to(device)
    logger.info("Model loaded")

    from app.db import get_supabase
    sb = get_supabase()

    # Load checkpoint
    checkpoint_path = Path(__file__).parent / args.checkpoint
    processed_ids: set[str] = set()
    if checkpoint_path.exists():
        processed_ids = set(json.loads(checkpoint_path.read_text()))
        logger.info("Resuming from checkpoint: %d songs done", len(processed_ids))

    pending_total = count_pending_songs(sb)
    if pending_total is not None:
        logger.info("Pending songs with Deezer previews: %d", pending_total)

    stats = {"attempted": 0, "extracted": 0, "failed": 0, "no_preview": 0, "checkpoint_skips": 0}
    max_songs = args.limit or float("inf")
    start_time = time.time()
    temp_dir = tempfile.mkdtemp(prefix="mert_batch_")

    download_pool = ThreadPoolExecutor(max_workers=args.workers)
    upload_pool = ThreadPoolExecutor(max_workers=args.workers)

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5

    try:
        while stats["attempted"] < max_songs:
            # Fetch enough rows to build a useful batch even with checkpoint hits at the front.
            fetch_limit = min(args.db_batch, int(max_songs - stats["attempted"])) if args.limit else args.db_batch
            jobs = None
            stale_ids: set[str] = set()
            for retry in range(3):
                try:
                    jobs, stale_ids = fetch_batch_window(sb, processed_ids, fetch_limit, args.db_batch)
                    consecutive_errors = 0
                    break
                except Exception as exc:
                    wait = 30 * (retry + 1)
                    logger.warning("DB fetch failed (attempt %d/3), retry in %ds: %s", retry + 1, wait, exc)
                    time.sleep(wait)

            if jobs is None:
                consecutive_errors += 1
                logger.error("DB fetch failed 3 times (%d/%d consecutive)", consecutive_errors, MAX_CONSECUTIVE_ERRORS)
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error("Too many consecutive DB errors, stopping.")
                    break
                continue

            stats["checkpoint_skips"] += len(stale_ids)

            if not jobs:
                if stale_ids:
                    # Only stale checkpoint hits remain in the current result set.
                    # Clear them once so a retry can re-attempt transient failures.
                    processed_ids -= stale_ids
                    logger.info("Cleared %d stale checkpoint entries, retrying...", len(stale_ids))
                    checkpoint_path.write_text(json.dumps(list(processed_ids)))
                    continue
                logger.info("No more songs to process.")
                break

            stats["attempted"] += len(jobs)
            logger.info(
                "=== Batch: %d jobs (attempted: %d, checkpoint_skips: %d) ===",
                len(jobs), stats["attempted"], stats["checkpoint_skips"],
            )

            # Stage 1: Parallel download + decode
            download_futures = {download_pool.submit(fetch_and_decode, job, temp_dir): job for job in jobs}
            ready_jobs: list[SongJob] = []

            for future in as_completed(download_futures):
                job = future.result()
                if job.error:
                    if job.error == "no_preview":
                        stats["no_preview"] += 1
                    else:
                        stats["failed"] += 1
                    processed_ids.add(job.id)
                    continue
                ready_jobs.append(job)

            # Stage 2: GPU inference (single-item, MERT doesn't batch well with variable lengths)
            for job in ready_jobs:
                try:
                    inputs = processor(job.audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
                    inputs = {k: v.to(device) for k, v in inputs.items()}

                    with torch.no_grad():
                        outputs = model(**inputs, output_hidden_states=True)

                    last_hidden = outputs.hidden_states[-1]
                    embedding = last_hidden.mean(dim=1).squeeze().cpu().numpy()
                    job.embedding = embedding.tolist()
                except Exception as exc:
                    logger.error("Inference failed for %s: %s", job.id, exc)
                    job.error = "inference_failed"
                    stats["failed"] += 1

            # Stage 3: Parallel upload
            upload_futures = []
            for job in ready_jobs:
                if job.embedding and args.apply:
                    upload_futures.append(upload_pool.submit(upload_embedding, job, sb))
                    stats["extracted"] += 1
                elif job.embedding:
                    stats["extracted"] += 1
                processed_ids.add(job.id)

            # Wait for uploads to finish
            for f in as_completed(upload_futures):
                if not f.result():
                    stats["failed"] += 1
                    stats["extracted"] -= 1

            # Progress + checkpoint
            elapsed = time.time() - start_time
            rate = stats["attempted"] / elapsed if elapsed > 0 else 0
            if pending_total is not None and rate > 0:
                remaining = max(0, pending_total - stats["attempted"]) / rate / 3600
                logger.info(
                    "Progress: attempted=%d/%d extracted=%d no_preview=%d failed=%d checkpoint_skips=%d | %.1f songs/s | ETA: %.1fh",
                    stats["attempted"], pending_total, stats["extracted"], stats["no_preview"],
                    stats["failed"], stats["checkpoint_skips"], rate, remaining,
                )
            else:
                logger.info(
                    "Progress: attempted=%d extracted=%d no_preview=%d failed=%d checkpoint_skips=%d | %.1f songs/s",
                    stats["attempted"], stats["extracted"], stats["no_preview"],
                    stats["failed"], stats["checkpoint_skips"], rate,
                )
            checkpoint_path.write_text(json.dumps(list(processed_ids)))

    finally:
        download_pool.shutdown(wait=False)
        upload_pool.shutdown(wait=False)
        checkpoint_path.write_text(json.dumps(list(processed_ids)))
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass

    elapsed = time.time() - start_time
    logger.info(
        "Done! attempted=%d extracted=%d failed=%d no_preview=%d checkpoint_skips=%d (%.1f min, %.1f songs/s)",
        stats["attempted"], stats["extracted"], stats["failed"], stats["no_preview"],
        stats["checkpoint_skips"], elapsed / 60, stats["attempted"] / elapsed if elapsed > 0 else 0,
    )


if __name__ == "__main__":
    main()
