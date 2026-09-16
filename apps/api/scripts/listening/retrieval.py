"""Offline benchmark for independent embedding retrieval.

Input schema (JSON):

``manifest.json``::

    {
      "recordings": [{
        "id": "track-id", "recording_family": "original-or-version-family",
        "recording_identity": "exact-audio-work", "artist_group": "artist-or-group",
        "split": "dev|test", "audio_sha256": "64 lowercase hex",
        "start_seconds": 0.0, "duration_seconds": 10.0,
        "source_evidence": {
          "declaration": "who/what permits this use",
          "analysis": true, "storage": true, "listening": true
        }
      }],
      "queries": [{"id": "query-name", "recording_id": "track-id",
                   "split": "dev|test", "positives": ["other-track-id"]}]
    }

``embeddings.json`` (one per model)::

    {"model": "stable-name", "revision": "immutable revision",
     "preprocessing": {"audio": "description", "pooling": "description"},
     "audio_segments": {"track-id": {"audio_sha256": "64 lowercase hex",
       "start_seconds": 0.0, "duration_seconds": 10.0}},
     "vectors": {"track-id": [0.1, 0.2]}}

Run ``python retrieval.py MANIFEST --embeddings baseline=BASELINE.json
--embeddings challenger=CHALLENGER.json --output report.json``. The aliases must
be unique. Every model independently ranks every eligible recording in the
query's split with exact cosine similarity. The benchmark has no preselection,
fusion, filters, MMR, network or audio access. Source evidence is a recorded
declaration for auditability, not legal verification. Output contains complete
rankings, optional positive ranks, coverage, metadata and SHA-256 input
fingerprints. Equal scores are ordered by recording ID for reproducibility.
The audio manifest fingerprint is SHA-256 over compact, key-sorted JSON mapping
each recording ID to ``audio_sha256``, ``start_seconds`` and
``duration_seconds``. It proves all model inputs declare the same audio bytes
and time ranges without exposing local paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _fingerprint(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_report(path: Path, report: dict[str, Any]) -> None:
    """Create a report without replacing an existing experiment artifact."""
    with path.open("x") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")


def audio_manifest_sha256(recordings: list[dict[str, Any]]) -> str:
    """Fingerprint the canonical recording-to-audio-segment mapping."""
    mapping = {row["id"]: {key: row[key] for key in ("audio_sha256", "start_seconds", "duration_seconds")}
               for row in recordings}
    raw = json.dumps(mapping, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return _fingerprint(raw)


def _validate_manifest(data: Any) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("recordings"), list)
        or not isinstance(data.get("queries"), list)
    ):
        raise ValueError("manifest must contain recordings and queries lists")
    recordings: dict[str, dict[str, Any]] = {}
    owners: dict[tuple[str, str], str] = {}
    for index, row in enumerate(data["recordings"]):
        if not isinstance(row, dict):
            raise ValueError(f"recordings[{index}] must be an object")
        rid = _require_text(row.get("id"), f"recordings[{index}].id")
        if rid in recordings:
            raise ValueError(f"duplicate recording id: {rid}")
        split = _require_text(row.get("split"), f"recordings[{index}].split")
        if split not in {"dev", "test"}:
            raise ValueError(f"recording {rid} has invalid split: {split}")
        family = _require_text(row.get("recording_family"), f"recording {rid}.recording_family")
        _require_text(row.get("recording_identity"), f"recording {rid}.recording_identity")
        artist = _require_text(row.get("artist_group"), f"recording {rid}.artist_group")
        audio_hash = _require_text(row.get("audio_sha256"), f"recording {rid}.audio_sha256")
        if len(audio_hash) != 64 or any(char not in "0123456789abcdef" for char in audio_hash):
            raise ValueError(f"recording {rid}.audio_sha256 must be 64 lowercase hex characters")
        for field in ("start_seconds", "duration_seconds"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"recording {rid}.{field} must be a finite number")
        if row["start_seconds"] < 0 or row["duration_seconds"] <= 0:
            raise ValueError(f"recording {rid} requires nonnegative start and positive duration")
        evidence = row.get("source_evidence")
        if not isinstance(evidence, dict):
            raise ValueError(f"recording {rid} requires source_evidence")
        _require_text(evidence.get("declaration"), f"recording {rid}.source_evidence.declaration")
        for permission in ("analysis", "storage", "listening"):
            if evidence.get(permission) is not True:
                raise ValueError(f"recording {rid} lacks declared {permission} permission")
        for kind, value in (("recording family", family), ("artist group", artist)):
            key = (kind, value)
            if key in owners and owners[key] != split:
                raise ValueError(f"{kind} {value!r} leaks across dev/test splits")
            owners[key] = split
        recordings[rid] = row

    queries: list[dict[str, Any]] = []
    query_ids: set[str] = set()
    for index, row in enumerate(data["queries"]):
        if not isinstance(row, dict):
            raise ValueError(f"queries[{index}] must be an object")
        qid = _require_text(row.get("id"), f"queries[{index}].id")
        if qid in query_ids:
            raise ValueError(f"duplicate query id: {qid}")
        query_ids.add(qid)
        rid = _require_text(row.get("recording_id"), f"query {qid}.recording_id")
        if rid not in recordings:
            raise ValueError(f"query {qid} references unknown recording {rid}")
        split = _require_text(row.get("split"), f"query {qid}.split")
        if split != recordings[rid]["split"]:
            raise ValueError(f"query {qid} split differs from its recording")
        positives = row.get("positives", [])
        if not isinstance(positives, list) or any(not isinstance(v, str) for v in positives):
            raise ValueError(f"query {qid}.positives must be a string list")
        if len(set(positives)) != len(positives):
            raise ValueError(f"query {qid} has duplicate positives")
        for positive in positives:
            if positive not in recordings or recordings[positive]["split"] != split:
                raise ValueError(f"query {qid} positive {positive} is absent from its split")
            if positive == rid or recordings[positive]["recording_identity"] == recordings[rid]["recording_identity"]:
                raise ValueError(f"query {qid} positive {positive} is the query or same recording")
        queries.append(row)
    if not queries:
        raise ValueError("manifest requires at least one query")
    return recordings, queries


def _validate_embeddings(
    data: Any, required_ids: set[str], alias: str, expected_audio_segments: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[float]], int]:
    if not isinstance(data, dict):
        raise ValueError(f"embedding input {alias} must be an object")
    _require_text(data.get("model"), f"{alias}.model")
    _require_text(data.get("revision"), f"{alias}.revision")
    preprocessing = data.get("preprocessing")
    if not isinstance(preprocessing, dict) or not preprocessing:
        raise ValueError(f"{alias}.preprocessing must be a non-empty object")
    for key, value in preprocessing.items():
        _require_text(key, f"{alias}.preprocessing key")
        _require_text(value, f"{alias}.preprocessing.{key}")
    if data.get("audio_segments") != expected_audio_segments:
        raise ValueError(f"{alias}.audio_segments do not match the corpus audio segments")
    vectors = data.get("vectors")
    if not isinstance(vectors, dict):
        raise ValueError(f"{alias}.vectors must be an object")
    missing = sorted(required_ids - vectors.keys())
    if missing:
        raise ValueError(f"{alias} is missing vectors: {', '.join(missing)}")
    dimension: int | None = None
    valid: dict[str, list[float]] = {}
    for rid in sorted(required_ids):
        vector = vectors[rid]
        if not isinstance(vector, list) or not vector:
            raise ValueError(f"{alias} vector {rid} must have nonzero dimension")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
            raise ValueError(f"{alias} vector {rid} must contain finite numbers")
        numeric = [float(v) for v in vector]
        if dimension is None:
            dimension = len(numeric)
        elif len(numeric) != dimension:
            raise ValueError(f"{alias} vector {rid} has inconsistent dimension")
        norm = math.sqrt(sum(v * v for v in numeric))
        if not math.isfinite(norm) or norm == 0.0:
            raise ValueError(f"{alias} vector {rid} has invalid zero or non-finite norm")
        valid[rid] = [v / norm for v in numeric]
    assert dimension is not None
    return valid, dimension


def benchmark(manifest: Any, models: dict[str, Any], *, fingerprints: dict[str, str]) -> dict[str, Any]:
    recordings, queries = _validate_manifest(manifest)
    if not models:
        raise ValueError("at least one embedding model is required")
    required_ids = set(recordings)
    expected_audio_segments = {
        rid: {key: row[key] for key in ("audio_sha256", "start_seconds", "duration_seconds")}
        for rid, row in recordings.items()
    }
    expected_audio_fingerprint = audio_manifest_sha256(list(recordings.values()))
    validated: dict[str, tuple[dict[str, list[float]], int]] = {}
    for alias, data in models.items():
        _require_text(alias, "model alias")
        validated[alias] = _validate_embeddings(data, required_ids, alias, expected_audio_segments)

    report: dict[str, Any] = {
        "protocol": "independent-exact-cosine-v1",
        "input_fingerprints": fingerprints,
        "audio_manifest_sha256": expected_audio_fingerprint,
        "coverage": {"manifest_recordings": len(recordings), "queries": len(queries), "models": {}},
        "models": {},
        "quality_claim": "None. Rankings and optional positive ranks are descriptive retrieval output only.",
    }
    for alias in sorted(models):
        data = models[alias]
        vectors, dimension = validated[alias]
        query_results = []
        for query in queries:
            query_id = query["recording_id"]
            query_recording = recordings[query_id]
            # Multiple catalog rows may refer to the same exact recording.
            # Pick the lowest ID so one recording cannot occupy several ranks.
            by_identity: dict[str, str] = {}
            for rid, row in recordings.items():
                if (row["split"] == query["split"] and rid != query_id
                        and row["recording_identity"] != query_recording["recording_identity"]):
                    identity = row["recording_identity"]
                    by_identity[identity] = min(rid, by_identity.get(identity, rid))
            eligible = list(by_identity.values())
            if not eligible:
                raise ValueError(f"query {query['id']} has no eligible candidates")
            scored = [(rid, sum(a * b for a, b in zip(vectors[query_id], vectors[rid], strict=True)))
                      for rid in eligible]
            scored.sort(key=lambda item: (-item[1], item[0]))
            rankings = [{"rank": rank, "recording_id": rid, "cosine": score}
                        for rank, (rid, score) in enumerate(scored, 1)]
            rank_by_id = {row["recording_id"]: row["rank"] for row in rankings}
            positives = [{"recording_id": rid, "rank": rank_by_id[rid]}
                         for rid in query.get("positives", [])]
            query_results.append({"query_id": query["id"], "recording_id": query_id,
                                  "split": query["split"], "eligible_candidates": len(eligible),
                                  "rankings": rankings, "positive_ranks": positives})
        report["models"][alias] = {"model": data["model"], "revision": data["revision"],
            "preprocessing": data["preprocessing"], "dimension": dimension, "queries": query_results}
        report["coverage"]["models"][alias] = {
            "vectors_required": len(required_ids), "vectors_present": len(required_ids),
            "queries_ranked": len(query_results),
            "candidate_scores": sum(row["eligible_candidates"] for row in query_results),
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--embeddings", action="append", required=True, metavar="ALIAS=PATH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_raw = args.manifest.read_bytes()
    models: dict[str, Any] = {}
    fingerprints = {"manifest_sha256": _fingerprint(manifest_raw), "embedding_sha256": {}}
    for value in args.embeddings:
        alias, separator, path_text = value.partition("=")
        if not separator or not alias or not path_text or alias in models:
            parser.error("--embeddings must be unique ALIAS=PATH values")
        raw = Path(path_text).read_bytes()
        models[alias] = json.loads(raw)
        fingerprints["embedding_sha256"][alias] = _fingerprint(raw)
    result = benchmark(json.loads(manifest_raw), models, fingerprints=fingerprints)
    _write_report(args.output, result)


if __name__ == "__main__":
    main()
