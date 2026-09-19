# PostGIS 3.4 + pgvector on PostgreSQL 16 — one image for both extension sets.
FROM postgis/postgis:16-3.4

RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16-pgvector \
 && rm -rf /var/lib/apt/lists/*

# Enable both extensions at first boot.
COPY init-extensions.sql /docker-entrypoint-initdb.d/
