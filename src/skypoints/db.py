"""Database setup. DuckDB runs the same SQL shape that Snowflake would."""
from pathlib import Path

import duckdb

from .config import COUNTRY_MAP

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def connect(path: str = ":memory:"):
    con = duckdb.connect(path)
    init_db(con)
    return con


def init_db(con) -> None:
    con.execute(read_sql("00_raw.sql"))
    con.execute(read_sql("01_support.sql"))
    con.executemany("INSERT INTO country_map VALUES (?, ?) ON CONFLICT DO NOTHING", list(COUNTRY_MAP.items()))


def target_table(country_iso2: str) -> str:
    cc = "".join(ch for ch in country_iso2.lower() if ch.isalpha())
    return f"tgt_member_{cc}"


def ensure_target(con, country_iso2: str) -> str:
    table = target_table(country_iso2)
    con.execute(read_sql("02_target_member.sql.tmpl").format(table=table))
    return table


def target_tables(con):
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'tgt\\_member\\_%' ESCAPE '\\'"
    ).fetchall()
    return [r[0] for r in rows]


def insert_many(con, sql, rows) -> None:
    """executemany that tolerates an empty list (DuckDB raises on empty)."""
    rows = list(rows)
    if rows:
        con.executemany(sql, rows)