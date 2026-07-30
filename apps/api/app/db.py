import os
import functools

from supabase import create_client, Client


def _url() -> str:
    return os.environ["SUPABASE_URL"]


@functools.lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Standard-Client fuer alle DB-Zugriffe der API.

    Nutzt den service_role-Key, wenn vorhanden. Auf dem eigenen Server hat die
    anon-Rolle bewusst keinen Zugriff mehr auf `songs` — die API ist der einzige
    Leser und arbeitet deshalb mit erhoehten Rechten. Der Fallback auf den
    anon-Key bleibt fuer lokale Entwicklung gegen Supabase erhalten.
    """
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_ANON_KEY"]
    return create_client(_url(), key)


@functools.lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
    return create_client(_url(), key)
