"""Job-Status in Postgres (Tabelle analysis_jobs) statt im Prozessspeicher.

API und Worker laufen als getrennte Container. Ein Dictionary im Speicher ist
dann pro Prozess privat — der Fortschritt des Workers wäre für die API
unsichtbar. Die Tabelle analysis_jobs existierte bereits mit passendem Schema
und wird hier erstmals verdrahtet (siehe infra-migration/docs/plan-audio-analyse.md).

Alle Funktionen sind synchron (der Supabase-Client blockiert). In asynchronen
Pfaden immer über asyncio.to_thread aufrufen.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.db import get_supabase

logger = logging.getLogger(__name__)

# Ein processing-Job ohne Statusupdate seit dieser Zeit gilt als abgestürzt.
# Der Worker meldet Fortschritt bei 0.1/0.8/1.0 — Stillstand heißt Absturz.
# Bewusst unterhalb des SSE-Abbruchs (900 s), damit der Nutzer die Meldung sieht.
STALL_AFTER_SEC = 300

# Notbremsen für den Upload-Ordner (gemeinsames Volume, wird nie pauschal geleert)
ORPHAN_MAX_AGE_SEC = 24 * 3600
VOLUME_CAP_BYTES = 5 * 1024**3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(job_id: str, audio_path: str, duration_sec: float | None) -> None:
    get_supabase().table("analysis_jobs").insert({
        "id": job_id,
        "status": "queued",
        "progress": 0.0,
        "audio_path": audio_path,
        "duration_sec": duration_sec,
    }).execute()


def update_job_status(job_id: str, status: str, progress: float | None = None,
                      result: dict | None = None, error: str | None = None) -> None:
    """Statusupdate aus API oder Worker. Signatur kompatibel zum alten Wrapper."""
    row: dict = {"status": status, "updated_at": _now()}
    if progress is not None:
        row["progress"] = progress
    if result is not None:
        row["result"] = result
    if error is not None:
        row["last_error"] = error
    if status in ("completed", "failed"):
        row["completed_at"] = _now()
    try:
        get_supabase().table("analysis_jobs").update(row).eq("id", job_id).execute()
    except Exception as exc:  # Status-Updates dürfen die Analyse nie abbrechen
        logger.warning("Job-Statusupdate fehlgeschlagen (%s -> %s): %s", job_id, status, exc)


def get_job(job_id: str) -> dict | None:
    """Liefert den Job im Format des alten _job_status-Eintrags, oder None.

    Wendet die Hängend-Regel an: processing ohne Update seit STALL_AFTER_SEC
    wird als failed gemeldet (nur in der Antwort — die Zeile bleibt unverändert,
    ein erfolgreicher später eintreffender Worker-Update gewinnt).
    """
    res = get_supabase().table("analysis_jobs").select("*").eq("id", job_id).execute()
    if not res.data:
        return None
    row = res.data[0]
    status = row["status"]

    if status == "processing" and row.get("updated_at"):
        updated = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        if age > STALL_AFTER_SEC:
            return {
                "status": "failed",
                "progress": row.get("progress", 0.0),
                "error": "Analysis stalled (no progress for 5 minutes)",
                "audio_path": row.get("audio_path"),
            }

    return {
        "status": status,
        "progress": row.get("progress", 0.0),
        "result": row.get("result"),
        "error": row.get("last_error"),
        "audio_path": row.get("audio_path"),
        "duration_sec": row.get("duration_sec"),
    }


def cleanup_temp_files(temp_dir: str) -> None:
    """Räumt den gemeinsamen Upload-Ordner auf, ohne laufende Jobs zu gefährden.

    Löscht nur: Dateien erledigter Jobs (completed/failed), verwaiste Dateien
    ohne Job-Zeile älter als 24 h, und — als harte Obergrenze — die ältesten
    Dateien ohne aktiven Job, bis das Volumen wieder unter 5 GB liegt.
    Ein pauschales Leeren (früher rmtree beim Shutdown) gibt es bewusst nicht mehr.
    """
    root = Path(temp_dir)
    if not root.exists():
        return
    files = [f for f in root.iterdir() if f.is_file()]
    if not files:
        return

    ids = [f.stem for f in files]
    active: set[str] = set()
    finished: set[str] = set()
    try:
        res = get_supabase().table("analysis_jobs").select("id,status").in_("id", ids).execute()
        for row in res.data or []:
            (finished if row["status"] in ("completed", "failed") else active).add(str(row["id"]))
    except Exception as exc:
        logger.warning("Cleanup: Job-Abfrage fehlgeschlagen, lösche nur nach Alter: %s", exc)

    import time
    now = time.time()
    for f in files:
        try:
            if f.stem in finished:
                f.unlink(missing_ok=True)
            elif f.stem not in active and now - f.stat().st_mtime > ORPHAN_MAX_AGE_SEC:
                f.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Cleanup: %s nicht löschbar: %s", f.name, exc)

    remaining = sorted((f for f in root.iterdir() if f.is_file()), key=lambda f: f.stat().st_mtime)
    total = sum(f.stat().st_size for f in remaining)
    for f in remaining:
        if total <= VOLUME_CAP_BYTES:
            break
        if f.stem in active:
            continue
        total -= f.stat().st_size
        f.unlink(missing_ok=True)
        logger.warning("Cleanup: Volumen-Obergrenze — %s gelöscht", f.name)
