#!/usr/bin/env python3
"""Review-Gate: hat ein ZWEITES Modell den aktuellen CODE gegengelesen?

Ein Modell, das seinen eigenen Code reviewt, findet vor allem, was es ohnehin
schon dachte. Dieses Gate verlangt vor dem Abschluss ein Cross-Model-Review -
und zwar eines, das den Code abdeckt, der HEUTE dasteht. Ein Review von gestern
auf altem Code ist wertlos, deshalb der Fingerabdruck-Vergleich.

Nur Code zaehlt. Reine Doku-/Notiz-Aenderungen (.md, .txt, ...) loesen kein
Review aus: ein Gate, das wegen eines herumliegenden Notizzettels blockiert,
wird abgeschaltet - und ein abgeschaltetes Gate schuetzt gar nichts. Fuer Doku
ist doc_drift_check.py zustaendig.

OPT-IN pro Repo: nur aktiv, wenn .agents/review_required existiert (versioniert).

Dieses Script ist die EINZIGE Quelle des Fingerabdrucks; tools/agent_review ruft
es mit --fingerprint auf. Zwei Kopien derselben Logik wuerden auseinanderdriften,
und dann passt kein Review mehr zu keinem Gate.

  python3 scripts/review_gate.py                # Gate
  python3 scripts/review_gate.py --fingerprint  # Fingerabdruck ausgeben
"""

import hashlib
import json
import pathlib
import subprocess
import sys

# Am Script-Pfad verankern, nicht am cwd (Hook-Aufrufe haben beliebige cwd).
ROOT = pathlib.Path(__file__).resolve().parents[1]
FLAG = ROOT / ".agents" / "review_required"
LAST = ROOT / ".agents" / "reviews" / "last_review.json"

# Aenderungen an diesen Dateien sind kein Grund fuer ein Code-Review.
DOC_SUFFIXES = {".md", ".txt", ".rst", ".adoc", ".log"}

# Verzeichnisse, die nie reviewt werden (Guard-Laufzeitdaten, Build-Output).
IGNORED_PREFIXES = (".agents/", "dist/", "build/", ".build/")


def is_code(rel):
    if rel.startswith(IGNORED_PREFIXES):
        return False
    return pathlib.PurePosixPath(rel).suffix.lower() not in DOC_SUFFIXES


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout or ""


def rev_exists(ref):
    r = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref], cwd=ROOT, capture_output=True
    )
    return r.returncode == 0


def baseline():
    """Ab welchem Stand gilt Code als ungeprueft?

    Frueher war das immer HEAD - und damit liess sich das Gate trivial umgehen:
    Code committen, Arbeitsbaum ist sauber, Gate meldet "nichts gegenzulesen".
    Der Code war nie gegengelesen. (Cross-Model-Review 2026-07-14, P1.)

    Reihenfolge:
      1. der Stand, den das letzte Review abgedeckt hat
      2. sonst der Upstream-Branch - lokale, ungepushte Commits gelten als
         ungeprueft
      3. sonst HEAD (Repo ohne Remote und ohne Review: mehr ist nicht bekannt)
    """
    if LAST.exists():
        try:
            head = json.loads(LAST.read_text(encoding="utf-8")).get("head")
            if head and rev_exists(head):
                return head
        except Exception:
            pass
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").strip()
    if upstream and rev_exists(upstream):
        return upstream
    return "HEAD"


def changed_code_paths(base=None):
    """Ungeprueftes: Commits seit der Basislinie + Arbeitsbaum + ungetrackt."""
    base = base or baseline()
    paths = set()
    for rel in git("diff", "--name-only", base).splitlines():
        if rel.strip():
            paths.add(rel.strip())
    for rel in git("ls-files", "--others", "--exclude-standard").splitlines():
        if rel.strip():
            paths.add(rel.strip())
    return sorted(p for p in paths if is_code(p))


def fingerprint():
    """Hash ueber Basislinie, Pfade UND Inhalte des ungeprueften Codes."""
    base = baseline()
    parts = [f"base:{git('rev-parse', base).strip()}"]
    for rel in changed_code_paths(base):
        f = ROOT / rel
        try:
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            digest = "geloescht"
        parts.append(f"{rel}:{digest}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def review_tool():
    """Konkret aufrufbaren Pfad zu agent_review liefern.

    Das Tool liegt im Workspace, nicht im Repo - ein Hinweis auf
    "tools/agent_review" liefe aus dem Repo heraus ins Leere
    (so im Cross-Model-Review aufgefallen).
    """
    for cand in (
        ROOT / "scripts" / "agent_review",  # mit dem Plugin ausgeliefert
        ROOT.parent / "tools" / "agent_review",
        ROOT.parent / "workflow-guard-system" / "tools" / "agent_review",
    ):
        if cand.exists():
            return str(cand)
    return "scripts/agent_review  (fehlt - /init-guard erneut laufen lassen)"


def fail(msg):
    print("REVIEW-GATE: FAIL", file=sys.stderr)
    print(" - " + msg, file=sys.stderr)
    print(f"   Behebung: {review_tool()} --repo {ROOT} --uncommitted", file=sys.stderr)
    print(
        "   Abschalten: .agents/review_required loeschen (Gate ist opt-in).",
        file=sys.stderr,
    )
    return 1


def main():
    if "--fingerprint" in sys.argv:
        print(fingerprint())
        return 0

    if "--baseline" in sys.argv:
        print(git("rev-parse", baseline()).strip())
        return 0

    if not FLAG.exists():
        print("REVIEW-GATE: uebersprungen (kein .agents/review_required)")
        return 0

    changed = changed_code_paths()
    if not changed:
        print("REVIEW-GATE: OK (keine Code-Aenderungen - nichts gegenzulesen)")
        return 0

    if not LAST.exists():
        return fail(f"kein Cross-Model-Review fuer {len(changed)} geaenderte Code-Datei(en)")

    try:
        last = json.loads(LAST.read_text(encoding="utf-8"))
    except Exception as e:
        return fail(f"last_review.json nicht lesbar: {e}")

    if last.get("fingerprint") != fingerprint():
        return fail(
            f"Review ist veraltet (vom {last.get('ts', '?')}) - der Code hat sich seitdem geaendert"
        )

    print(
        f"REVIEW-GATE: OK (gegengelesen am {last.get('ts')}, "
        f"{len(changed)} Code-Datei(en), Stand unveraendert)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
