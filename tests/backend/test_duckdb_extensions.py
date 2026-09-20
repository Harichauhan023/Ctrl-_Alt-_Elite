import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def test_duckdb_opens_without_crash(tmp_path):
    from app.db.engine import _open_duckdb
    db = _open_duckdb(tmp_path / "t.duckdb")
    db.close()                                   # must NEVER raise


def test_spatial_available_or_gracefully_missed(tmp_path):
    import duckdb
    from app.db.engine import _open_duckdb
    db = _open_duckdb(tmp_path / "t2.duckdb")
    if not db.spatial_loaded:
        # degraded is legal — but a vendored copy would fix it instantly; flag it loudly
        plat = duckdb.connect().execute("PRAGMA platform").fetchone()[0]
        vend = ROOT / "third_party" / "duckdb-extensions" / duckdb.__version__ / plat
        import pytest as _pt
        _pt.skip(
            f"spatial unavailable on this network; drop binaries into {vend} "
            f"(python scripts/fetch_duckdb_extensions.py on an open machine)"
        )
    db.close()
