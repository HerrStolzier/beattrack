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

Dieses Script ist die EINZIGE Quelle des Fingerabdrucks UND des Ablageorts;
tools/agent_review ruft es mit --fingerprint bzw. --store auf. Zwei Kopien
derselben Logik wuerden auseinanderdriften, und dann passt kein Review mehr zu
keinem Gate.

  python3 scripts/review_gate.py                     # Gate
  python3 scripts/review_gate.py --fingerprint       # Fingerabdruck ausgeben
  python3 scripts/review_gate.py --fingerprint <rev> # ... gegen eine feste Basislinie
  python3 scripts/review_gate.py --store             # Ablageort der Belege ausgeben
"""

import hashlib
import json
import os
import pathlib
import subprocess
import sys

# Am Script-Pfad verankern, nicht am cwd (Hook-Aufrufe haben beliebige cwd).
ROOT = pathlib.Path(__file__).resolve().parents[1]
FLAG = ROOT / ".agents" / "review_required"

# Alt-Pfad. Bis 2026-08-04 lag der Beleg hier - IM Arbeitsbaum, und damit in
# jedem Worktree ein eigener. Wird nur noch gelesen, damit Repos mit altem
# Beleg nicht ploetzlich blockieren; geschrieben wird in store_dir().
LEGACY_LAST = ROOT / ".agents" / "reviews" / "last_review.json"

# Namen im gemeinsamen Speicher (siehe store_dir()).
STORE_SUBDIR = ("workflow-guard", "reviews")
RECORD_LOG = "records.jsonl"
LAST_NAME = "last_review.json"

# So viele juengste Belege liest das Gate. agent_review kuerzt das Log auf
# dieselbe Zahl - beide Werte gehoeren zusammen.
MAX_RECORDS = 20

# Aenderungen an diesen Dateien sind kein Grund fuer ein Code-Review.
DOC_SUFFIXES = {".md", ".txt", ".rst", ".adoc", ".log"}

# Verzeichnisse, die nie reviewt werden (Guard-Laufzeitdaten, Build-Output).
IGNORED_PREFIXES = (".agents/", "dist/", "build/", ".build/")

# ... mit Ausnahme der versionierten Regeln des Guards selbst. Sie liegen unter
# .agents/ und waeren damit vom Praefix-Filter erfasst gewesen: Wer
# project_check abschwaecht oder review_required loescht, aendert WAS geprueft
# wird bzw. OB geprueft wird - und ausgerechnet das lief ohne Gegenlesen durch.
# Ein Gate, das seine eigenen Regeln nicht schuetzt, ist keins.
# (Cross-Model-Review 2026-07-31, P1.)
POLICY_PATHS = frozenset(
    {
        ".agents/project_check",
        ".agents/review_required",
        ".agents/doc_paths_ignore",
        ".agents/.gitignore",
    }
)


def is_code(rel):
    if rel in POLICY_PATHS:
        return True
    if rel.startswith(IGNORED_PREFIXES):
        return False
    return pathlib.PurePosixPath(rel).suffix.lower() not in DOC_SUFFIXES


class GitError(RuntimeError):
    """Eine git-Abfrage ist gescheitert: Ergebnis unbekannt, NICHT leer."""


def git(*args):
    """Fail closed - ein gescheiterter Aufruf ist kein leeres Ergebnis.

    Frueher lieferte diese Funktion bei jedem Fehler "". changed_code_paths()
    las das als "nichts geaendert", und das Gate meldete OK. Ein gesperrter
    Index, ein kaputtes Repo oder ein Rechteproblem liess damit ungepruefen
    Code durch - genau im Moment, in dem das Gate haette halten muessen.
    (Cross-Model-Review 2026-07-31, P1.)
    """
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        detail = (r.stderr or "").strip() or f"Exit {r.returncode}"
        raise GitError(f"git {' '.join(args)}: {detail}")
    return r.stdout or ""


_MEMO = {}


def memo(key, produce):
    """Eine Frage pro Lauf. baseline() wird mehrfach gebraucht, git ist teuer."""
    if key not in _MEMO:
        _MEMO[key] = produce()
    return _MEMO[key]


def store_dir():
    """Der gemeinsame Review-Speicher von Hauptcheckout UND allen Worktrees.

    Frueher lag der Beleg unter <arbeitsbaum>/.agents/reviews/. Jeder Worktree
    hatte damit seinen eigenen, und `git worktree remove` loeschte ihn mit.
    Beobachtet am 2026-08-04 in investors-club-global: Review gruen, PR
    gemergt, Worktree abgeraeumt - und im Hauptcheckout war der Beleg weg,
    obwohl exakt dieser Code gegengelesen worden war. Das Review musste komplett
    neu laufen. Ein Beleg, der mit dem Arbeitsbaum stirbt, ist keiner.

    `git rev-parse --git-common-dir` zeigt aus jedem Worktree auf dasselbe .git
    des Hauptcheckouts. Der Beleg liegt damit (a) an EINER Stelle fuer alle
    Arbeitsbaeume und (b) strukturell ausserhalb der Versionskontrolle - was in
    .git/ liegt, kann nicht committet werden. Das war vorher eine
    .gitignore-Zusage, jetzt ist es eine Eigenschaft des Ortes.

    None, wenn git nicht antwortet - der Aufrufer faellt dann auf den Alt-Pfad
    zurueck. Bewusst kein Fehler: der Ort ist kein Anspruch auf den Code.
    """
    return memo("store", _store_dir)


def _store_dir():
    r = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], cwd=ROOT, capture_output=True, text=True
    )
    raw = (r.stdout or "").strip()
    if r.returncode != 0 or not raw:
        return None
    common = pathlib.Path(raw)
    if not common.is_absolute():
        # rev-parse antwortet relativ zum cwd, und das ist hier ROOT.
        common = ROOT / common
    return common.resolve().joinpath(*STORE_SUBDIR)


def records():
    """Bekannte Review-Belege, neuester zuerst.

    Mehrere statt einer: seit der Speicher gemeinsam ist, schreiben parallele
    Worktrees in dieselbe Ablage. Mit nur einem Datensatz wuerde jede Sitzung
    den Beleg der anderen entwerten, und beide muessten staendig neu reviewen -
    der Preis fuer die Rettung waere ein staendig blockierendes Gate.

    Ohne Fingerabdruck ist ein Datensatz wertlos und wird verworfen: er koennte
    sonst ueber seinen `head` die Basislinie setzen, ohne je etwas belegt zu
    haben.
    """
    return memo("records", _records)


def read_text(path):
    """Inhalt oder None. Ein fehlender Beleg ist der Normalfall, kein Fehler."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _records():
    blobs = []
    store = store_dir()
    if store:
        log = read_text(store / RECORD_LOG)
        if log:
            blobs.extend(log.splitlines()[-MAX_RECORDS:])
        blobs.append(read_text(store / LAST_NAME))
    blobs.append(read_text(LEGACY_LAST))

    out = []
    for blob in blobs:
        if not blob or not blob.strip():
            continue
        try:
            rec = json.loads(blob)
        except Exception:
            continue
        if isinstance(rec, dict) and rec.get("fingerprint"):
            out.append(rec)
    return sorted(out, key=lambda r: str(r.get("ts") or ""), reverse=True)


