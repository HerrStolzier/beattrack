"""Frozen candidate-pool listening comparison, without network access.

prepare snapshot.json output_directory
assess output_directory/key.json ratings.json
"""
import argparse
import hashlib
import json
import random
import copy
from pathlib import Path

from app.routes.similar import _deduplicate_versions, _fuse_candidates
from app.services.vectors import parse_vector
from app.services.features import normalize_handcrafted

METHODS = ("musicnn", "fusion", "fusion_mert")


def prepare(snapshot, *, snapshot_hash):
    snapshot = copy.deepcopy(snapshot)
    config = next((r["value"] for r in snapshot["normalization_configs"]
                   if r["key"] == "normalization_stats"), None)
    stats = json.loads(config) if isinstance(config, str) else config
    if not isinstance(stats, dict) or not parse_vector(stats.get("mean"), 44) or not parse_vector(stats.get("std"), 44):
        raise ValueError("A frozen valid normalization_stats configuration is required")
    if any(value < 0 for value in stats["std"]):
        raise ValueError("Negative standard deviation")
    api = Path(__file__).parents[2]
    code_hash = hashlib.sha256(b"".join(path.read_bytes() for path in [
        Path(__file__), api / "app/routes/similar.py", api / "app/services/vectors.py",
        api / "app/services/features.py",
    ])).hexdigest()
    experiment_hash = hashlib.sha256((snapshot_hash + code_hash).encode()).hexdigest()
    public = {"experiment": experiment_hash, "cases": []}
    key = {"experiment": experiment_hash, "snapshot_sha256": snapshot_hash, "code_sha256": code_hash,
           "protocol": "fixed-30-local-normalization-no-mmr-v1",
           "captured_at": snapshot["captured_at"], "stats_sha256": snapshot["stats_sha256"],
           "cases": [], "judgments": {}}
    rng = random.Random(snapshot_hash)
    for case_index, case in enumerate(snapshot["cases"]):
        seed = case["seed"]
        candidates = case["candidates"]
        normalized_count = 0
        for row in [seed, *case["vectors"]]:
            raw = parse_vector(row.get("handcrafted_raw"), 44)
            row["handcrafted_norm"] = (parse_vector(normalize_handcrafted(raw, stats), 44)
                                       if raw is not None else None)
            normalized_count += row["handcrafted_norm"] is not None
        if len({r["id"] for r in candidates}) != len(candidates):
            raise ValueError("Duplicate candidate IDs")
        if any(r["id"] == seed["id"] for r in candidates):
            raise ValueError("Reference leaked into candidates")
        recordings = {}
        canonical = {}
        for row in candidates:
            recording = ("deezer", row["deezer_id"]) if row.get("deezer_id") else ("id", row["id"])
            canonical[row["id"]] = recordings.setdefault(recording, row["id"])
        hc = parse_vector(seed.get("handcrafted_norm"), 44)
        mert = parse_vector(seed.get("mert_embedding"), 768)
        rankings = {}
        signals = {}
        # Fixed weights: genre feedback and MMR deliberately excluded so only
        # the scoring signal changes. This is not the full production pipeline.
        for method in METHODS:
            if method == "musicnn":
                rows = sorted(candidates, key=lambda r: r["similarity"], reverse=True)
            else:
                rows = _fuse_candidates(candidates, hc, case["vectors"],
                                        query_mert=mert if method == "fusion_mert" else None)
            top = _deduplicate_versions(rows)[:10]
            rankings[method] = [canonical[r["id"]] for r in top]
            signals[method] = {canonical[r["id"]]: r.get("_signals", ["musicnn"]) for r in top}
        union = sorted({sid for ids in rankings.values() for sid in ids})
        rng.shuffle(union)
        by_id = {row["id"]: row for row in candidates}
        public_rows = []
        for position, sid in enumerate(union):
            judgment = f"s{case_index + 1}-p{position + 1}"
            row = by_id[sid]
            public_rows.append({"judgment": judgment, "title": row["title"],
                                "artist": row["artist"], "deezer_id": row.get("deezer_id")})
            key["judgments"][judgment] = {"seed": seed["id"], "song": sid}
        public["cases"].append({"seed": {k: seed.get(k) for k in ("title", "artist", "deezer_id")},
                                "candidates": public_rows})
        key["cases"].append({"seed": seed["id"], "rankings": rankings, "signals": signals,
                             "recording_aliases": canonical,
                             "normalized_locally": normalized_count,
                             "rows_to_normalize": 1 + len(case["vectors"]),
                             "query_signals": {"handcrafted": hc is not None, "mert": mert is not None}})
    return public, key


def assess(key, ratings):
    if ratings.get("experiment") != key["experiment"]:
        raise ValueError("Ratings belong to another snapshot")
    judgments = {}
    for row in ratings["ratings"]:
        jid = row["judgment"]
        if jid not in key["judgments"] or jid in judgments:
            raise ValueError("Unknown or duplicate judgment")
        if row["fit"] not in ("yes", "partly", "no", "unavailable"):
            raise ValueError("Invalid fit rating")
        if row["known"] not in ("yes", "no", "unknown") or row["save"] not in ("yes", "no", "unknown"):
            raise ValueError("Invalid discovery rating")
        judgments[jid] = row
    by_pair = {(key["judgments"][jid]["seed"], key["judgments"][jid]["song"]): row
               for jid, row in judgments.items()}
    report = {"experiment": key["experiment"], "received": len(judgments),
              "expected": len(key["judgments"]), "results": [],
              "conclusion": "Descriptive only; no automatic product-quality or significance claim."}
    for case in key["cases"]:
        for method, ids in case["rankings"].items():
            rows = [by_pair.get((case["seed"], sid)) for sid in ids]
            audible = [r for r in rows if r and r["fit"] != "unavailable"]
            hits = sum(r["fit"] == "yes" for r in audible)
            complete = len(audible) == len(ids) and len(ids) == 10
            report["results"].append({"seed": case["seed"], "method": method,
                "returned": len(ids), "audible_rated": len(audible), "fits": hits,
                "partly": sum(r["fit"] == "partly" for r in audible),
                "discoveries_to_save": sum(r["known"] == "no" and r["save"] == "yes" for r in audible),
                "precision_at_10": hits / 10 if complete else None,
                "complete_top10": complete})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "assess"])
    parser.add_argument("input", type=Path)
    parser.add_argument("output_or_ratings", type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    if args.command == "assess":
        print(json.dumps(assess(json.loads(raw), json.loads(args.output_or_ratings.read_text())), indent=2))
        return
    public, key = prepare(json.loads(raw), snapshot_hash=hashlib.sha256(raw).hexdigest())
    out = args.output_or_ratings
    out.mkdir(parents=True, exist_ok=False)
    (out / "key.json").write_text(json.dumps(key, indent=2))
    template = Path(__file__).with_name("listening.html").read_text()
    # Escape the HTML script boundary; all displayed metadata uses textContent.
    payload = json.dumps(public).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    (out / "index.html").write_text(template.replace("__EXPERIMENT_DATA__", payload))
    print(f"Prepared {len(public['cases'])} references; open index.html, keep key.json separate.")


if __name__ == "__main__":
    main()
