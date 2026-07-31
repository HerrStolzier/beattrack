#!/usr/bin/env python3
"""Prueft lokale Evidenz fuer behauptete Agenten-Claims.

Claim-Typen:
  file                 -> behaupteter lokaler Pfad existiert
  external_source      -> hat 'url' und 'checked_at'
  skipped_verification -> hat konkreten 'reason'
  command              -> passender Erfolgseintrag in .agents/command_runs.jsonl

Aufruf: python3 scripts/claim_check.py [pfad/zu/claims.json]
Default-Pfad: .agents/claims.json
"""

import json
import pathlib
import sys

# Am Script-Pfad verankern, nicht am cwd (Hook-Aufrufe haben beliebige cwd).
ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = ROOT / ".agents" / "command_runs.jsonl"


def load_command_successes():
    ok = set()
    if RUNS.exists():
        for line in RUNS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("exit_code") == 0 and e.get("command"):
                ok.add(e["command"].strip())
    return ok


def check_claim(c, cmd_ok):
    t = c.get("type")
    if t == "file":
        path = c.get("path", "")
        return (ROOT / path).exists(), f"file: {path}"
    if t == "external_source":
        ok = bool(c.get("url")) and bool(c.get("checked_at"))
        return ok, f"external_source: {c.get('url', '?')}"
    if t == "skipped_verification":
        return bool(c.get("reason")), f"skipped_verification: {c.get('reason', '?')}"
    if t == "command":
        cmd = (c.get("command") or "").strip()
        return cmd in cmd_ok, f"command: {cmd}"
    return False, f"unbekannter claim-typ: {t}"


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".agents" / "claims.json"
    if not path.exists():
        print(f"CLAIM-CHECK: keine Claims-Datei ({path.name}) - nichts zu pruefen.")
        return 0
    try:
        claims = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"CLAIM-CHECK: FAIL - Claims-Datei nicht lesbar: {e}", file=sys.stderr)
        return 1
    if isinstance(claims, dict):
        claims = claims.get("claims", [])

    cmd_ok = load_command_successes()
    failed = []
    for c in claims:
        ok, label = check_claim(c, cmd_ok)
        if not ok:
            failed.append(label)

    if failed:
        print("CLAIM-CHECK: FAIL", file=sys.stderr)
        for f in failed:
            print(" - unbelegt: " + f, file=sys.stderr)
        return 1

    print(f"CLAIM-CHECK: OK ({len(claims)} Claims belegt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