def upstream_ref():
    """Upstream-Branch oder None, wenn keiner gesetzt ist.

    "Kein Upstream" ist ein normaler Zustand. Ein Repo, das nicht antwortet,
    ist es nicht: Faellt baseline() dann still auf HEAD zurueck, sind lokale,
    ungepruefte Commits nicht mehr im Diff und das Gate meldet "keine
    Aenderungen". Unterschieden wird ueber die Frage, ob das Repo ueberhaupt
    noch antwortet - nicht ueber den Text der Fehlermeldung, der an Sprache und
    git-Version haengt. (Cross-Model-Review 2026-07-31, zweite Runde.)
    """
    r = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        return r.stdout.strip() or None

    # Fehlgeschlagen. Ist ueberhaupt einer konfiguriert? Wenn nein, ist das der
    # Normalfall. Wenn doch, konnte git ihn nur nicht aufloesen - dann ist die
    # Basislinie unbekannt, und still auf HEAD zurueckzufallen wuerde lokale,
    # ungepruefte Commits aus dem Diff nehmen. (Dritte Review-Runde.)
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "-q", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if branch.returncode != 0:
        return None  # detached HEAD oder kein Repo: kein Upstream-Begriff
    name = branch.stdout.strip()
    configured = subprocess.run(
        ["git", "config", "--get", f"branch.{name}.merge"],
        cwd=ROOT,
        capture_output=True,
    )
    if configured.returncode != 0:
        return None  # kein Upstream gesetzt - normaler Zustand
    detail = (r.stderr or "").strip() or f"Exit {r.returncode}"
    raise GitError(f"Upstream fuer {name} konfiguriert, aber nicht aufloesbar: {detail}")


