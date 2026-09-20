#!/usr/bin/env python3
"""Fetch DuckDB extensions for THIS platform into the vendored cache.

    python scripts/fetch_duckdb_extensions.py

Copies spatial+vss into <repo>/third_party/duckdb-extensions/<ver>/<platform>/.
Once present, the app loads them offline forever (engine._ensure_extension
tier-2). Run this ON ANY machine that CAN reach extensions.duckdb.org, then
copy the resulting third_party folder to firewalled machines.
"""
from __future__ import annotations
import gzip, shutil, sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    import duckdb
    ver = duckdb.__version__
    plat = duckdb.connect().execute("PRAGMA platform").fetchone()[0]
    out = ROOT / "third_party" / "duckdb-extensions" / ver / plat
    out.mkdir(parents=True, exist_ok=True)
    print(f"▶ duckdb {ver} · platform {plat} → {out}")
    for name in ("spatial", "vss"):
        target = out / f"{name}.duckdb_extension"
        if target.exists():
            print(f"  ✔ {name} already vendored"); continue
        url = f"https://extensions.duckdb.org/{ver}/{plat}/{name}.duckdb_extension.gz"
        print(f"  ⭳ {url}")
        data = urlopen(url, timeout=120).read()
        target.write_bytes(gzip.decompress(data))
        print(f"  ✔ {name} vendored ({target.stat().st_size/1e6:.1f} MB)")
    print("✅ done — boot the app and duckdb will load these offline")

if __name__ == "__main__":
    main()
