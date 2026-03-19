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


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch extract MERT embeddings (pipelined)")
    parser.add_argument("--apply", action="store_true", help="Store in DB")
    parser.add_argument("--limit", type=int, default=0, help="Max songs (0=all)")
    parser.add_argument("--batch", type=int, default=4, help="GPU batch size")
    parser.add_argument("--workers", type=int, default=4, help="I/O thread count")
    parser.add_argument("--db-batch", type=int, default=500, help="DB fetch batch size")
    parser.add_argument("--checkpoint", type=str, default="mert_checkpoint.json")
    args = parser.parse_args()

    import torch
    from transformers import AutoModel, Wav2Vec2FeatureExtractor

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

    stats = {"extracted": 0, "failed": 0, "no_preview": 0, "skipped": 0}
    total_processed = 0
    max_songs = args.limit or float("inf")
    start_time = time.time()
    temp_dir = tempfile.mkdtemp(prefix="mert_batch_")

    download_pool = ThreadPoolExecutor(max_workers=args.workers)
    upload_pool = ThreadPoolExecutor(max_workers=args.workers)

    try:
        while total_processed < max_songs:
            # Fetch batch from DB
            fetch_limit = min(args.db_batch, int(max_songs - total_processed)) if args.limit else args.db_batch
            result = (
                sb.table("songs")
                .select("id, deezer_id, artist, title")
                .is_("mert_embedding", "null")
                .not_.is_("deezer_id", "null")
                .order("created_at", desc=False)
                .limit(fetch_limit)
                .execute()
            )
            songs = result.data or []
            if not songs:
                logger.info("No more songs to process.")
                break

            # Filter already processed
            jobs = []
            for s in songs:
                sid = str(s["id"])
                if sid in processed_ids:
                    stats["skipped"] += 1
                    total_processed += 1
                    continue
                jobs.append(SongJob(id=sid, deezer_id=s["deezer_id"],
                                    artist=s["artist"], title=s["title"]))

            if not jobs:
                continue

            logger.info("=== Batch: %d jobs (total: %d) ===", len(jobs), total_processed)

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
                    total_processed += 1
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
                total_processed += 1

            # Wait for uploads to finish
            for f in as_completed(upload_futures):
                if not f.result():
                    stats["failed"] += 1
                    stats["extracted"] -= 1

            # Progress + checkpoint
            elapsed = time.time() - start_time
            rate = total_processed / elapsed if elapsed > 0 else 0
            remaining = (121000 - total_processed) / rate / 3600 if rate > 0 else 0
            logger.info(
                "Progress: %d | extracted=%d failed=%d | %.1f songs/s | ETA: %.1fh",
                total_processed, stats["extracted"], stats["failed"], rate, remaining,
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
        "Done! extracted=%d failed=%d no_preview=%d skipped=%d (%.1f min, %.1f songs/s)",
        stats["extracted"], stats["failed"], stats["no_preview"],
        stats["skipped"], elapsed / 60, total_processed / elapsed if elapsed > 0 else 0,
    )


if __name__ == "__main__":
    main()