def gate_armed():
    """Ist das Gate scharf?

    Auch dann, wenn die Flagge im Arbeitsbaum schon geloescht ist, aber noch in
    HEAD steht: Sonst liesse sich das Gate mit einem `rm` lautlos abschalten,
    und ausgerechnet die Abschaltung waere das Einzige, was nie gegengelesen
    wird. Ist die Loeschung committet, ist das Gate aus - dann steht sie im
    Diff und jemand hat sie gesehen. (Cross-Model-Review 2026-07-31, P1.)

    Ob die Flagge in HEAD steht, muss git beantworten. Kann git das nicht, ist
    die Antwort unbekannt - und "unbekannt" darf nicht "aus" heissen, sonst
    schaltet ein defektes Repo das Gate ab (zweite Review-Runde).
    """
    if FLAG.exists():
        return True
    if not (ROOT / ".git").exists():
        # Gar kein Repo (auch kein Worktree-Verweis): hier gab es nie eine
        # Flagge, und ohne Historie kann das Gate ohnehin nichts pruefen.
        return False
    if not rev_exists("HEAD"):
        # Repo da, HEAD aber unlesbar: ob die Flagge einmal drin war, ist nicht
        # feststellbar. Ein defektes Repo darf das Gate nicht abschalten.
        return True
    # ls-tree statt cat-file: cat-file liefert fuer "Pfad nicht in HEAD" und fuer
    # echte Fehler denselben Code (128) und taugt damit nicht zur Unterscheidung.
    # ls-tree endet mit 0 und leerer Ausgabe, wenn der Pfad fehlt.
    try:
        in_head = git("ls-tree", "--name-only", "HEAD", "--", ".agents/review_required")
    except GitError:
        return True
    return bool(in_head.strip())


def rev_exists(ref):
    """Existiert der Commit WIRKLICH - nicht nur sein Name?

    `rev-parse --verify` allein reicht nicht: fuer eine volle SHA antwortet git
    auch dann noch mit Exit 0, wenn das Objekt laengst weg ist (die
    commit-graph-Datei kennt es noch). Nachgemessen am 2026-08-04: nach
    Squash-Merge, Branch-Loeschung und `git gc --prune=now` meldete
    `rev-parse --verify` weiter Erfolg, `git diff <sha>` brach mit
    "fatal: bad object" ab. Das Gate haette dann nicht sauber auf den Upstream
    zurueckfallen koennen, sondern waere mit "Stand nicht feststellbar"
    gescheitert - richtig blockierend, aber mit falscher Begruendung.
    `^{commit}` erzwingt, dass das Objekt geladen wird.
    """
    r = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
    )
    return r.returncode == 0


def is_ancestor(ref, other):
    """Baut `other` auf `ref` auf? Fehler zaehlt als nein (fail closed)."""
    r = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ref, other], cwd=ROOT, capture_output=True
    )
    return r.returncode == 0


def baseline():
    """Ab welchem Stand gilt Code als ungeprueft?

    Frueher war das immer HEAD - und damit liess sich das Gate trivial umgehen:
    Code committen, Arbeitsbaum ist sauber, Gate meldet "nichts gegenzulesen".
    Der Code war nie gegengelesen. (Cross-Model-Review 2026-07-14, P1.)

    Reihenfolge:
      1. der juengste Review-Stand, auf dem DIESER Arbeitsbaum aufbaut
      2. sonst der Upstream-Branch - lokale, ungepushte Commits gelten als
         ungeprueft
      3. sonst HEAD (Repo ohne Remote und ohne Review: mehr ist nicht bekannt)

    "auf dem dieser Arbeitsbaum aufbaut" ist seit dem gemeinsamen Speicher
    noetig: dort liegen auch die Belege paralleler Worktrees. Der Stand eines
    Nachbarbranches ist fuer diesen hier keine Basislinie - er wuerde einen
    Diff quer ueber beide Branches erzeugen, und das Review liefe auf einem
    Umfang, den niemand gemeint hat. Ein nicht passender Beleg wird deshalb
    uebergangen, nicht benutzt; die Basislinie rutscht dann auf den Upstream,
    also nach hinten - im Zweifel wird mehr geprueft, nie weniger.
    """
    return memo("baseline", _baseline)


