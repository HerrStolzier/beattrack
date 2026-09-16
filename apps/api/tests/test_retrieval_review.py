"""Offline retrieval review stays blinded, local and honest about coverage."""
import hashlib
import importlib.util
import json
import threading
import urllib.error
import urllib.request
import wave
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest


def load(name):
    path = Path(__file__).parents[1] / f"scripts/listening/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review = load("review_retrieval")
server = load("serve_local")


def fixture(tmp_path):
    evidence = {"declaration": "fixture", "analysis": True, "storage": True, "listening": True}
    recordings = []
    for rid in ["q", "a", "b", "c", "d", "e", "f"]:
        source = tmp_path / f"{rid}.source"
        source.write_bytes(f"audio-{rid}".encode())
        recordings.append({"id": rid, "title": f"Title {rid}", "artist": f"Artist {rid}",
            "source_path": str(source), "audio_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "start_seconds": 0.0, "duration_seconds": 10.0, "attribution": f"Credit {rid}",
            "license": "Test license", "recording_identity": f"identity-{rid}", "split": "dev",
            "source_evidence": evidence})
    manifest = {"recordings": recordings,
                "queries": [{"id": "query", "recording_id": "q", "split": "dev"}]}
    audio_hash = review._audio_fingerprint(recordings)
    def rows(order):
        return [{"rank": i + 1, "recording_id": rid, "cosine": 1 - i / 10} for i, rid in enumerate(order)]
    report = {"protocol": "independent-exact-cosine-v1", "audio_manifest_sha256": audio_hash,
              "input_fingerprints": {"manifest_sha256": "m"}, "models": {
        "base": {"queries": [{"query_id": "query", "recording_id": "q",
                                "rankings": rows(["a", "b", "c", "d", "e", "f"])}]},
        "alt": {"queries": [{"query_id": "query", "recording_id": "q",
                               "rankings": rows(["f", "e", "d", "c", "b", "a"])}]},
    }}
    return manifest, report


def prepare(tmp_path):
    manifest, report = fixture(tmp_path)
    output = tmp_path / "review"
    def clipper(source, start, duration, destination):
        assert start == 0 and duration == 10
        destination.write_bytes(b"RIFF-fixture")
    public, key = review.prepare(manifest, report, manifest_hash="m", report_hash="r",
                                 output=output, clipper=clipper, duration_probe=lambda _: 10.0)
    return output, public, key


def test_top_five_union_is_repeatable_and_blinds_methods(tmp_path):
    _, public, key = prepare(tmp_path)
    assert len(public["cases"][0]["candidates"]) == 6
    assert set(key["cases"][0]["rankings"]["base"]) == {"a", "b", "c", "d", "e"}
    assert set(key["cases"][0]["rankings"]["alt"]) == {"b", "c", "d", "e", "f"}
    assert not any("method" in row or "score" in row for row in public["cases"][0]["candidates"])


