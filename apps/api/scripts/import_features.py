"""Import extracted features from JSONL into Supabase via SQL.

Generates batched INSERT statements for use with Supabase MCP execute_sql,
or outputs SQL to stdout for piping into psql.

Usage:
    # Print SQL to stdout (for piping to psql or manual review):
    python apps/api/scripts/import_features.py \
        --jsonl apps/api/scripts/seed_features.jsonl \
        --format sql

    # Generate numbered .sql files for batch import:
    python apps/api/scripts/import_features.py \
        --jsonl apps/api/scripts/seed_features.jsonl \
        --format files --output-dir apps/api/scripts/sql_batches \
        --batch-size 50
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def escape_sql(value: str | None) -> str:
    """Escape a string for SQL insertion."""
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def row_to_values(row: dict) -> str:
    """Convert a JSONL row dict to a SQL VALUES tuple string."""
    title = escape_sql(row.get("title"))
    artist = escape_sql(row.get("artist"))
    album = escape_sql(row.get("album"))
    duration = row.get("duration_sec")
    duration_str = str(duration) if duration is not None else "NULL"
    bpm = row.get("bpm")
    bpm_str = str(bpm) if bpm is not None else "NULL"
    key = escape_sql(row.get("musical_key"))
    learned = escape_sql(row.get("learned_embedding"))
    hc_raw = escape_sql(row.get("handcrafted_raw"))
    hc_norm = escape_sql(row.get("handcrafted_norm"))
    source = escape_sql(row.get("source"))
    emb_type = escape_sql(row.get("embedding_type"))
    meta_status = escape_sql(row.get("metadata_status"))
    genre = escape_sql(row.get("genre"))
    year = row.get("release_year")
    year_str = str(year) if year is not None else "NULL"

    return (
        f"({title}, {artist}, {album}, {duration_str}, {bpm_str}, {key}, "
        f"{learned}::vector, {hc_raw}::vector, {hc_norm}::vector, "
        f"{source}, {emb_type}, {meta_status}, {genre}, {year_str})"
    )


def generate_insert(rows: list[dict]) -> str:
    """Generate a single INSERT statement for a batch of rows."""
    columns = (
        "title, artist, album, duration_sec, bpm, musical_key, "
        "learned_embedding, handcrafted_raw, handcrafted_norm, "
        "source, embedding_type, metadata_status, genre, release_year"
    )
    values = ",\n".join(row_to_values(r) for r in rows)
    return f"INSERT INTO public.songs ({columns})\nVALUES\n{values};"


def main() -> None:
    parser = argparse.ArgumentParser(description="Import features JSONL into Supabase.")
    parser.add_argument("--jsonl", required=True, help="Path to seed_features.jsonl")
    parser.add_argument(
        "--format",
        choices=["sql", "files"],
        default="files",
        help="Output format: 'sql' prints to stdout, 'files' writes numbered .sql files",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for .sql batch files (default: sql_batches/ next to JSONL)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Rows per INSERT statement (default: 50)",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl).resolve()
    if not jsonl_path.is_file():
        logger.error("JSONL file not found: %s", jsonl_path)
        sys.exit(1)

    # Read all rows
    rows = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                # Strip internal _tid field
                row.pop("_tid", None)
                rows.append(row)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping invalid JSON on line %d: %s", line_num, exc)

    logger.info("Loaded %d rows from '%s'", len(rows), jsonl_path)

    if not rows:
        logger.info("No rows to import.")
        return

    # Generate batched INSERT statements
    batches = [rows[i : i + args.batch_size] for i in range(0, len(rows), args.batch_size)]
    logger.info("Generated %d batches of up to %d rows each", len(batches), args.batch_size)

    if args.format == "sql":
        for batch in batches:
            print(generate_insert(batch))
            print()
    else:
        output_dir = Path(args.output_dir) if args.output_dir else jsonl_path.parent / "sql_batches"
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, batch in enumerate(batches, 1):
            sql_file = output_dir / f"batch_{i:04d}.sql"
            sql_file.write_text(generate_insert(batch), encoding="utf-8")

        logger.info("Wrote %d .sql files to '%s'", len(batches), output_dir)
        logger.info(
            "Import via MCP execute_sql or: cat %s/*.sql | psql $DATABASE_URL",
            output_dir,
        )


if __name__ == "__main__":
    main()