def _baseline():
    for rec in records():
        head = rec.get("head")
        if head and rev_exists(head) and is_ancestor(head, "HEAD"):
            return head
    upstream = upstream_ref()
    if upstream and rev_exists(upstream):
        return upstream
    return "HEAD"


def nul_paths(*args):
    """Pfadliste NUL-separiert abfragen - die einzige Form, die git nie quotet.

    Ohne `-z` quotet git Pfade mit Umlaut/Sonderzeichen (core.quotepath) und
    escapet Zeilenumbrueche: `"sch\\303\\266n.py"` existiert als Datei nie, ihr
    Inhalt ging als Konstante "geloescht" in den Fingerabdruck ein, und
    Aenderungen an der echten Datei blieben fuer das Gate unsichtbar. Zugleich
    galt eine gequotete `.md`-Datei wegen des Suffixes `.md"` als Code.
    (Ist-Zustand-Analyse 2026-08-04, per Repro belegt.)

    Bewusst als Bytes gelesen und mit os.fsdecode dekodiert: git liefert bei
    `-z` die rohen Pfad-Bytes. Ein Name, der kein gueltiges UTF-8 ist, wuerde
    mit text=True als UnicodeDecodeError durchschlagen - das Gate koennte in
    so einem Repo nie wieder einen Fingerabdruck bilden. fsdecode rundet die
    Bytes verlustfrei durch Pfad-Operationen (surrogateescape).
    (Cross-Model-Review 2026-08-05, P2.)
    """
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        detail = r.stderr.decode("utf-8", "replace").strip() or f"Exit {r.returncode}"
        raise GitError(f"git {' '.join(args)}: {detail}")
    return [os.fsdecode(p) for p in (r.stdout or b"").split(b"\0") if p]


def changed_code_paths(base=None):
    """Ungeprueftes: Commits seit der Basislinie + Arbeitsbaum + ungetrackt."""
    base = base or baseline()
    paths = set()
    # --no-renames: Bei erkannter Umbenennung nennt git nur den NEUEN Pfad. Ein
    # `git mv .agents/review_required .agents/review_required.disabled` waere so
    # unsichtbar geblieben - der neue Name faellt unter den .agents/-Filter, der
    # alte tauchte nie auf, und das Gate meldete "keine Code-Aenderungen",
    # waehrend gerade die Reviewpflicht abgeraeumt wurde. Ohne Rename-Erkennung
    # erscheinen beide Pfade. (Cross-Model-Review 2026-07-31, vierte Runde.)
    paths.update(nul_paths("diff", "--no-renames", "--name-only", "-z", base))
    paths.update(nul_paths("ls-files", "--others", "--exclude-standard", "-z"))
    return sorted(p for p in paths if is_code(p))


def fingerprint(base=None):
    """Hash ueber Basislinie, Pfade UND Inhalte des ungeprueften Codes.

    `base` ist angebbar, weil jeder Beleg seine EIGENE Basislinie mitbringt.
    Ohne das vergleicht das Gate Aepfel mit Birnen: agent_review laesst den
    Fingerabdruck berechnen, BEVOR es den Beleg schreibt - danach setzt genau
    dieser Beleg die Basislinie neu, und der eigene Fingerabdruck passt nicht
    mehr zu dem, was das Gate ausrechnet. Sichtbar wird das, sobald Beleg-Kopf
    und Basislinie auseinanderfallen (Commit waehrend der Arbeit, paralleler
    Worktree); latent war es vorher schon.
    """
    base = base or baseline()
    return memo(f"fp:{base}", lambda: _fingerprint(base))


