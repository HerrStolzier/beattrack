"""Ensure blindness, repeatability and honest treatment of missing judgments."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "listening_experiment", Path(__file__).parents[1] / "scripts/listening/experiment.py",
)
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def snapshot():
    return {"captured_at": "test", "stats_sha256": "stats", "normalization_configs": [
        {"key": "normalization_stats", "value": {"mean": [0.0] * 44, "std": [1.0] * 44}},
    ], "cases": [{
        "seed": {"id": "seed", "title": "Seed", "artist": "Artist",
                 "handcrafted_raw": [1.0] * 44},
        "candidates": [{"id": str(i), "title": f"Track {i}", "artist": f"Artist {i}",
                        "similarity": 0.9 - i * 0.01} for i in range(12)],
        "vectors": [{"id": str(i), "handcrafted_raw": [1.0 if i > 5 else -1.0] * 44}
                    for i in range(12)],
    }]}


def test_reproducible_blinded_union_without_duplicate_judgments():
    public, key = experiment.prepare(snapshot(), snapshot_hash="same")
    assert (public, key) == experiment.prepare(snapshot(), snapshot_hash="same")
    candidates = public["cases"][0]["candidates"]
    assert len(candidates) == len(key["judgments"]) == 12
    assert not any({"similarity", "method", "_signals", "rankings"} & row.keys() for row in candidates)
    assert key["cases"][0]["rankings"]["musicnn"] != key["cases"][0]["rankings"]["fusion"]
    assert key["cases"][0]["rankings"]["fusion"] == key["cases"][0]["rankings"]["fusion_mert"]


def test_missing_and_unavailable_judgments_are_not_negative_votes():
    _, key = experiment.prepare(snapshot(), snapshot_hash="same")
    empty = experiment.assess(key, {"experiment": key["experiment"], "ratings": []})
    assert all(row["precision_at_10"] is None for row in empty["results"])
    ratings = [{"judgment": jid, "fit": "unavailable", "known": "unknown", "save": "unknown"}
               for jid in key["judgments"]]
    report = experiment.assess(key, {"experiment": key["experiment"], "ratings": ratings})
    assert all(row["audible_rated"] == 0 and row["precision_at_10"] is None for row in report["results"])
    for row in ratings:
        row.update(fit="yes", known="no", save="yes")
    report = experiment.assess(key, {"experiment": key["experiment"], "ratings": ratings})
    assert all(row["precision_at_10"] == 1 and row["discoveries_to_save"] == 10 for row in report["results"])


def test_wrong_experiment_is_rejected():
    _, key = experiment.prepare(snapshot(), snapshot_hash="same")
    with pytest.raises(ValueError, match="another snapshot"):
        experiment.assess(key, {"experiment": "wrong", "ratings": []})


def test_recording_chosen_under_different_ids_gets_one_judgment():
    data = snapshot()
    data["cases"][0]["candidates"][0]["deezer_id"] = 123
    data["cases"][0]["candidates"][8]["deezer_id"] = 123
    public, key = experiment.prepare(data, snapshot_hash="duplicate-recording")
    assert sum(r.get("deezer_id") == 123 for r in public["cases"][0]["candidates"]) == 1
    assert "8" not in [r["song"] for r in key["judgments"].values()]
    assert all("8" not in ids for ids in key["cases"][0]["rankings"].values())
