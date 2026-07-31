#!/usr/bin/env python3
"""Ein-Befehl-Abschluss fuer Agenten.

Reihenfolge:
  1. Struktur-Guard (workflow_check.py)
  2. Doku-Drift-Gate (doc_drift_check.py) - behauptete Pfade muessen existieren
  3. Review-Gate (review_gate.py) - opt-in via .agents/review_required
  4. Technischer Projektcheck (Befehl aus .agents/project_check, optional)
  5. Optional: Claim-Check (--auto-claims)
  6. Lauf-Log nach .agents/finish_runs.jsonl

Exit-Code 2 bei Fehlschlag, damit ein Stop-Hook den Abschluss blockiert.
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys

# Am Script-Pfad verankern, NICHT am cwd: Der Stop-Hook kann mit einem beliebigen
# Arbeitsverzeichnis starten. Mit cwd-relativem ROOT wuerde .agents/project_check
# dann nicht gefunden und der Projektcheck STILL uebersprungen - ein Guard, der
# "OK" meldet, ohne geprueft zu haben.
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
AGENTS = ROOT / ".agents"
RUNS = AGENTS / "command_runs.jsonl"
FINISH_LOG = AGENTS / "finish_runs.jsonl"


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def record_command(command, exit_code):
    AGENTS.mkdir(exist_ok=True)
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"command": command, "exit_code": exit_code, "ts": now()},
                ensure_ascii=False,
            )
            + "\n"
        )


def run(cmd):
    print(f"$ {cmd}")
    return subprocess.run(cmd, shell=True, cwd=ROOT).returncode


def read_stdin_json():
    try:
        if not sys.stdin.isatty():
            return json.loads(sys.stdin.read() or "{}")
    except Exception:
        pass
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto-claims", action="store_true")
    args = ap.parse_args()

    read_stdin_json()  # Hook-Payload konsumieren (Stop-Hook uebergibt JSON via stdin)

    steps = []

    # 1) Struktur-Guard
    steps.append(("workflow_check", run("python3 scripts/workflow_check.py")))

    # 2) Doku-Drift: behauptet die Doku Pfade, die es nicht gibt?
    steps.append(("doc_drift", run("python3 scripts/doc_drift_check.py")))

    # 3) Cross-Model-Review (nur wenn .agents/review_required existiert)
    steps.append(("review_gate", run("python3 scripts/review_gate.py")))

    # 4) Technischer Projektcheck (optional)
    pc = AGENTS / "project_check"
    if pc.exists() and pc.read_text(encoding="utf-8").strip():
        cmd = pc.read_text(encoding="utf-8").strip()
        crc = run(cmd)
        record_command(cmd, crc)
        steps.append(("project_check", crc))
    else:
        print("project_check: uebersprungen (keine .agents/project_check) - Grund dokumentieren")
        steps.append(("project_check_skipped", 0))

    # 4) Claims
    if args.auto_claims:
        steps.append(("claim_check", run("python3 scripts/claim_check.py")))

    failed = [n for n, c in steps if c != 0]

    # Den Abschlussbefehl selbst als Evidenz protokollieren - ERST JETZT, nach ALLEN
    # Schritten. Vorher geloggt wuerde ein fehlgeschlagener claim_check als
    # "exit_code: 0" im Beleg-Log stehen: falsche Evidenz fuer kuenftige Claims.
    finish_cmd = "python3 scripts/agent_finish.py" + (" --auto-claims" if args.auto_claims else "")
    record_command(finish_cmd, 0 if not failed else 1)

    FINISH_LOG.parent.mkdir(exist_ok=True)
    with FINISH_LOG.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"ts": now(), "steps": dict(steps), "ok": not failed},
                ensure_ascii=False,
            )
            + "\n"
        )

    if failed:
        print("AGENT-FINISH: FAIL -> " + ", ".join(failed), file=sys.stderr)
        print(
            "Arbeit ist nicht abgeschlossen. Bitte beheben und erneut abschliessen.",
            file=sys.stderr,
        )
        return 2

    print("AGENT-FINISH: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
