import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.config import get_settings                     # noqa: E402
from app.geospatial.features import init_extractor      # noqa: E402
from app.geospatial.hexgrid import hotspot_grid         # noqa: E402
from app.geospatial.loader import get_store             # noqa: E402


@pytest.fixture(scope="session")
def store():
    return get_store(get_settings().data_dir)


@pytest.fixture(scope="session", autouse=True)
def extractor(store):
    """Engine tests run on the memory extractor (DB-free & fast).
    SQL-extractor parity is covered separately in test_features.py."""
    return init_extractor(None, store)


@pytest.fixture(scope="session")
def grid(store, extractor):
    if not hotspot_grid.ready:
        hotspot_grid.build(store, extractor, None)
    return hotspot_grid


@pytest.fixture(scope="session")
def tmp_geodb(store):
    """Isolated temp DuckDB + spatial, seeded from the real layers."""
    import tempfile
    from app.db.engine import _open_duckdb
    from app.db.seed import seed_geodb
    path = Path(tempfile.mkdtemp(prefix="geoready-test-")) / "test.duckdb"
    db = _open_duckdb(path)
    if not db.spatial_loaded:
        import pytest as _pt
        _pt.skip("duckdb 'spatial' extension unavailable on this machine "
                 "(network blocks extensions.duckdb.org and no vendored copy loaded)")
    seed_geodb(db, store)
    yield db
    db.close()
