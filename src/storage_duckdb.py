#!/usr/bin/env python3
from pathlib import Path
import duckdb
import pandas as pd

PARQUET_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry_store.parquet"

def append_and_query_telemetry(new_rows: list[dict]) -> pd.DataFrame:
    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(database=":memory:")
    new_df = pd.DataFrame(new_rows)

    if PARQUET_PATH.exists():
        con.execute(f"CREATE TABLE history AS SELECT * FROM read_parquet('{PARQUET_PATH}')")
        con.execute("INSERT INTO history SELECT * FROM new_df")
    else:
        con.execute("CREATE TABLE history AS SELECT * FROM new_df")

    # Retain rolling window of last 2,000 target snapshots and persist to ZSTD Parquet
    con.execute("""
        CREATE TABLE trimmed AS
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp DESC) as rn FROM history
        ) WHERE rn <= 2000
    """)
    con.execute("ALTER TABLE trimmed DROP COLUMN rn")
    con.execute(f"COPY trimmed TO '{PARQUET_PATH}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    # Compute SQL window deltas per target
    enriched_df = con.execute("""
        SELECT
            timestamp,
            target,
            count,
            gc_pct,
            kmer_entropy,
            COALESCE(count - LAG(count) OVER (PARTITION BY target ORDER BY timestamp), 0) AS delta_records,
            ROUND(AVG(gc_pct) OVER (PARTITION BY target ORDER BY timestamp ROWS BETWEEN 5 PRECEDING AND CURRENT ROW), 2) AS rolling_gc
        FROM trimmed
        ORDER BY timestamp ASC
    """).df()

    con.close()
    return enriched_df