def _fingerprint(base):
    parts = [f"base:{git('rev-parse', base).strip()}"]
    for rel in changed_code_paths(base):
        f = ROOT / rel
        try:
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            digest = "geloescht"
        # Laengen-Praefix macht die Serialisierung eindeutig. Seit Pfade mit
        # Zeilenumbruch roh durchkommen, konnte EIN gebastelter Dateiname wie
        # "a.py:<hash>\nb.py" die Eintraege ZWEIER reviewter Dateien imitieren -
        # gleicher Fingerabdruck, ungepruefter Code. Mit "<laenge>:<pfad>:" ist
        # jede Zeichenkette nur noch auf eine Weise lesbar. Aendert den
        # Fingerabdruck bestehender Belege mit offenen Aenderungen: das Gate
        # fordert dort EINMAL ein frisches Review - zu viel pruefen, nie zu
        # wenig. (Cross-Model-Review 2026-08-05, P1.)
        parts.append(f"{len(rel)}:{rel}:{digest}")
    return hashlib.sha256("\n".join(parts).encode("utf-8", "surrogatepass")).hexdigest()


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
    print(f"   Belege liegen in: {store_dir() or LEGACY_LAST.parent}", file=sys.stderr)
    print(
        "   Abschalten: .agents/review_required loeschen (Gate ist opt-in).",
        file=sys.stderr,
    )
    return 1


def main():
    # Die Abfragemodi duerfen bei einem git-Fehler nichts ausgeben: agent_review
    # liest sie und wuerde eine leere Zeile als gueltige Antwort verbuchen.
    if "--fingerprint" in sys.argv:
        # Optionale feste Basislinie. agent_review erhebt den Fingerabdruck
        # zweimal - vor und nach dem Review - und muss beide Male gegen DIESELBE
        # Basislinie rechnen. Sonst verschiebt ein Beleg aus einem parallelen
        # Worktree die Basislinie mitten im Lauf, die beiden Fingerabdruecke
        # unterscheiden sich, und ein voellig korrektes Review wuerde verworfen.
        # (Cross-Model-Review 2026-08-04, zweite Runde.)
        i = sys.argv.index("--fingerprint")
        rest = sys.argv[i + 1 :]
        pinned = rest[0] if rest and not rest[0].startswith("-") else None
        try:
            print(fingerprint(pinned))
        except GitError as e:
            print(f"REVIEW-GATE: Fingerabdruck nicht ermittelbar - {e}", file=sys.stderr)
            return 2
        return 0

    if "--baseline" in sys.argv:
        try:
            print(git("rev-parse", baseline()).strip())
        except GitError as e:
            print(f"REVIEW-GATE: Basislinie nicht ermittelbar - {e}", file=sys.stderr)
            return 2
        return 0

    if "--store" in sys.argv:
        # Anders als --fingerprint/--baseline behauptet dieser Modus nichts ueber
        # den Code, er nennt nur einen Ort. Antwortet git nicht, ist der
        # Alt-Pfad die richtige Antwort - dann schreiben Gate und agent_review
        # weiter an dieselbe Stelle, statt auseinanderzulaufen.
        print(store_dir() or LEGACY_LAST.parent)
        return 0

    if not gate_armed():
        print("REVIEW-GATE: uebersprungen (kein .agents/review_required)")
        return 0

    try:
        changed = changed_code_paths()
    except GitError as e:
        return fail(f"Stand nicht feststellbar, {e}")
    if not changed:
        print("REVIEW-GATE: OK (keine Code-Aenderungen - nichts gegenzulesen)")
        return 0

    known = records()
    if not known:
        return fail(f"kein Cross-Model-Review fuer {len(changed)} geaenderte Code-Datei(en)")

    # Jeder Beleg zaehlt, nicht nur der juengste: im gemeinsamen Speicher liegen
    # auch die der Nachbar-Worktrees. Geprueft wird jeder gegen SEINE eigene
    # Basislinie - ein Beleg von nebenan kann so nicht faelschlich passen, denn
    # der Fingerabdruck deckt Basislinie, Pfade und Inhalte ab.
    match = None
    for rec in known:
        base = rec.get("base")
        if base and not rev_exists(base):
            continue  # Beleg zeigt auf einen Stand, den es nicht mehr gibt
        try:
            if fingerprint(base) == rec.get("fingerprint"):
                match = rec
                break
        except GitError as e:
            return fail(f"Fingerabdruck nicht ermittelbar, {e}")

    if not match:
        return fail(
            f"Review ist veraltet (vom {known[0].get('ts', '?')}) - "
            "der Code hat sich seitdem geaendert"
        )

    print(
        f"REVIEW-GATE: OK (gegengelesen am {match.get('ts')}, "
        f"{len(changed)} Code-Datei(en), Stand unveraendert)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
