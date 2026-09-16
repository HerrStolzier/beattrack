"""Verify strict, independent full-corpus embedding retrieval."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "independent_retrieval", Path(__file__).parents[1] / "scripts/listening/retrieval.py",
)
retrieval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retrieval)


def manifest():
    evidence = {"declaration": "test fixture permission", "analysis": True, "storage": True, "listening": True}
    audio = {"audio_sha256": "a" * 64, "start_seconds": 0.0, "duration_seconds": 10.0}
    return {
        "recordings": [
            {"id": "q", "recording_family": "fq", "recording_identity": "iq", "artist_group": "aq",
             "split": "dev", "source_evidence": evidence, **audio},
            {"id": "a", "recording_family": "fa", "recording_identity": "ia", "artist_group": "aa",
             "split": "dev", "source_evidence": evidence, **audio},
            {"id": "b", "recording_family": "fb", "recording_identity": "ib", "artist_group": "ab",
             "split": "dev", "source_evidence": evidence, **audio},
            {"id": "c", "recording_family": "fc", "recording_identity": "ic", "artist_group": "ac",
             "split": "dev", "source_evidence": evidence, **audio},
        ],
        "queries": [{"id": "query", "recording_id": "q", "split": "dev", "positives": ["c"]}],
    }


def model(name, vectors):
    recordings = manifest()["recordings"]
    segments = {row["id"]: {key: row[key] for key in ("audio_sha256", "start_seconds", "duration_seconds")}
                for row in recordings}
    return {"model": name, "revision": "commit-1",
            "preprocessing": {"audio": "same 10 s", "pooling": "mean"},
            "audio_segments": segments, "vectors": vectors}


def run(data=None, models=None):
    data = data or manifest()
    models = models or {"baseline": model("base", {"q": [1, 0], "a": [1, 0], "b": [0.8, 0.2], "c": [0, 1]})}
    return retrieval.benchmark(data, models, fingerprints={"manifest_sha256": "x", "embedding_sha256": {}})


def test_alternate_encoder_finds_candidate_absent_from_baseline_top_two():
    models = {
        "baseline": model("base", {"q": [1, 0], "a": [1, 0], "b": [0.8, 0.2], "c": [0, 1]}),
        "alternate": model("alt", {"q": [1, 0], "a": [0, 1], "b": [-1, 0], "c": [1, 0]}),
    }
    report = run(models=models)
    base = report["models"]["baseline"]["queries"][0]
    alt = report["models"]["alternate"]["queries"][0]
    assert "c" not in [row["recording_id"] for row in base["rankings"][:2]]
    assert alt["rankings"][0]["recording_id"] == "c"
    assert alt["positive_ranks"] == [{"recording_id": "c", "rank": 1}]
    assert len(base["rankings"]) == len(alt["rankings"]) == 3


@pytest.mark.parametrize("field", ["recording_family", "artist_group"])
def test_dev_test_group_leakage_is_rejected(field):
    data = manifest()
    copied = dict(data["recordings"][0])
    copied.update(id="test-recording", split="test", recording_family="other-family", artist_group="other-artist")
    copied[field] = data["recordings"][0][field]
    data["recordings"].append(copied)
    with pytest.raises(ValueError, match="leaks across dev/test"):
        run(data=data)


def test_missing_vectors_are_rejected_without_fallback():
    with pytest.raises(ValueError, match="missing vectors: c"):
        run(models={"broken": model("broken", {"q": [1, 0], "a": [1, 0], "b": [0, 1]})})


@pytest.mark.parametrize("bad", [[0, 0], [float("nan"), 1], [float("inf"), 1], []])
def test_invalid_vectors_are_rejected(bad):
    vectors = {"q": [1, 0], "a": [1, 0], "b": [0, 1], "c": bad}
    with pytest.raises(ValueError, match="nonzero dimension|finite numbers|invalid zero"):
        run(models={"broken": model("broken", vectors)})


def test_ties_are_deterministic_by_recording_id():
    vectors = {rid: [1, 0] for rid in ("q", "a", "b", "c")}
    first = run(models={"same": model("same", vectors)})
    second = run(models={"same": model("same", vectors)})
    assert first == second
    assert [row["recording_id"] for row in first["models"]["same"]["queries"][0]["rankings"]] == ["a", "b", "c"]


def test_query_and_same_recording_are_excluded_but_distinct_remix_is_retained():
    data = manifest()
    data["recordings"][1]["recording_family"] = "fq"
    data["recordings"][2]["recording_identity"] = "iq"
    embeddings = model("base", {"q": [1, 0], "a": [1, 0], "b": [0.8, 0.2], "c": [0, 1]})
    report = run(data=data, models={"baseline": embeddings})
    ids = [row["recording_id"] for row in report["models"]["baseline"]["queries"][0]["rankings"]]
    assert "q" not in ids
    assert "b" not in ids
    assert ids == ["a", "c"]


def test_audio_segment_fingerprint_mismatch_is_rejected():
    embeddings = model("base", {"q": [1, 0], "a": [1, 0], "b": [0.8, 0.2], "c": [0, 1]})
    embeddings["audio_segments"]["c"]["duration_seconds"] = 9.0
    with pytest.raises(ValueError, match="do not match the corpus audio segments"):
        run(models={"baseline": embeddings})


def test_duplicate_recording_identity_has_one_deterministic_candidate():
    data = manifest()
    duplicate = dict(data["recordings"][1])
    duplicate["id"] = "a-alias"
    data["recordings"].append(duplicate)
    embeddings = model("base", {
        "q": [1, 0], "a": [1, 0], "a-alias": [1, 0], "b": [0.8, 0.2], "c": [0, 1],
    })
    embeddings["audio_segments"]["a-alias"] = embeddings["audio_segments"]["a"]
    report = run(data=data, models={"baseline": embeddings})
    ids = [row["recording_id"] for row in report["models"]["baseline"]["queries"][0]["rankings"]]
    assert ids == ["a", "b", "c"]


def test_report_writer_does_not_overwrite_existing_file(tmp_path):
    output = tmp_path / "report.json"
    retrieval._write_report(output, {"first": True})
    with pytest.raises(FileExistsError):
        retrieval._write_report(output, {"second": True})
    assert output.read_text() == '{\n  "first": true\n}\n'
