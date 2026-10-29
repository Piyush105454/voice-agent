import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

# Tests never call paid APIs, including from background threads that outlive a test's monkeypatch.
# (Unit tests that exercise a client set a fake key explicitly and stub the HTTP call.)
from config import settings  # noqa: E402

settings.anthropic_api_key = ""
settings.sarvam_api_key = ""
settings.bolna_api_key = ""

# Tests reset their database: never the one the running app uses (real students' sign-ups live there).
_live_url = settings.database_url
_base, _, _name = _live_url.rpartition("/")
if not _name.endswith("_test"):
    settings.database_url = f"{_base}/{_name}_test"
    settings.graph_name = f"{settings.graph_name}_test"
    try:
        import psycopg

        with psycopg.connect(f"{_base}/postgres", autocommit=True, connect_timeout=3) as conn:
            if not conn.execute("select 1 from pg_database where datname=%s", (f"{_name}_test",)).fetchone():
                conn.execute(f'create database "{_name}_test"')
    except Exception:
        pass  # databases down: the DB tests skip themselves