def test_prepare_rejects_wrong_audio_fingerprint_and_missing_permission(tmp_path):
    manifest, report = fixture(tmp_path)
    report["audio_manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="audio fingerprint"):
        review.prepare(manifest, report, manifest_hash="m", report_hash="r", output=tmp_path / "wrong")
    report["audio_manifest_sha256"] = review._audio_fingerprint(manifest["recordings"])
    manifest["recordings"][0]["source_evidence"]["listening"] = False
    with pytest.raises(ValueError, match="listening permission"):
        review.prepare(manifest, report, manifest_hash="m", report_hash="r", output=tmp_path / "denied")


def test_prepare_binds_complete_manifest_and_rejects_duplicate_query_result(tmp_path):
    manifest, report = fixture(tmp_path)
    with pytest.raises(ValueError, match="complete manifest"):
        review.prepare(manifest, report, manifest_hash="different", report_hash="r", output=tmp_path / "hash")
    report["models"]["base"]["queries"].append(dict(report["models"]["base"]["queries"][0]))
    with pytest.raises(ValueError, match="repeats query result"):
        review.prepare(manifest, report, manifest_hash="m", report_hash="r", output=tmp_path / "duplicate")


@pytest.mark.parametrize("fault", ["self", "identity", "split"])
def test_prepare_rejects_ineligible_candidates(tmp_path, fault):
    manifest, report = fixture(tmp_path)
    first = report["models"]["base"]["queries"][0]["rankings"][0]
    if fault == "self":
        first["recording_id"] = "q"
    elif fault == "identity":
        manifest["recordings"][1]["recording_identity"] = "identity-q"
    else:
        manifest["recordings"][1]["split"] = "test"
    report["audio_manifest_sha256"] = review._audio_fingerprint(manifest["recordings"])
    with pytest.raises(ValueError, match="query recording|another split"):
        review.prepare(manifest, report, manifest_hash="m", report_hash="r", output=tmp_path / fault)


@pytest.mark.parametrize("start,duration", [(-1.0, 10.0), (float("nan"), 10.0), (0.0, 2.9), (0.0, 30.1)])
def test_prepare_rejects_invalid_segment_before_clipping(tmp_path, start, duration):
    manifest, report = fixture(tmp_path)
    manifest["recordings"][0]["start_seconds"] = start
    manifest["recordings"][0]["duration_seconds"] = duration
    called = False
    def clipper(*args):
        nonlocal called
        called = True
    with pytest.raises(ValueError, match="start_seconds|duration_seconds"):
        review.prepare(manifest, report, manifest_hash="m", report_hash="r",
                       output=tmp_path / "invalid-segment", clipper=clipper)
    assert called is False


def test_prepare_rejects_truncated_clip(tmp_path):
    manifest, report = fixture(tmp_path)
    output = tmp_path / "truncated"
    def clipper(source, start, duration, destination):
        destination.write_bytes(b"short")
    with pytest.raises(ValueError, match="clip duration differs"):
        review.prepare(manifest, report, manifest_hash="m", report_hash="r", output=output,
                       clipper=clipper, duration_probe=lambda _: 8.0)


def test_real_ffmpeg_clip_has_requested_duration(tmp_path):
    source = tmp_path / "source.wav"
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\0\0" * 8000 * 4)
    destination = tmp_path / "clip.wav"
    review._ffmpeg_clip(source, 0.5, 3.0, destination)
    assert review._probe_duration(destination) == pytest.approx(3.0, abs=0.05)


def test_missing_and_unavailable_do_not_produce_precision(tmp_path):
    _, _, key = prepare(tmp_path)
    empty = review.assess(key, {"experiment": key["experiment"], "ratings": []})
    assert all(row["precision_at_5"] is None for row in empty["results"])
    ratings = [{"judgment": jid, "fit": "unavailable", "known": "unknown", "save": "unknown", "note": ""}
               for jid in key["judgments"]]
    result = review.assess(key, {"experiment": key["experiment"], "ratings": ratings})
    assert all(row["audible_rated"] == 0 and row["precision_at_5"] is None for row in result["results"])


def test_discovery_requires_fit_unknown_and_save(tmp_path):
    _, _, key = prepare(tmp_path)
    ratings = [{"judgment": jid, "fit": "yes", "known": "no", "save": "yes", "note": ""}
               for jid in key["judgments"]]
    first = review.assess(key, {"experiment": key["experiment"], "ratings": ratings})
    assert all(row["precision_at_5"] == 1 and row["discoveries"] == 5 for row in first["results"])
    ratings[0]["fit"] = "partly"
    second = review.assess(key, {"experiment": key["experiment"], "ratings": ratings})
    assert all(row["discoveries"] == 4 for row in second["results"])


def test_assessment_rejects_foreign_and_duplicate_ids(tmp_path):
    _, _, key = prepare(tmp_path)
    valid = {"judgment": next(iter(key["judgments"])), "fit": "yes", "known": "no", "save": "yes", "note": ""}
    with pytest.raises(ValueError, match="unknown or duplicate"):
        review.assess(key, {"experiment": key["experiment"], "ratings": [valid, valid]})
    invalid = dict(valid, judgment="foreign")
    with pytest.raises(ValueError, match="unknown or duplicate"):
        review.assess(key, {"experiment": key["experiment"], "ratings": [invalid]})


def test_server_only_allows_index_and_prepared_clips(tmp_path):
    output, public, key = prepare(tmp_path)
    payload = json.dumps(public).replace("<", "\\u003c")
    output.joinpath("index.html").write_text(
        f'<script id="experiment-data" type="application/json">{payload}</script>')
    output.joinpath("key.json").write_text(json.dumps(key))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(output))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    try:
        assert urllib.request.urlopen(base + "/index.html").status == 200
        clip = public["cases"][0]["candidates"][0]["clip"]
        assert urllib.request.urlopen(base + "/clips/" + clip).read() == b"RIFF-fixture"
        for path in ("/key.json", "/../key.json", "/clips/../key.json", "/manifest.json"):
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + path)
            assert error.value.code == 404
    finally:
        httpd.shutdown()
        thread.join()
        httpd.server_close()


def test_server_rejects_nonopaque_clip_name_in_page(tmp_path):
    directory = tmp_path / "malicious"
    directory.mkdir()
    payload = {"cases": [{"seed": {"clip": "../key.json"}, "candidates": []}]}
    directory.joinpath("index.html").write_text(
        f'<script id="experiment-data" type="application/json">{json.dumps(payload)}</script>')
    with pytest.raises(ValueError, match="invalid clip name"):
        server.make_handler(directory)
