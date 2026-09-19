"""Dual-mode spatial database — the analysis backbone.

Hero mode   : PostgreSQL + PostGIS + pgvector  (docker-compose, spec §5/§18)
Fallback    : DuckDB file + spatial + vss(HNSW) extensions (embedded, zero-install)

BOTH modes run the SAME meter-based SQL (geometry stored in UTM-43N,
EPSG:32643), so every spatial analysis is a real SQL query against a real
database — no in-memory shortcut on the primary path. If even DuckDB fails to
initialise, the API degrades to the in-memory GeoPandas engine
(`features_mode = "memory"`), exactly like the AI provider failover doctrine:
the product never bricks, but the docs tell you which mode you are in.

Table layout (identical names in both modes):

    population_cells  (h3, population, density, lon, lat, geom POINT)
    roads             (road_type, name, major, speed_kmh, geom LINESTRING)
    competitors       (name, category, source, lon, lat, geom POINT)
    landuse           (category, geom POLYGON)
    risk_zones        (risk_type, risk_level, geom POLYGON)
    rag_chunks        (id, document_id, title, chunk_text, source, tags,
                       embedding VECTOR(384), created_at)
    hotspot_cells     (h3, lon, lat, features_json, geom POLYGON)
    meta_kv           (key, value)

Geometry in UTM meters ⇒ ST_Distance / ST_Buffer / ST_Length return meters,
identically in PostGIS and DuckDB.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

SRID = 32643  # UTM-43N — Rajkot

_POINT_TABLES = ("population_cells", "competitors")
_GEOM_TYPES = {
    "population_cells": "POINT",
    "roads": "LINESTRING",
    "competitors": "POINT",
    "landuse": "POLYGON",
    "risk_zones": "POLYGON",
    "hotspot_cells": "POLYGON",
}


class GeoDB:
    def __init__(self, mode: str, conn, path: str | None = None):
        self.mode = mode            # "postgis" | "duckdb"
        self.conn = conn
        self.path = path
        self.lock = threading.Lock()
        self.error: str | None = None

    # ─────────────────────────────────────────────────────────────────────
    # low-level helpers
    # ─────────────────────────────────────────────────────────────────────
    @property
    def ph(self) -> str:
        return "%s" if self.mode == "postgis" else "?"

    def q(self, sql: str, params: tuple | list | None = None):
        with self.lock:
            if self.mode == "postgis":
                cur = self.conn.cursor()
                cur.execute(sql, params or ())
                return cur.fetchall()
            return self.conn.execute(sql, params or []).fetchall()

    def x(self, sql: str, params: tuple | list | None = None):
        with self.lock:
            if self.mode == "postgis":
                cur = self.conn.cursor()
                cur.execute(sql, params or ())
            else:
                self.conn.execute(sql, params or [])

    def many(self, sql: str, rows: list[tuple]):
        if not rows:
            return
        with self.lock:
            if self.mode == "postgis":
                cur = self.conn.cursor()
                cur.executemany(sql, rows)
            elif "INSERT" in sql and "VALUES" in sql:
                # DuckDB executemany can't splay per-row args when ? appears
                # INSIDE function calls (ST_GeomFromText(?) etc.) — build one
                # compact multi-row VALUES insert with escaped literals.
                # (own seed data only — never user input)
                pre = sql.split("VALUES", 1)[0]
                body = ", ".join("(" + ",".join(self._lit(v) for v in row) + ")" for row in rows)
                self.conn.execute(pre + "VALUES " + body)
            else:
                self.conn.executemany(sql, rows)

    @staticmethod
    def _lit(v) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        if isinstance(v, (int, float)):
            return repr(v)
        return "'" + str(v).replace("'", "''") + "'"

    def commit(self):
        if self.mode == "postgis":
            with self.lock:
                self.conn.commit()

    def geom_expr(self, placeholder: bool = True) -> str:
        """SQL expression turning a WKT bind param into geometry (both dialects)."""
        p = self.ph if placeholder else "?"
        return f"ST_GeomFromText({p}, {SRID})" if self.mode == "postgis" else f"ST_GeomFromText({p})"

    def vector_lit(self, vec: list[float]) -> str:
        return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"

    def table_empty(self, name: str) -> bool:
        try:
            return self.q(f"SELECT COUNT(*) FROM {name}")[0][0] == 0
        except Exception:
            return True

    # ─────────────────────────────────────────────────────────────────────
    # schema
    # ─────────────────────────────────────────────────────────────────────
    def create_schema(self, drop: bool = False):
        pg = self.mode == "postgis"
        def geom_col(t: str) -> str:
            return f"GEOMETRY({_GEOM_TYPES[t]}, {SRID})" if pg else "GEOMETRY"
        id_col = "SERIAL PRIMARY KEY" if pg else "INTEGER"
        vec_col = "vector(384)" if pg else "FLOAT[384]"
        ts_col = "TIMESTAMPTZ DEFAULT now()" if pg else "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"

        tables = [
            f"""CREATE TABLE population_cells (
                id {id_col}{' PRIMARY KEY' if not pg else ''}, h3 VARCHAR,
                population DOUBLE, density DOUBLE, lon DOUBLE, lat DOUBLE,
                geom {geom_col('population_cells')})""",
            f"""CREATE TABLE roads (
                id {id_col}{' PRIMARY KEY' if not pg else ''},
                road_type VARCHAR, name VARCHAR, major BOOLEAN, speed_kmh DOUBLE,
                geom {geom_col('roads')})""",
            f"""CREATE TABLE competitors (
                id {id_col}{' PRIMARY KEY' if not pg else ''},
                name VARCHAR, category VARCHAR, source VARCHAR,
                lon DOUBLE, lat DOUBLE, geom {geom_col('competitors')})""",
            f"""CREATE TABLE landuse (
                id {id_col}{' PRIMARY KEY' if not pg else ''},
                category VARCHAR, geom {geom_col('landuse')})""",
            f"""CREATE TABLE risk_zones (
                id {id_col}{' PRIMARY KEY' if not pg else ''},
                risk_type VARCHAR, risk_level VARCHAR, geom {geom_col('risk_zones')})""",
            f"""CREATE TABLE rag_chunks (
                id {id_col}{' PRIMARY KEY' if not pg else ''},
                document_id VARCHAR, title VARCHAR, chunk_text VARCHAR,
                source VARCHAR, tags VARCHAR, embedding {vec_col}, created_at {ts_col})""",
            f"""CREATE TABLE hotspot_cells (
                h3 VARCHAR PRIMARY KEY, lon DOUBLE, lat DOUBLE,
                features_json VARCHAR, geom {geom_col('hotspot_cells')})""",
            "CREATE TABLE meta_kv (key VARCHAR PRIMARY KEY, value VARCHAR)",
        ]
        if drop:
            for t in ("population_cells", "roads", "competitors", "landuse",
                      "risk_zones", "rag_chunks", "hotspot_cells", "meta_kv"):
                self.x(f"DROP TABLE IF EXISTS {t}")
        for ddl in tables:
            self.x(ddl)
        # spatial indexes (PostGIS GIST; DuckDB spatial index coverage is
        # dataset-scale adequate without one, HNSW handles vectors)
        if pg:
            for t, gcol in [(t, "geom") for t in _GEOM_TYPES]:
                self.x(f"CREATE INDEX IF NOT EXISTS {t}_geom_idx ON {t} USING GIST ({gcol})")
        self.commit()

    def create_vector_index(self):
        """Called after RAG ingest. pgvector: plain seq scan is fine at ~60
        chunks; DuckDB gets a real HNSW index to prove the vector-DB claim."""
        try:
            if self.mode == "duckdb":
                self.x("DROP INDEX IF EXISTS rag_chunks_hnsw")
                self.x("CREATE INDEX rag_chunks_hnsw ON rag_chunks USING HNSW (embedding)")
        except Exception as exc:  # never fatal
            print(f"  ⚠ HNSW index skipped: {exc}")

    # ─────────────────────────────────────────────────────────────────────
    # RAG
    # ─────────────────────────────────────────────────────────────────────
    def replace_rag_chunks(self, chunks: list[dict]):
        self.x("DELETE FROM rag_chunks")
        ph = self.ph
        for i, c in enumerate(chunks, start=1):
            vec = self.vector_lit(c["embedding"])
            if self.mode == "postgis":
                self.x(
                    f"INSERT INTO rag_chunks (id, document_id, title, chunk_text, source, tags, embedding)"
                    f" VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{vec}::vector)",
                    (i, c["document_id"], c["title"], c["text"], c["source"],
                     json.dumps(c["tags"]),) )
            else:
                self.x(
                    f"INSERT INTO rag_chunks (id, document_id, title, chunk_text, source, tags, embedding)"
                    f" VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{vec}::FLOAT[384])",
                    (i, c["document_id"], c["title"], c["text"], c["source"],
                     json.dumps(c["tags"]),))
        self.commit()

    def rag_count(self) -> int:
        try:
            return int(self.q("SELECT COUNT(*) FROM rag_chunks")[0][0])
        except Exception:
            return 0

    def vector_search(self, vec: list[float], k: int = 4) -> list[dict]:
        lit = self.vector_lit(vec)
        if self.mode == "postgis":
            sql = (f"SELECT title, chunk_text, source, tags, 1 - (embedding <=> '{lit}'::vector) AS sim"
                   f" FROM rag_chunks ORDER BY embedding <=> '{lit}'::vector LIMIT {int(k)}")
            rows = self.q(sql)
        else:
            sql = (f"SELECT title, chunk_text, source, tags,"
                   f" 1 - array_cosine_distance(embedding, '{lit}'::FLOAT[384]) AS sim"
                   f" FROM rag_chunks ORDER BY array_cosine_distance(embedding, '{lit}'::FLOAT[384])"
                   f" LIMIT {int(k)}")
            rows = self.q(sql)
        out = []
        for title, text, source, tags, sim in rows:
            try:
                tag_list = json.loads(tags) if isinstance(tags, str) else list(tags)
            except Exception:
                tag_list = []
            out.append({"title": title, "text": text, "source": source,
                        "tags": tag_list, "score": round(float(sim), 4)})
        return out

    def rag_chunk_rows(self) -> list[dict]:
        rows = self.q("SELECT title, chunk_text, source, tags FROM rag_chunks")
        out = []
        for title, text, source, tags in rows:
            try:
                tag_list = json.loads(tags) if isinstance(tags, str) else list(tags)
            except Exception:
                tag_list = []
            out.append({"title": title, "text": text, "source": source, "tags": tag_list})
        return out

    # ─────────────────────────────────────────────────────────────────────
    # hotspot materialisation
    # ─────────────────────────────────────────────────────────────────────
    def replace_hotspot_cells(self, cells: list[dict]):
        self.x("DELETE FROM hotspot_cells")
        ph = self.ph
        sql = (f"INSERT INTO hotspot_cells (h3, lon, lat, features_json, geom)"
               f" VALUES ({ph},{ph},{ph},{ph},{self.geom_expr()})")
        self.many(sql, [(c["h3"], c["lon"], c["lat"], json.dumps(c["features"]), c["wkt"])
                        for c in cells])
        self.commit()

    def info(self) -> dict:
        def _count(t):
            try:
                return self.q(f"SELECT COUNT(*) FROM {t}")[0][0]
            except Exception:
                return 0
        return {"mode": self.mode, "path": self.path,
                "tables": {t: _count(t) for t in
                           ("population_cells", "roads", "competitors", "landuse",
                            "risk_zones", "rag_chunks", "hotspot_cells")}}

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# connection factory
# ─────────────────────────────────────────────────────────────────────────────
_GEODB: GeoDB | None = None


def _try_postgis(dsn: str) -> GeoDB | None:
    import psycopg  # lazy — only needed in hero mode
    print(f"▶ Trying PostgreSQL/PostGIS at {dsn.split('@')[-1]} …")
    conn = psycopg.connect(dsn, connect_timeout=3, autocommit=False)
    conn.execute("SELECT 1")
    # verify the extensions truly exist (this is the spec §5/§18 promise)
    exts = {r[0] for r in conn.execute("SELECT extname FROM pg_extension").fetchall()}
    missing = {"postgis", "vector"} - exts
    if missing:
        raise RuntimeError(f"PostgreSQL reachable but extensions missing: {', '.join(missing)}")
    print("✔ Connected — PostGIS + pgvector confirmed")
    return GeoDB("postgis", conn, path=dsn.split("@")[-1])


def _open_duckdb(path: Path) -> GeoDB:
    import duckdb  # lazy
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = duckdb.connect(str(path))
    except Exception as exc:
        if "lock" in str(exc).lower():
            # another process (the live server) is the writer — work against a
            # consistent snapshot COPY for read-only tooling/probes.
            import shutil, tempfile
            snap = Path(tempfile.gettempdir()) / f"{path.stem}-ro-snap.duckdb"
            shutil.copy2(path, snap)
            wal = path.with_suffix(path.suffix + ".wal")
            print(f"⚠ duckdb locked by writer — using snapshot copy {snap}")
            conn = duckdb.connect(str(snap), read_only=True)
        else:
            raise
    for stmt in ("INSTALL spatial", "LOAD spatial"):
        conn.execute(stmt)
    try:
        conn.execute("INSTALL vss")
        conn.execute("LOAD vss")
        conn.execute("SET hnsw_enable_experimental_persistence = true")
    except Exception as exc:
        print(f"  ⚠ duckdb vss extension unavailable ({exc}); cosine search still works via SQL")
    return GeoDB("duckdb", conn, path=str(path))


def init_geodb(database_url: str, duckdb_path: str) -> GeoDB:
    """Resolve the active spatial DB. Hero = PostGIS; fallback = DuckDB file."""
    global _GEODB
    if _GEODB is not None:
        return _GEODB
    # 1) hero: PostgreSQL when a DSN is configured and reachable
    if database_url:
        try:
            _GEODB = _try_postgis(database_url)
            return _GEODB
        except Exception as exc:
            print(f"⚠ PostgreSQL not usable ({type(exc).__name__}: {exc})")
            print("  → falling back to embedded DuckDB (same SQL, same tables)")
    # 2) embedded: DuckDB + spatial + vss
    _GEODB = _open_duckdb(Path(duckdb_path))
    print(f"✔ DuckDB spatial store open — {duckdb_path}")
    return _GEODB


def get_geodb() -> GeoDB | None:
    return _GEODB
