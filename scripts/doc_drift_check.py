#!/usr/bin/env python3
"""Doku-Drift-Gate: behauptete Pfade muessen wirklich existieren.

Automatisch gepflegte Doku driftet still in Fiktion ab: sie beschreibt Dateien,
die es nicht (mehr) gibt, und nachgelagerte Agenten bauen gegen Erfundenes.
Dieses Gate prueft eine harte Tatsache: Jeder Pfad, den die Guard-Docs in
Backticks behaupten, existiert im Repo.

Bewusst konservativ - ein Gate mit Fehlalarmen wird abgeschaltet und ist dann
wertlos. Geprueft wird nur, was eindeutig ein Repo-Pfad ist:
  - keine URLs, keine absoluten Pfade, keine ~/-Pfade (nicht unsere Wahrheit)
  - keine Globs/Platzhalter, keine Befehle, keine ENV-Variablen
  - ohne Verzeichnistrenner nur bei bekannter Dateiendung (sonst waere
    `Promise.all` oder `0.0.0.0` ein "Pfad")
  - Treffer auch per Suffix: `pipeline/ports.ts` findet `src/pipeline/ports.ts`

Laufzeit-Artefakte (.env, Outputs, Logs) kommen zeilenweise nach
.agents/doc_paths_ignore - versioniert, damit jede Ausnahme sichtbar bleibt.

  python3 scripts/doc_drift_check.py            # Gate (Exit 1 bei Drift)
  python3 scripts/doc_drift_check.py --report   # nur berichten (Exit 0)
"""

import argparse
import pathlib
import re
import sys

# Am Script-Pfad verankern, nicht am cwd (Hook-Aufrufe haben beliebige cwd).
ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ["WORKFLOWS.md", "CHECKS.md", "KNOWN_ERRORS.md"]
IGNORE_FILE = ROOT / ".agents" / "doc_paths_ignore"

INLINE_CODE = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^\s*```")

# .agents NICHT prunen: project_check ist versionierte Projektwahrheit und
# wird in CHECKS.md zu Recht behauptet.
PRUNE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".build",
    "build",
    "dist",
    ".next",
    "__pycache__",
    ".swiftpm",
    "target",
    "out",
}

# Ohne "/" nur pruefen, wenn die Endung wirklich nach Datei aussieht.
FILE_EXTS = {
    "ts",
    "tsx",
    "js",
    "jsx",
    "mjs",
    "cjs",
    "py",
    "sh",
    "zsh",
    "bash",
    "md",
    "json",
    "jsonl",
    "toml",
    "yml",
    "yaml",
    "swift",
    "sql",
    "txt",
    "lock",
    "cfg",
    "ini",
    "plist",
    "env",
    "html",
    "css",
    "rs",
    "go",
}

COMMAND_HEADS = {
    "npm",
    "npx",
    "node",
    "uv",
    "uvx",
    "python",
    "python3",
    "pip",
    "pytest",
    "git",
    "swift",
    "bash",
    "zsh",
    "sh",
    "brew",
    "cd",
    "ls",
    "cat",
    "grep",
    "rm",
    "mkdir",
    "curl",
    "open",
    "ruff",
    "mypy",
    "eslint",
    "tsc",
    "vitest",
    "docker",
    "make",
    "sudo",
    "export",
    "source",
    "chmod",
    "codex",
    "claude",
}
GLOB_CHARS = set("*?[]{}$<>|!")


def looks_like_path(tok):
    if not tok or len(tok) > 200:
        return False
    if any(c.isspace() for c in tok):
        return False  # Befehlszeile, kein Pfad
    if "://" in tok:
        return False  # URL
    if tok.startswith(("/", "~", "-", "#", "@", "%", "..")):
        return False  # absolut/home/Nachbarrepo/Flag - nicht unsere Wahrheit
    if any(c in GLOB_CHARS for c in tok):
        return False  # Glob/Platzhalter
    if tok.isupper():
        return False  # ENV-Variable
    head = tok.split("/", 1)[0]
    if head in COMMAND_HEADS:
        return False

    if "/" in tok:
        return True  # Verzeichnistrenner -> Pfadbehauptung

    # Kein "/": nur mit plausibler Dateiendung und nicht-leerem Namen.
    m = re.match(r"^(.+)\.([A-Za-z0-9]{1,6})$", tok)
    if not m:
        return False
    stem, ext = m.group(1), m.group(2).lower()
    return bool(stem) and ext in FILE_EXTS


def load_ignore():
    pats = set()
    if IGNORE_FILE.exists():
        for line in IGNORE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pats.add(line)
    return pats


def repo_paths():
    """Alle Repo-Pfade als POSIX-Strings, ohne Build-/Fremd-Verzeichnisse."""
    out = set()
    for p in ROOT.rglob("*"):
        if any(part in PRUNE_DIRS for part in p.relative_to(ROOT).parts):
            continue
        out.add(p.relative_to(ROOT).as_posix())
    return out


def resolve(tok, known):
    """Exakter Treffer oder Suffix-Treffer (pipeline/ports.ts -> src/pipeline/ports.ts)."""
    cand = tok[2:] if tok.startswith("./") else tok
    cand = cand.rstrip("/")
    if not cand:
        return True
    if cand in known:
        return True
    suffix = "/" + cand
    return any(k.endswith(suffix) for k in known)


def candidates(doc):
    out, in_fence = [], False
    text = doc.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for tok in INLINE_CODE.findall(line):
            tok = tok.strip().rstrip(",.;:)")
            if looks_like_path(tok):
                out.append((lineno, tok))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="nur berichten, nie fehlschlagen")
    args = ap.parse_args()

    ignore = load_ignore()
    known = repo_paths()
    missing, checked = [], 0

    for name in DOCS:
        doc = ROOT / name
        if not doc.exists():
            continue
        for lineno, tok in candidates(doc):
            if tok in ignore:
                continue
            checked += 1
            if not resolve(tok, known):
                missing.append(f"{name}:{lineno}: behauptet, existiert nicht: {tok}")

    if missing:
        report = args.report
        stream = sys.stdout if report else sys.stderr
        print("DOC-DRIFT: Report" if report else "DOC-DRIFT: FAIL", file=stream)
        for m in missing:
            print(" - " + m, file=stream)
        print(
            f"({checked} Pfade geprueft, {len(missing)} unbelegt. Doku korrigieren, "
            f"oder Laufzeit-Artefakte nach .agents/doc_paths_ignore)",
            file=stream,
        )
        return 0 if report else 1

    print(f"DOC-DRIFT: OK ({checked} behauptete Pfade existieren)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
