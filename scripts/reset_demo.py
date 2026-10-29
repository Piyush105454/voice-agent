"""Reset the demo: drop + create schema, seed, rebuild the graph. Usage: python scripts/reset_demo.py"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from config import settings  # noqa: E402
from graph_seed import rebuild_graph  # noqa: E402
from pg import close, run, run_script  # noqa: E402


def main() -> None:
    t0 = time.perf_counter()
    for f in ("drop.sql", "schema.sql", "seed.sql"):
        run_script((ROOT / "sql" / f).read_text(encoding="utf-8"))
        print(f"  applied sql/{f}")
    if settings.demo_student_phone:
        run("update students set phone_e164=%s where first_name='Rahul'", (settings.demo_student_phone,))
        print("  Rahul's phone set from DEMO_STUDENT_PHONE")
    print(f"  graph rebuilt: {rebuild_graph()}")
    print(f"done in {time.perf_counter() - t0:.2f}s")
    close()


if __name__ == "__main__":
    main()
