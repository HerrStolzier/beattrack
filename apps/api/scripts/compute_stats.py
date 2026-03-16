"""Compute handcrafted normalization stats and re-normalize all songs.

Generates SQL statements for use with Supabase MCP execute_sql.
No Supabase client or env vars needed — runs entirely via SQL.

Usage:
    # Generate SQL files:
    python scripts/compute_stats.py --format files --output-dir scripts/sql_stats

    # Print SQL to stdout:
    python scripts/compute_stats.py --format sql

Steps (all executed server-side in PostgreSQL):
    1. Compute mean + std per dimension (44-dim) using aggregate functions
    2. Upsert stats into config table as 'normalization_stats'
    3. Re-normalize all songs in-place → update handcrafted_norm
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DIMS = 44


def generate_compute_and_upsert_sql() -> str:
    """Generate SQL that computes stats and upserts them into config table.

    Uses a CTE to extract each dimension from the pgvector, compute
    AVG and STDDEV across all songs, then packs it into a JSON object.
    """
    # Build dimension extraction expressions
    # pgvector doesn't support subscripting — must cast to float8[] first
    dim_avgs = ", ".join(
        f"AVG(arr[{i + 1}])::float8 AS avg_{i}" for i in range(DIMS)
    )
    dim_stds = ", ".join(
        f"GREATEST(STDDEV_POP(arr[{i + 1}])::float8, 1e-10) AS std_{i}"
        for i in range(DIMS)
    )

    # Build JSON arrays from computed values
    mean_json = " || ',' || ".join(f"s.avg_{i}::text" for i in range(DIMS))
    std_json = " || ',' || ".join(f"s.std_{i}::text" for i in range(DIMS))

    return f"""-- Step 1+2: Compute normalization stats and upsert into config
WITH raw_arrays AS (
  SELECT replace(replace(handcrafted_raw::text, '[', '{{'), ']', '}}')::float8[] AS arr
  FROM public.songs
  WHERE handcrafted_raw IS NOT NULL
),
stats AS (
  SELECT
    {dim_avgs},
    {dim_stds},
    COUNT(*)::int AS n_songs
  FROM raw_arrays
)
INSERT INTO public.config (key, value)
SELECT
  'normalization_stats',
  json_build_object(
    'mean', ('[' || {mean_json} || ']')::json,
    'std', ('[' || {std_json} || ']')::json,
    'dim', {DIMS},
    'n_songs', s.n_songs
  )::jsonb
FROM stats s
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;"""


def generate_normalize_sql() -> str:
    """Generate SQL that re-normalizes all songs using stored stats.

    Reads mean/std from config table and applies Z-score normalization
    to each dimension of handcrafted_raw, writing the result to handcrafted_norm.
    """
    # Build the normalized vector expression: (raw[i] - mean[i]) / std[i]
    norm_dims = ", ".join(
        f"(s.handcrafted_raw[{i + 1}] - (stats.value::json->>'mean')::json->>{i}::float8) "
        f"/ (stats.value::json->>'std')::json->>{i}::float8"
        for i in range(DIMS)
    )

    # Simpler approach: use a plpgsql DO block for clarity
    return f"""-- Step 3: Re-normalize all songs using stored stats
DO $$
DECLARE
  v_mean float8[];
  v_std float8[];
  v_dim int := {DIMS};
  v_raw float8[];
  v_norm float8[];
  v_count int := 0;
  rec RECORD;
BEGIN
  -- Load stats from config
  SELECT
    ARRAY(SELECT json_array_elements_text((value::json->>'mean')::json)::float8)
      INTO v_mean
  FROM public.config WHERE key = 'normalization_stats';

  SELECT
    ARRAY(SELECT json_array_elements_text((value::json->>'std')::json)::float8)
      INTO v_std
  FROM public.config WHERE key = 'normalization_stats';

  IF v_mean IS NULL THEN
    RAISE EXCEPTION 'normalization_stats not found in config table';
  END IF;

  -- Normalize each song
  FOR rec IN
    SELECT id, handcrafted_raw
    FROM public.songs
    WHERE handcrafted_raw IS NOT NULL
  LOOP
    -- Extract raw vector to array (pgvector doesn't support direct ::float8[] cast)
    v_raw := replace(replace(rec.handcrafted_raw::text, '[', '{{'), ']', '}}')::float8[];

    -- Z-score normalize
    v_norm := ARRAY(
      SELECT (v_raw[i] - v_mean[i]) / v_std[i]
      FROM generate_series(1, v_dim) AS i
    );

    -- Update
    UPDATE public.songs
    SET handcrafted_norm = v_norm::vector
    WHERE id = rec.id;

    v_count := v_count + 1;
    IF v_count % 5000 = 0 THEN
      RAISE NOTICE 'Normalized % songs...', v_count;
    END IF;
  END LOOP;

  RAISE NOTICE 'Done! Normalized % songs total.', v_count;
END $$;"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate SQL for computing normalization stats."
    )
    parser.add_argument(
        "--format",
        choices=["sql", "files"],
        default="files",
        help="Output format: 'sql' prints to stdout, 'files' writes .sql files",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for .sql files (default: sql_stats/ next to this script)",
    )
    args = parser.parse_args()

    sql_compute = generate_compute_and_upsert_sql()
    sql_normalize = generate_normalize_sql()

    if args.format == "sql":
        print(sql_compute)
        print()
        print(sql_normalize)
    else:
        output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent / "sql_stats"
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "01_compute_stats.sql").write_text(sql_compute, encoding="utf-8")
        (output_dir / "02_normalize.sql").write_text(sql_normalize, encoding="utf-8")

        logger.info("Wrote 2 SQL files to '%s'", output_dir)
        logger.info("Run via MCP execute_sql or: psql $DATABASE_URL < %s/01_compute_stats.sql", output_dir)


if __name__ == "__main__":
    main()
