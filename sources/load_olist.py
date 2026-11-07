"""Load the nine Olist CSV files into Oracle, MySQL and PostgreSQL (story S1-09).

Usage (repo root, venv active, .env filled in):
    python sources/load_olist.py --ddl            # create tables, then load everything
    python sources/load_olist.py --only mysql     # one system only
    python sources/load_olist.py --reload         # wipe the tables and load again

Safe to re-run: it refuses to load into a table that already has rows unless you pass
--reload. Each table is loaded in one transaction, so a failure leaves it empty, not half full.
"""
import argparse
import sys
import time

import pandas as pd
from sqlalchemy import delete, func, select

from klarity_db import (CSV_OF, REPO, SYSTEMS, T, apply_ddl, convert_values, csv_columns,
                        get_engine, tables_for)

CHUNK = 20_000


def load_table(conn, table, csv_path):
    cols = csv_columns(table.name)
    total = 0
    for chunk in pd.read_csv(csv_path, dtype=str, keep_default_na=False,
                             encoding="utf-8", chunksize=CHUNK):
        missing = [c for c in cols if c not in chunk.columns]
        if missing:
            raise ValueError(f"{csv_path.name}: missing columns {missing}")
        typed = {c: convert_values(chunk[c].tolist(), table.c[c].type) for c in cols}
        rows = [dict(zip(cols, values)) for values in zip(*(typed[c] for c in cols))]
        conn.execute(table.insert(), rows)
        total += len(rows)
    return total


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--data-dir", default=str(REPO / "sources" / "olist_data"))
    p.add_argument("--only", choices=[*SYSTEMS, "all"], default="all")
    p.add_argument("--ddl", action="store_true", help="create the tables first")
    p.add_argument("--reload", action="store_true", help="delete existing rows first")
    args = p.parse_args(argv)

    from pathlib import Path
    data_dir = Path(args.data_dir)
    systems = SYSTEMS if args.only == "all" else [args.only]
    missing = [CSV_OF[t.name] for s in systems for t in tables_for(s)
               if not (data_dir / CSV_OF[t.name]).exists()]
    if missing:
        print(f"ERROR: missing CSV files in {data_dir}: {missing}", file=sys.stderr)
        return 2

    for system in systems:
        engine = get_engine(system)
        tables = tables_for(system)
        if args.ddl:
            apply_ddl(engine, system)
            print(f"[{system}] tables created")
        with engine.begin() as conn:
            counts = {t.name: conn.execute(select(func.count()).select_from(t)).scalar_one()
                      for t in tables}
        if any(counts.values()) and not args.reload:
            print(f"[{system}] ERROR: tables already hold rows {counts}. Use --reload to replace them.",
                  file=sys.stderr)
            return 3
        if args.reload:
            with engine.begin() as conn:
                for t in reversed(tables):
                    conn.execute(delete(t))
            print(f"[{system}] existing rows removed")
        for t in tables:
            start = time.time()
            with engine.begin() as conn:
                n = load_table(conn, t, data_dir / CSV_OF[t.name])
            print(f"[{system}] {t.name}: {n:,} rows in {time.time() - start:.1f}s")
    print("Load finished. Next: python sources/verify_load.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
