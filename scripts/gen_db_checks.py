#!/usr/bin/env python3
"""Generate database-checks artifacts for the Cloud Hermes Core V1 smoke DB.

Emits into artifacts/cloud-hermes-core-v1/database-checks/:
  - schema.sql        : full sqlite_master DDL (tables + triggers + indexes)
  - integrity.txt     : PRAGMA integrity_check + foreign_key_check + row counts
  - tables.csv        : per-table row counts
"""
from __future__ import annotations
import csv
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_DIR = "F:/Users/user/Documents/learning os-worktrees/artifacts/cloud-hermes-core-v1/database-checks"
DB_PATHS = [
    os.path.join(REPO, "work", "smoke-data", "hermes_cloud.db"),
    os.path.join(REPO, "hermes_cloud.db"),
]


def find_db() -> str:
    for p in DB_PATHS:
        if os.path.exists(p):
            return p
    raise SystemExit(f"No smoke DB found among: {DB_PATHS}")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    db_path = find_db()
    print(f"[db-checks] using: {db_path}")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    # 1) schema DDL
    rows = con.execute(
        "SELECT type,name,sql FROM sqlite_master "
        "WHERE sql IS NOT NULL ORDER BY type, name"
    ).fetchall()
    with open(os.path.join(OUT_DIR, "schema.sql"), "w", encoding="utf-8") as f:
        f.write(f"-- Cloud Hermes Core V1 — schema dump\n")
        f.write(f"-- source: {db_path}\n\n")
        for r in rows:
            f.write(f"-- {r['type']}: {r['name']}\n")
            f.write(r["sql"].rstrip() + ";\n\n")

    # 2) integrity + fk + counts
    integrity = con.execute("PRAGMA integrity_check").fetchall()
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    with open(os.path.join(OUT_DIR, "integrity.txt"), "w", encoding="utf-8") as f:
        f.write("PRAGMA integrity_check:\n")
        f.write("\n".join((r[0] for r in integrity)) or "ok" + "\n")
        f.write("\n\nPRAGMA foreign_key_check (should be empty):\n")
        f.write("\n".join((str(dict(r)) for r in fk)) or "(none — no FK violations)\n")

    # 3) row counts per table
    tables = [r["name"] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]
    counts = []
    for t in tables:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
        except Exception as e:  # pragma: no cover
            n = f"ERR:{e}"
        counts.append((t, n))
    with open(os.path.join(OUT_DIR, "tables.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["table", "row_count"])
        for t, n in counts:
            w.writerow([t, n])

    # 4) append-only event store verification
    evt_total = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    trig = con.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' "
        "AND (name LIKE '%no_update%' OR name LIKE '%no_delete%')"
    ).fetchall()
    with open(os.path.join(OUT_DIR, "integrity.txt"), "a", encoding="utf-8") as f:
        f.write(f"\nevents total rows: {evt_total}\n")
        f.write("append-only triggers present: " + (", ".join(r["name"] for r in trig) or "NONE") + "\n")

    print(f"[db-checks] wrote schema.sql, integrity.txt, tables.csv to {OUT_DIR}")
    print(f"[db-checks] tables={len(tables)} events={evt_total} integrity={integrity[0][0] if integrity else '?'} fk_violations={len(fk)}")
    # Fold the WAL into the main db so the artifact file is self-contained/portable.
    try:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print("[db-checks] wal_checkpoint(TRUNCATE) done")
    except Exception as e:  # pragma: no cover
        print(f"[db-checks] wal_checkpoint skipped: {e}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
