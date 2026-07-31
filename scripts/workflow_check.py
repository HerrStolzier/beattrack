#!/usr/bin/env python3
"""Struktur-Guard: Pflichtdateien, Pflichtabschnitte, Kopfzeilen, keine Platzhalter.

Rein strukturell und damit in jedem Repo identisch (per md5 pruefbar).
Technische Projektchecks gehoeren NICHT hierher, sondern nach
.agents/project_check - agent_finish.py fuehrt sie aus.
"""

import pathlib
import re
import sys

# Am Script-Pfad verankern, nicht am cwd (Hook-Aufrufe haben beliebige cwd).
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Datei -> Liste von Markierungen, die im Text vorkommen muessen
REQUIRED_FILES = {
    "CLAUDE.md": ["## Abschluss", "## Belegpflicht"],
    "WORKFLOWS.md": ["## "],
    "KNOWN_ERRORS.md": [],
    "CHECKS.md": ["## Standardabschluss"],
}

REQUIRED_SCRIPTS = [
    "scripts/workflow_check.py",
    "scripts/agent_finish.py",
    "scripts/claim_check.py",
    "scripts/doc_drift_check.py",
    "scripts/review_gate.py",
    "scripts/agent_review",
]

# Unausgefuellte Templates sind schlimmer als keine Doku: sie lesen sich wie Wahrheit.
PLACEHOLDER_MARKERS = ["PLATZHALTER", "TODO(guard)", "<!-- fixme -->"]

# Nur diese Dateien werden auf Platzhalter geprueft (nicht der ganze Code).
PLACEHOLDER_SCOPE = ["WORKFLOWS.md", "CHECKS.md", "KNOWN_ERRORS.md"]

# Greppbarer Kopf: Agenten sollen per grep das richtige Doc finden, statt alle
# zu lesen. Muss direkt nach dem H1 stehen, damit `head` es sicher erfasst.
HEADER_SCOPE = ["WORKFLOWS.md", "CHECKS.md", "KNOWN_ERRORS.md"]
HEADER_LINES = 10
HEADER_FIELDS = ["Zweck", "Scope", "Suchbegriffe", "Stand"]
STAND_RE = re.compile(r"^> \*\*Stand:\*\* (\d{4}-\d{2}-\d{2})\s*$")


def check_required_files(problems):
    for fname, needles in REQUIRED_FILES.items():
        p = ROOT / fname
        if not p.exists():
            problems.append(f"fehlt: {fname}")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for n in needles:
            if n not in text:
                problems.append(f"{fname}: Abschnitt/Markierung fehlt: '{n.strip()}'")


def check_required_scripts(problems):
    for s in REQUIRED_SCRIPTS:
        if not (ROOT / s).exists():
            problems.append(f"fehlt: {s}")


def check_placeholders(problems):
    for fname in PLACEHOLDER_SCOPE:
        p = ROOT / fname
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            for marker in PLACEHOLDER_MARKERS:
                if marker in line:
                    problems.append(f"{fname}:{lineno}: unausgefuellter Platzhalter '{marker}'")


def check_headers(problems):
    for fname in HEADER_SCOPE:
        p = ROOT / fname
        if not p.exists():
            continue  # Fehlen meldet bereits check_required_files
        head = p.read_text(encoding="utf-8", errors="replace").splitlines()[:HEADER_LINES]
        for field in HEADER_FIELDS:
            if not any(line.startswith(f"> **{field}:**") for line in head):
                problems.append(
                    f"{fname}: Kopfzeile '> **{field}:**' fehlt in den ersten {HEADER_LINES} Zeilen"
                )
        stand = [line for line in head if line.startswith("> **Stand:**")]
        if stand and not STAND_RE.match(stand[0]):
            problems.append(f"{fname}: '> **Stand:**' braucht ein Datum als YYYY-MM-DD")


def main():
    problems = []
    check_required_files(problems)
    check_required_scripts(problems)
    check_headers(problems)
    check_placeholders(problems)

    if problems:
        print("WORKFLOW-GUARD: FAIL", file=sys.stderr)
        for p in problems:
            print(" - " + p, file=sys.stderr)
        return 1

    print("WORKFLOW-GUARD: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
