"""Encode explicit local audio segments for retrieval.py; never download audio/models.

Use benchmark runtime for mert/clap, existing API runtime for musicnn.
Manifest recordings additionally need path, audio_sha256, start_seconds, duration_seconds.
Paths are relative to the manifest. Source declarations must permit processing.
Model weights must already exist locally. Output is created exclusively.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

import numpy as np


def decode(path, start, duration, sr):
    result = subprocess.run([
        "ffmpeg", "-nostdin", "-v", "error", "-ss", str(start), "-i", str(path),
        "-t", str(duration), "-f", "f32le", "-acodec", "pcm_f32le",
        "-ar", str(sr), "-ac", "1", "-",
    ], check=True, capture_output=True, timeout=90)
    audio = np.frombuffer(result.stdout, dtype=np.float32).copy()
    if len(audio) < int(duration * sr) - sr // 20 or not np.isfinite(audio).all():
        raise ValueError("Audio segment truncated or invalid")
    return audio


def encode(manifest, manifest_dir, model_name, weights, revision):
    # Preflight every source before loading expensive weights or decoding audio.
    rows = manifest["recordings"]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Recordings must be nonempty and unique")
    for row in rows:
        evidence = row.get("source_evidence", {})
        if not evidence.get("declaration") or any(
            evidence.get(key) is not True for key in ("analysis", "storage", "listening")
        ):
            raise ValueError("Missing source permission declaration")
        for field in ("start_seconds", "duration_seconds"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Explicit finite segment bounds required")
        if row["start_seconds"] < 0 or not 3 <= row["duration_seconds"] <= 30:
            raise ValueError("Segment start must be nonnegative and duration between 3 and 30 seconds")
        path = manifest_dir / row["path"]
        if not path.is_file():
            raise ValueError("Local audio file missing")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row.get("audio_sha256"):
            raise ValueError("Local audio checksum differs from manifest")

    sr = {"mert": 24000, "clap": 48000, "musicnn": 16000}[model_name]
    before = time.perf_counter()
    if model_name == "musicnn":
        import essentia.standard as es
        model = es.TensorflowPredictMusiCNN(graphFilename=str(weights), output="model/dense/BiasAdd")
        actual_revision = hashlib.sha256(weights.read_bytes()).hexdigest()
        if revision != actual_revision:
            raise ValueError("MusiCNN revision must equal weight SHA256")
    else:
        import torch
        from transformers import AutoModel, ClapFeatureExtractor, ClapModel, Wav2Vec2FeatureExtractor
        if model_name == "mert":
            model = AutoModel.from_pretrained(str(weights), trust_remote_code=True, local_files_only=True).eval()
            processor = Wav2Vec2FeatureExtractor.from_pretrained(str(weights), local_files_only=True)
        else:
            model = ClapModel.from_pretrained(str(weights), local_files_only=True).eval()
            processor = ClapFeatureExtractor.from_pretrained(str(weights), local_files_only=True)
    report = {"model": model_name, "revision": revision,
              "preprocessing": {"sample_rate": str(sr), "channels": "mono", "device": "cpu",
                                "pooling": "mean-last-hidden" if model_name == "mert" else
                                "mean-dense-BiasAdd" if model_name == "musicnn" else "audio-projection",
                                "segment_policy": "explicit manifest bounds; no random cropping"},
              "vectors": {}, "audio_segments": {},
              "measurements": {"load_seconds": time.perf_counter() - before, "recordings": []}}
    for row in rows:
        path = manifest_dir / row["path"]
        before = time.perf_counter()
        audio = decode(path, row["start_seconds"], row["duration_seconds"], sr)
        decode_seconds = time.perf_counter() - before
        before = time.perf_counter()
        if model_name == "musicnn":
            vector = model(audio).mean(axis=0)
        else:
            # CLAP's long-input cropping must be repeatable, not implicitly random.
            np.random.seed(0)
            inputs = processor(audio, sampling_rate=sr, return_tensors="pt")
            with torch.inference_mode():
                output = (model(**inputs).last_hidden_state.mean(dim=1) if model_name == "mert"
                          else model.get_audio_features(**inputs))
            vector = output.squeeze(0).cpu().numpy()
        inference_seconds = time.perf_counter() - before
        if vector.ndim != 1 or not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
            raise ValueError("Invalid model output")
        report["vectors"][row["id"]] = vector.tolist()
        report["audio_segments"][row["id"]] = {
            "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "start_seconds": row["start_seconds"], "duration_seconds": row["duration_seconds"]}
        report["measurements"]["recordings"].append({
            "id": row["id"], "decode_seconds": decode_seconds,
            "inference_seconds": inference_seconds})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--model", required=True, choices=["mert", "clap", "musicnn"])
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    raw = args.manifest.read_bytes()
    report = encode(json.loads(raw), args.manifest.resolve().parent, args.model,
                    args.weights.resolve(), args.revision)
    report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
