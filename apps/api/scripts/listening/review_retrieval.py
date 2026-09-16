"""Prepare and assess a blinded local review of independent retrieval reports.

Prepare creates a new directory containing only ``index.html``, short local
``clips/*.wav`` files and a private ``key.json``. Source audio paths come from
the manifest and are never copied into the page or served. The manifest must
include title, artist, source_path, attribution and license for each recording,
in addition to the fields required by retrieval.py.

Usage::

    review_retrieval.py prepare manifest.json report.json output-directory
    review_retrieval.py assess output-directory/key.json ratings.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
from pathlib import Path
from typing import Any, Callable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _audio_fingerprint(recordings: list[dict[str, Any]]) -> str:
    mapping = {row["id"]: {key: row[key] for key in ("audio_sha256", "start_seconds", "duration_seconds")}
               for row in recordings}
    raw = json.dumps(mapping, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _ffmpeg_clip(source: Path, start: float, duration: float, output: Path) -> None:
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-ss", str(start), "-t", str(duration),
        "-i", str(source), "-vn", "-c:a", "pcm_s16le", str(output),
    ], check=True, timeout=120)


def _probe_duration(path: Path) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], check=True, capture_output=True, text=True, timeout=30)
    duration = float(result.stdout.strip())
    if not math.isfinite(duration):
        raise ValueError("ffprobe returned a non-finite duration")
    return duration


def prepare(
    manifest: dict[str, Any], report: dict[str, Any], *, manifest_hash: str, report_hash: str,
    output: Path, clipper: Callable[[Path, float, float, Path], None] = _ffmpeg_clip,
    duration_probe: Callable[[Path], float] = _probe_duration,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if report.get("protocol") != "independent-exact-cosine-v1":
        raise ValueError("report is not independent-exact-cosine-v1")
    fingerprints = report.get("input_fingerprints")
    if not isinstance(fingerprints, dict) or fingerprints.get("manifest_sha256") != manifest_hash:
        raise ValueError("report manifest fingerprint does not match the complete manifest")
    recordings_list = manifest.get("recordings")
    if not isinstance(recordings_list, list):
        raise ValueError("manifest recordings must be a list")
    recordings: dict[str, dict[str, Any]] = {}
    for row in recordings_list:
        if not isinstance(row, dict):
            raise ValueError("recording must be an object")
        rid = _text(row.get("id"), "recording.id")
        if rid in recordings:
            raise ValueError(f"duplicate recording id: {rid}")
        for field in ("title", "artist", "source_path", "attribution", "license"):
            _text(row.get(field), f"recording {rid}.{field}")
        _text(row.get("recording_identity"), f"recording {rid}.recording_identity")
        split = _text(row.get("split"), f"recording {rid}.split")
        if split not in {"dev", "test"}:
            raise ValueError(f"recording {rid} has invalid split")
        start = row.get("start_seconds")
        duration = row.get("duration_seconds")
        if (isinstance(start, bool) or not isinstance(start, (int, float)) or not math.isfinite(start)
                or start < 0):
            raise ValueError(f"recording {rid} requires finite nonnegative start_seconds")
        if (isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration)
                or not 3 <= duration <= 30):
            raise ValueError(f"recording {rid} duration_seconds must be finite and between 3 and 30")
        evidence = row.get("source_evidence")
        if not isinstance(evidence, dict) or evidence.get("listening") is not True:
            raise ValueError(f"recording {rid} lacks declared listening permission")
        recordings[rid] = row
    expected_audio = _audio_fingerprint(recordings_list)
    if report.get("audio_manifest_sha256") != expected_audio:
        raise ValueError("report audio fingerprint does not match manifest")
    queries = manifest.get("queries")
    if not isinstance(queries, list):
        raise ValueError("manifest queries must be a list")
    query_by_id: dict[str, dict[str, Any]] = {}
    for row in queries:
        if not isinstance(row, dict):
            raise ValueError("query must be an object")
        qid = _text(row.get("id"), "query.id")
        if qid in query_by_id:
            raise ValueError(f"duplicate query id: {qid}")
        recording_id = _text(row.get("recording_id"), f"query {qid}.recording_id")
        if recording_id not in recordings:
            raise ValueError(f"query {qid} has unknown recording")
        if row.get("split") != recordings[recording_id]["split"]:
            raise ValueError(f"query {qid} split differs from its recording")
        query_by_id[qid] = row
    if not query_by_id:
        raise ValueError("manifest requires at least one query")
    models = report.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("report requires models")

    rankings: dict[str, dict[str, list[str]]] = {}
    union_by_query: dict[str, set[str]] = {qid: set() for qid in query_by_id}
    for method, model in models.items():
        _text(method, "method")
        method_queries = model.get("queries") if isinstance(model, dict) else None
        if not isinstance(method_queries, list):
            raise ValueError(f"model {method} has invalid queries")
        for result in method_queries:
            qid = result.get("query_id") if isinstance(result, dict) else None
            if qid not in query_by_id:
                raise ValueError(f"model {method} has foreign query {qid}")
            if method in rankings.get(qid, {}):
                raise ValueError(f"model {method} repeats query result {qid}")
            query_recording_id = query_by_id[qid]["recording_id"]
            if result.get("recording_id") != query_recording_id:
                raise ValueError(f"model {method} query {qid} references the wrong query recording")
            rows = result.get("rankings")
            if not isinstance(rows, list):
                raise ValueError(f"model {method} query {qid} has invalid rankings")
            ids = []
            for row in rows[:5]:
                rid = row.get("recording_id") if isinstance(row, dict) else None
                if rid not in recordings:
                    raise ValueError(f"model {method} query {qid} has foreign candidate {rid}")
                candidate = recordings[rid]
                query_recording = recordings[query_recording_id]
                if candidate["split"] != query_recording["split"]:
                    raise ValueError(f"model {method} query {qid} has candidate from another split")
                same_recording = candidate["recording_identity"] == query_recording["recording_identity"]
                if rid == query_recording_id or same_recording:
                    raise ValueError(f"model {method} query {qid} contains the query recording")
                if rid in ids:
                    raise ValueError(f"model {method} query {qid} repeats candidate {rid}")
                ids.append(rid)
            rankings.setdefault(qid, {})[method] = ids
            union_by_query[qid].update(ids)
    expected_methods = set(models)
    if any(set(rankings.get(qid, {})) != expected_methods for qid in query_by_id):
        raise ValueError("every query must have rankings for every model")

    experiment = hashlib.sha256(f"{manifest_hash}:{report_hash}".encode()).hexdigest()
    public: dict[str, Any] = {"experiment": experiment, "cases": [], "credits": [],
                              "review_note": manifest.get("review_note", "") }
    key: dict[str, Any] = {"experiment": experiment, "manifest_sha256": manifest_hash,
                           "report_sha256": report_hash, "protocol": report["protocol"],
                           "cases": [], "judgments": {}}
    used = {row["recording_id"] for row in queries}
    used.update(*(ids for ids in union_by_query.values()))
    output.mkdir(parents=True, exist_ok=False)
    clips = output / "clips"
    clips.mkdir()
    clip_names: dict[str, str] = {}
    for rid in sorted(used):
        row = recordings[rid]
        source = Path(row["source_path"]).expanduser()
        if not source.is_file() or _sha256(source) != row["audio_sha256"]:
            raise ValueError(f"recording {rid} source is missing or checksum differs")
        name = hashlib.sha256(f"{experiment}:{rid}".encode()).hexdigest()[:24] + ".wav"
        destination = clips / name
        clipper(source, float(row["start_seconds"]), float(row["duration_seconds"]), destination)
        if not destination.is_file():
            raise ValueError(f"clipper did not create clip for {rid}")
        actual_duration = duration_probe(destination)
        expected_duration = float(row["duration_seconds"])
        duration_tolerance = max(0.1, expected_duration * 0.02)
        if not math.isfinite(actual_duration) or abs(actual_duration - expected_duration) > duration_tolerance:
            raise ValueError(f"recording {rid} clip duration differs from requested segment")
        clip_names[rid] = name
        public["credits"].append({"recording_id": rid, "title": row["title"], "artist": row["artist"],
                                  "attribution": row["attribution"], "license": row["license"]})

    rng = random.Random(experiment)
    for case_index, (qid, query) in enumerate(query_by_id.items(), 1):
        seed_id = query["recording_id"]
        candidate_ids = sorted(union_by_query[qid])
        rng.shuffle(candidate_ids)
        public_rows = []
        key_case = {"query_id": qid, "seed": seed_id, "rankings": rankings[qid]}
        for position, rid in enumerate(candidate_ids, 1):
            judgment = f"q{case_index}-p{position}"
            row = recordings[rid]
            public_rows.append({"judgment": judgment, "clip": clip_names[rid], "title": row["title"],
                                "artist": row["artist"], "attribution": row["attribution"],
                                "license": row["license"]})
            key["judgments"][judgment] = {"query_id": qid, "recording_id": rid}
        seed = recordings[seed_id]
        public["cases"].append({"query_id": qid,
            "seed": {"clip": clip_names[seed_id], "title": seed["title"], "artist": seed["artist"]},
            "candidates": public_rows})
        key["cases"].append(key_case)
    return public, key


def assess(key: dict[str, Any], ratings: dict[str, Any]) -> dict[str, Any]:
    if ratings.get("experiment") != key.get("experiment"):
        raise ValueError("ratings belong to another experiment")
    rows = ratings.get("ratings")
    if not isinstance(rows, list):
        raise ValueError("ratings must be a list")
    accepted: dict[str, dict[str, Any]] = {}
    for row in rows:
        jid = row.get("judgment") if isinstance(row, dict) else None
        if jid not in key["judgments"] or jid in accepted:
            raise ValueError("unknown or duplicate judgment")
        if row.get("fit") not in {"yes", "partly", "no", "unavailable"}:
            raise ValueError("invalid fit rating")
        if row.get("known") not in {"yes", "no", "unknown"} or row.get("save") not in {"yes", "no", "unknown"}:
            raise ValueError("invalid discovery rating")
        if not isinstance(row.get("note", ""), str):
            raise ValueError("note must be a string")
        accepted[jid] = row
    by_pair = {(key["judgments"][jid]["query_id"], key["judgments"][jid]["recording_id"]): row
               for jid, row in accepted.items()}
    results = []
    for case in key["cases"]:
        for method, ids in case["rankings"].items():
            top = ids[:5]
            judged = [by_pair.get((case["query_id"], rid)) for rid in top]
            audible = [row for row in judged if row and row["fit"] != "unavailable"]
            complete = len(top) == 5 and len(audible) == 5
            results.append({"query_id": case["query_id"], "method": method, "returned": len(top),
                "audible_rated": len(audible), "fits": sum(row["fit"] == "yes" for row in audible),
                "precision_at_5": sum(row["fit"] == "yes" for row in audible) / 5 if complete else None,
                "discoveries": sum(row["fit"] == "yes" and row["known"] == "no" and row["save"] == "yes"
                                   for row in audible), "complete_top5": complete})
    return {"experiment": key["experiment"], "received": len(accepted),
            "expected": len(key["judgments"]), "results": results,
            "conclusion": "Descriptive ratings only; no automatic musical-quality or significance claim."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("manifest", type=Path)
    prepare_parser.add_argument("report", type=Path)
    prepare_parser.add_argument("output", type=Path)
    assess_parser = sub.add_parser("assess")
    assess_parser.add_argument("key", type=Path)
    assess_parser.add_argument("ratings", type=Path)
    args = parser.parse_args()
    if args.command == "assess":
        print(json.dumps(assess(json.loads(args.key.read_text()), json.loads(args.ratings.read_text())), indent=2))
        return
    manifest_raw = args.manifest.read_bytes()
    report_raw = args.report.read_bytes()
    public, key = prepare(json.loads(manifest_raw), json.loads(report_raw),
                          manifest_hash=hashlib.sha256(manifest_raw).hexdigest(),
                          report_hash=hashlib.sha256(report_raw).hexdigest(), output=args.output)
    payload = json.dumps(public).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = Path(__file__).with_name("review_retrieval.html").read_text()
    (args.output / "index.html").write_text(template.replace("__EXPERIMENT_DATA__", payload))
    (args.output / "key.json").write_text(json.dumps(key, indent=2))
    print(f"Prepared {len(public['cases'])} queries. Keep key.json private; serve with serve_local.py.")


if __name__ == "__main__":
    main()
