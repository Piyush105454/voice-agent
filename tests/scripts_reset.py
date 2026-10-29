"""Test helper: reset the demo DB + graph (same as scripts/reset_demo.py, importable)."""
from pathlib import Path

from graph_seed import rebuild_graph
from pg import run_script

ROOT = Path(__file__).resolve().parent.parent


def reset() -> None:
    for f in ("drop.sql", "schema.sql", "seed.sql"):
        run_script((ROOT / "sql" / f).read_text(encoding="utf-8"))
    import db
    for fn in (db.misconception_descriptions, db.misconception_names, db.topic_names):
        fn.cache_clear()
    rebuild_graph()
